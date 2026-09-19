"""
Authentication endpoints using JWT.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.config import settings
from app.db.auth import create_user, get_user_by_email, update_user_preferences

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


class AuthRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    preferred_languages: Optional[str]


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user_by_email(email)
    if user is None:
        raise credentials_exception
    return {
        "id": user.id,
        "email": user.email,
        "preferred_languages": user.preferred_languages,
    }


@router.post("/register", response_model=TokenResponse)
async def register(req: AuthRequest):
    existing = await get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = pwd_context.hash(req.password)
    user = await create_user(req.email, hashed)
    
    token = create_access_token(data={"sub": user.email})
    return {
        "access_token": token,
        "user_id": user.id,
        "email": user.email,
        "preferred_languages": user.preferred_languages,
    }


@router.post("/login", response_model=TokenResponse)
async def login(req: AuthRequest):
    user = await get_user_by_email(req.email)
    if not user or not pwd_context.verify(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token(data={"sub": user.email})
    return {
        "access_token": token,
        "user_id": user.id,
        "email": user.email,
        "preferred_languages": user.preferred_languages,
    }


@router.get("/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user


class PrefsUpdate(BaseModel):
    preferred_languages: str

@router.post("/prefs")
async def update_prefs(prefs: PrefsUpdate, current_user: dict = Depends(get_current_user)):
    await update_user_preferences(current_user["id"], prefs.preferred_languages)
    return {"status": "success"}
