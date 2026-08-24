from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, String, Text, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


class SessionRecord(Base):
    """
    Every agent session is stored as a single JSON blob of AgentState.
    This is deliberately simple (no relational modeling of flights/hotels)
    because the whole point is resumability: load the blob, resume the
    graph. Swap for Postgres by changing DATABASE_URL in .env — no code
    changes needed elsewhere.
    """

    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    state_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    # FIX B12: updated_at was never actually updated on save because
    # SQLAlchemy Core's `onupdate` only fires on UPDATE statements triggered
    # by ORM flush, not on manual attribute assignment.  We now set it
    # explicitly in save_state() below so every save is correctly timestamped.
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def save_state(session_id: str, state: dict) -> None:
    async with async_session_factory() as db:
        existing = await db.get(SessionRecord, session_id)
        payload = json.dumps(state, default=str)
        now = datetime.now(timezone.utc)
        if existing:
            existing.state_json = payload
            # FIX B12: explicitly stamp the update time on every save.
            existing.updated_at = now
        else:
            db.add(SessionRecord(id=session_id, state_json=payload, created_at=now, updated_at=now))
        await db.commit()


async def load_state(session_id: str) -> Optional[dict]:
    async with async_session_factory() as db:
        record = await db.get(SessionRecord, session_id)
        return json.loads(record.state_json) if record else None
