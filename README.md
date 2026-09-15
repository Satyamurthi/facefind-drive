# FaceFind Drive 🔍

**Facial recognition search over a Google Drive folder.** Authorized users upload a reference photo; the app returns all matching photos from the admin-configured Drive folder, with thumbnails, confidence scores, and download links.

> ⚖️ **Ethical use only.** Access is restricted to authorized users. All searches are logged. The app must be configured with a clear Stated Purpose by the admin.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Vanilla CSS |
| Backend | FastAPI (Python 3.11) + SQLite |
| Face Recognition | DeepFace + ArcFace |
| Drive Access | Google Drive API v3 (Service Account) |
| Auth | JWT + bcrypt + Invite Codes |
| Hosting | Netlify (frontend) + Railway/Render (backend) |

---

## Step 1 — Google Cloud Service Account Setup (5 minutes)

### 1.1 Create a GCP project
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click **New Project** → name it `facefind-drive` → Create

### 1.2 Enable the Drive API
1. Navigate to **APIs & Services → Library**
2. Search for "Google Drive API" → **Enable**

### 1.3 Create a Service Account
1. Go to **APIs & Services → Credentials → Create Credentials → Service Account**
2. Name: `facefind-sa`, Role: leave blank → Done
3. Click the service account → **Keys → Add Key → Create new key → JSON**
4. Download the JSON file → save it as `backend/service_account/credentials.json`

### 1.4 Grant folder access to the service account
1. Open the JSON file and copy the `client_email` value (e.g. `facefind-sa@....iam.gserviceaccount.com`)
2. In Google Drive, right-click your target folder → **Share**
3. Paste the service account email → set role to **Viewer** → Send
4. Copy the folder ID from the URL: `drive.google.com/drive/folders/`**`FOLDER_ID`**

---

## Step 2 — Backend Setup

```bash
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### Configure environment
```bash
cp .env.example .env
```
Edit `.env` and fill in:
- `SECRET_KEY` — generate with: `python -c "import secrets; print(secrets.token_hex(32))"`
- `DRIVE_FOLDER_ID` — from step 1.4
- `ALLOWED_ORIGINS` — your Netlify frontend URL

### Create the first admin user
```bash
# Start the backend first:
uvicorn main:app --reload

# In another terminal, use the API to create the first admin.
# Since there's no admin yet, use the seeding script:
python -c "
import asyncio
from db.database import init_db, AsyncSessionLocal
from db.models import User
from utils.auth_utils import hash_password

async def seed():
    await init_db()
    async with AsyncSessionLocal() as s:
        u = User(email='admin@example.com', hashed_password=hash_password('changeme'), role='admin', full_name='Admin')
        s.add(u)
        await s.commit()
        print('Admin created: admin@example.com / changeme')

asyncio.run(seed())
"
```

### Start backend
```bash
uvicorn main:app --reload --port 8000
```
API docs: http://localhost:8000/api/docs

---

## Step 3 — Frontend Setup

```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173

---

## Step 4 — Index the Drive Folder

1. Log in as admin → **Admin → Configuration**
2. Set your **Drive Folder ID** and **Stated Purpose** → Save
3. Click **⚡ Incremental Update** to start indexing
4. Watch the index stats update — this may take a few minutes for large folders

---

## Deploying to Production

### Backend → Railway (free tier)
1. Push the `backend/` folder to a GitHub repo
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Set environment variables from your `.env` in Railway's Variables tab
4. Add your service account JSON as an environment variable:
   - Set `GOOGLE_APPLICATION_CREDENTIALS_JSON` to the entire JSON contents
   - Update `drive_client.py` to read from env if file not found (see note below)
5. Railway auto-deploys on push

### Frontend → Netlify
1. Push the `frontend/` folder to GitHub
2. Connect to [netlify.com](https://netlify.com) → New site from Git
3. Build command: `npm run build`, Publish: `dist`
4. Add environment variable: `VITE_API_URL=https://your-railway-app.up.railway.app`
5. Deploy

---

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key (32+ chars) | **Required** |
| `DRIVE_FOLDER_ID` | Google Drive folder ID | **Required** |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Path to SA JSON key | `./service_account/credentials.json` |
| `FACE_SIMILARITY_THRESHOLD` | Match confidence cutoff (0–1) | `0.68` |
| `FACE_MODEL` | DeepFace model | `ArcFace` |
| `FACE_DETECTOR` | Face detector backend | `retinaface` |
| `INDEX_INTERVAL_HOURS` | Drive re-index frequency | `6` |
| `ALLOWED_ORIGINS` | CORS allowed origins | `http://localhost:5173` |
| `STATED_PURPOSE` | Shown in consent banner | `Event Photo Retrieval` |

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/login` | Public | Login |
| POST | `/api/auth/register` | Public | Register with invite code |
| GET | `/api/auth/me` | User | Current user info |
| POST | `/api/search` | User | Upload reference image → SSE results |
| GET | `/api/download/thumbnail/{id}` | User | Proxied thumbnail |
| GET | `/api/download/file/{id}` | User | Download single file |
| POST | `/api/download/zip` | User | Download multiple files as ZIP |
| GET | `/api/admin/config` | Admin | Get app config |
| PUT | `/api/admin/config` | Admin | Update app config |
| GET/POST | `/api/admin/users` | Admin | User management |
| GET/POST | `/api/admin/invite-codes` | Admin | Invite code management |
| GET | `/api/admin/audit-logs` | Admin | View audit log |
| GET | `/api/admin/index-stats` | Admin | Cache statistics |
| POST | `/api/cache/refresh` | Admin | Trigger Drive re-index |

---

## Architecture

```
Browser (React + Vite → Netlify)
        │ REST + SSE
FastAPI Backend (Railway)
        ├── DeepFace ArcFace (face embeddings)
        ├── SQLite (users, cache, audit log)
        └── Google Drive API v3 (read-only, service account)
```

---

## Privacy & Security Notes

- **Scoped access**: The service account can only read files in the shared folder — not any other Drive content.
- **No images stored**: Reference images are processed in-memory and never saved. Only SHA-256 hashes appear in audit logs.
- **Consent banner**: Every search page shows the admin-configured stated purpose.
- **Audit logging**: Every search, login, and admin action is logged with timestamp, user, and IP.
- **JWT auth**: 1-hour access tokens with 7-day refresh tokens.
- **Invite-only registration**: New users require an admin-issued invite code.
