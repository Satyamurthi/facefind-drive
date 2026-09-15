"""
seed_admin.py — Bootstrap the first admin user into the database.

Usage:
    python seed_admin.py

This script creates the DB tables (if missing) and inserts an admin user.
Run this once after deploying to Supabase to get your first admin account.
"""

import asyncio
import getpass
import sys
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Load settings from .env
from config import get_settings
from db.models import Base, User
from utils.auth_utils import hash_password


async def seed(email: str, password: str, full_name: str):
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        print("⏳ Creating tables if they don't exist...")
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Tables ready.")

    async with async_session() as session:
        # Check if email already exists
        result = await session.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"\n⚠️  A user with email '{email}' already exists.")
            print(f"   Role: {existing.role} | Active: {existing.is_active}")
            if existing.role != "admin":
                existing.role = "admin"
                await session.commit()
                print("   ✅ Role upgraded to 'admin'.")
            else:
                print("   ℹ️  No changes made.")
            await engine.dispose()
            return

        admin = User(
            id=str(uuid.uuid4()),
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name or None,
            role="admin",
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        print(f"\n✅ Admin user created!")
        print(f"   Email:    {email}")
        print(f"   Name:     {full_name or '(none)'}")
        print(f"   Role:     admin")
        print(f"   ID:       {admin.id}")
        print(f"\n👉 You can now log in at your FaceFind Drive frontend.")

    await engine.dispose()


def main():
    print("=" * 50)
    print("  FaceFind Drive — Admin Seed Script")
    print("=" * 50)
    print()

    email = input("Admin email: ").strip()
    if not email:
        print("❌ Email cannot be empty.")
        sys.exit(1)

    full_name = input("Full name (optional, press Enter to skip): ").strip()

    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("❌ Passwords do not match.")
        sys.exit(1)
    if len(password) < 8:
        print("❌ Password must be at least 8 characters.")
        sys.exit(1)

    print()
    asyncio.run(seed(email, password, full_name))


if __name__ == "__main__":
    main()
