"""
Face Recognition Engine — powered by Google Gemini Vision API.

Strategy:
  INDEXING PHASE (run once per image, results cached in DB):
    • Upload each Drive image to Gemini
    • Ask Gemini to describe every face in the image as a structured JSON
      (facial geometry, skin tone, hair, distinctive features, etc.)
    • Store that face descriptor JSON as the "embedding" in DriveFileCache

  SEARCH PHASE (per user search):
    • Extract descriptor from the reference image
    • For each indexed file, call Gemini asking:
      "Given face descriptor A (reference) and face descriptor B (indexed),
       how confident are you (0.0–1.0) that these are the same person?"
    • Filter results above threshold

  Advantages over local DeepFace:
    ✓ No 500MB model download
    ✓ No TensorFlow / compilation required
    ✓ Works on any hardware (CPU-only servers, free tier)
    ✓ Handles low-quality / obscured faces better
    ✓ Multilingual image understanding
"""

from __future__ import annotations

import base64
import io
import json
import logging
import re
from typing import Optional

import google.generativeai as genai
from PIL import Image

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ─── Gemini client (lazy init) ────────────────────────────────────────────────

_model = None


def _get_model():
    global _model
    if _model is None:
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Get a free key at https://aistudio.google.com/apikey"
            )
        genai.configure(api_key=settings.gemini_api_key)
        _model = genai.GenerativeModel(settings.gemini_model)
    return _model


# ─── Image helpers ────────────────────────────────────────────────────────────

def _image_to_part(image_bytes: bytes, max_size: int = 1024) -> dict:
    """Convert raw image bytes to a Gemini inline image part, resized for efficiency."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    # Resize for API efficiency — faces are still recognisable at 1024px
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    data = buf.getvalue()
    return {
        "inline_data": {
            "mime_type": "image/jpeg",
            "data": base64.b64encode(data).decode(),
        }
    }


def _parse_json_from_response(text: str) -> dict | list | None:
    """Extract the first JSON block from Gemini's response text."""
    # Try direct parse first
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    # Find JSON inside markdown code fences
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", stripped)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Find first {...} or [...] block
    match = re.search(r"(\{[\s\S]+\}|\[[\s\S]+\])", stripped)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None


# ─── Face Descriptor Extraction ───────────────────────────────────────────────

_DESCRIPTOR_PROMPT = """
Analyze this image and detect all human faces present.

For each face found, produce a JSON object with these fields:
{
  "face_index": <integer, 0-based>,
  "approximate_age_range": "<e.g. 25-35>",
  "gender_presentation": "<e.g. masculine / feminine / neutral>",
  "skin_tone": "<very light / light / medium / medium-dark / dark / very dark>",
  "face_shape": "<oval / round / square / heart / oblong / diamond>",
  "eye_color": "<color>",
  "eye_shape": "<e.g. almond / round / hooded / monolid>",
  "eyebrow_shape": "<e.g. arched / straight / bushy / thin>",
  "nose_shape": "<e.g. narrow / broad / upturned / prominent>",
  "lip_fullness": "<thin / medium / full>",
  "jaw_line": "<sharp / soft / square / round>",
  "cheekbones": "<high / average / low>",
  "hair_color": "<color or 'bald'>",
  "hair_style": "<e.g. short straight, long curly, bald>",
  "facial_hair": "<none / stubble / mustache / beard / full beard>",
  "distinctive_features": ["<e.g. glasses, scar, mole, freckles, dimples>"],
  "face_position": "<front-facing / slight-left / slight-right / profile / angled>",
  "image_quality": "<excellent / good / fair / poor>"
}

Return a JSON array of face objects. If NO face is detected, return: []
Return ONLY valid JSON — no explanation text.
""".strip()


def extract_embeddings(image_bytes: bytes, **kwargs) -> list[list]:
    """
    Detect all faces in image_bytes and return a list of face descriptors.

    Each descriptor is stored as a list containing a single dict (to match
    the List[List[float]] shape that DriveFileCache.embeddings expects,
    but here each "embedding" is actually a face descriptor dict serialized
    inside a list).

    Returns:
        List of face descriptors. Each descriptor is [face_dict].
        Empty list if no faces found or Gemini call fails.

    Raises:
        ValueError: If image cannot be decoded.
    """
    model = _get_model()
    try:
        image_part = _image_to_part(image_bytes)
    except Exception as exc:
        raise ValueError(f"Cannot decode image: {exc}") from exc

    try:
        response = model.generate_content(
            [_DESCRIPTOR_PROMPT, image_part],
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=2048,
            ),
        )
        text = response.text
        faces = _parse_json_from_response(text)

        if not isinstance(faces, list):
            logger.debug("Gemini returned non-list for face detection: %s", text[:200])
            return []

        # Wrap each face dict in a list so it fits the DB column schema
        descriptors = []
        for face in faces:
            if isinstance(face, dict):
                descriptors.append([face])  # [face_dict]

        logger.debug("Extracted %d face descriptor(s) from image", len(descriptors))
        return descriptors

    except Exception as exc:
        logger.warning("Gemini face extraction failed: %s", exc)
        return []


# ─── Face Comparison ─────────────────────────────────────────────────────────

_COMPARE_PROMPT_TEMPLATE = """
You are a precise facial recognition system. Your job is to determine whether two face descriptions refer to the same real person.

REFERENCE FACE (person we are searching for):
{ref_desc}

CANDIDATE FACE (from a photo in our database):
{cand_desc}

Analyze both descriptors carefully. Consider:
- Key biometric features: face shape, nose shape, jaw line, cheekbones, eye shape/color
- Consistent distinctive features (glasses, scars, moles, facial hair)
- Age-appropriate matches (the candidate may be from a different time)
- Ignore: lighting, image quality, hairstyle changes, makeup

Respond with ONLY a JSON object like:
{{
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<one sentence explaining the key matching or non-matching features>"
}}

Where confidence means:
  0.95–1.0: Extremely high confidence — same person
  0.80–0.94: High confidence — very likely same person
  0.65–0.79: Moderate confidence — probably same person
  0.40–0.64: Low confidence — might be same person
  0.00–0.39: Very low — likely different people
""".strip()


def _compare_descriptors(ref_desc: dict, cand_desc: dict) -> float:
    """Ask Gemini to score similarity between two face descriptor dicts. Returns 0–1."""
    model = _get_model()
    prompt = _COMPARE_PROMPT_TEMPLATE.format(
        ref_desc=json.dumps(ref_desc, indent=2),
        cand_desc=json.dumps(cand_desc, indent=2),
    )
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=256,
            ),
        )
        result = _parse_json_from_response(response.text)
        if isinstance(result, dict):
            confidence = float(result.get("confidence", 0.0))
            logger.debug("Gemini comparison: %.3f — %s", confidence, result.get("reasoning", ""))
            return max(0.0, min(1.0, confidence))
    except Exception as exc:
        logger.warning("Gemini comparison failed: %s", exc)
    return 0.0


def cosine_similarity(a, b) -> float:
    """Compatibility shim — not used with Gemini but kept for import compatibility."""
    return 0.0


def compare_against_index(
    reference_embeddings: list[list],
    indexed_files: list[dict],
    threshold: float = 0.68,
) -> list[dict]:
    """
    Compare reference face descriptors against all cached file descriptors.

    Args:
        reference_embeddings: List of [face_dict] from extract_embeddings on reference image.
        indexed_files: List of DriveFileCache dicts with 'embeddings' key.
        threshold: Minimum Gemini confidence to include in results.

    Returns:
        Sorted list of match dicts (highest confidence first):
          {file_id, filename, thumbnail_url, web_view_link, confidence}
    """
    if not reference_embeddings:
        return []

    # Flatten all reference face dicts
    ref_faces: list[dict] = []
    for emb in reference_embeddings:
        if isinstance(emb, list) and len(emb) > 0 and isinstance(emb[0], dict):
            ref_faces.append(emb[0])

    if not ref_faces:
        return []

    matches: dict[str, dict] = {}

    for file_record in indexed_files:
        file_embeddings = file_record.get("embeddings") or []
        if not file_embeddings:
            continue

        # Flatten candidate face dicts
        cand_faces: list[dict] = []
        for emb in file_embeddings:
            if isinstance(emb, list) and len(emb) > 0 and isinstance(emb[0], dict):
                cand_faces.append(emb[0])

        if not cand_faces:
            continue

        # Find best score across all (ref_face, cand_face) pairs
        best_score = 0.0
        for ref_f in ref_faces:
            for cand_f in cand_faces:
                score = _compare_descriptors(ref_f, cand_f)
                if score > best_score:
                    best_score = score

        if best_score >= threshold:
            matches[file_record["file_id"]] = {
                "file_id": file_record["file_id"],
                "filename": file_record["filename"],
                "thumbnail_url": file_record.get("thumbnail_url"),
                "web_view_link": file_record.get("web_view_link"),
                "confidence": round(best_score, 4),
            }

    return sorted(matches.values(), key=lambda x: x["confidence"], reverse=True)
