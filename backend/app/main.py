from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_session import router as session_router
from app.api.routes_guides import router as guides_router
from app.api.routes_packages import router as packages_router
from app.api.routes_auth import router as auth_router
from app.api.routes_payment import router as payment_router
from app.config import settings
from app.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Agentic Travel Concierge", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session_router)
app.include_router(guides_router)
app.include_router(packages_router)
app.include_router(auth_router)
app.include_router(payment_router)


@app.get("/health")
async def health():
    return {"status": "ok", "llm_provider": settings.LLM_PROVIDER, "model": settings.AGENT_MODEL}
