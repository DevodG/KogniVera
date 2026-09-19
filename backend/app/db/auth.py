import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, DateTime, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

from app.db.database import Base, async_session_factory


class UserRecord(Base):
    """
    User accounts stored in the local concierge.db.
    This is separate from the read-only PackagePro data.
    """
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    preferred_languages = Column(String, nullable=True) # comma-separated BCP-47
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


async def create_user(email: str, hashed_password: str) -> UserRecord:
    async with async_session_factory() as db:
        user_id = f"usr_{uuid.uuid4().hex[:8]}"
        user = UserRecord(
            id=user_id,
            email=email,
            hashed_password=hashed_password,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def get_user_by_email(email: str) -> Optional[UserRecord]:
    async with async_session_factory() as db:
        result = await db.execute(select(UserRecord).where(UserRecord.email == email))
        return result.scalars().first()


async def update_user_preferences(user_id: str, languages: str) -> None:
    async with async_session_factory() as db:
        user = await db.get(UserRecord, user_id)
        if user:
            user.preferred_languages = languages
            await db.commit()
