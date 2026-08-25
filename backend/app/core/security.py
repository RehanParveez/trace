from datetime import datetime, timedelta, timezone
from typing import Any
import jwt
import bcrypt
from app.core.config import settings

def create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
  now = datetime.now(timezone.utc)
  payload: dict[str, Any] = {
    "sub": subject,
    "type": token_type,
    "iat": now,
    "exp": now + expires_delta,
  }
  return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def create_access_token(subject: str) -> str:
  return create_token(
    subject,
    "access",
    timedelta(minutes=settings.access_token_expire_minutes),
  )

def create_refresh_token(subject: str) -> str:
  return create_token(
    subject,
    "refresh",
    timedelta(days=settings.refresh_token_expire_days),
  )

def decode_token(token: str) -> dict[str, Any]:
  return jwt.decode(
    token,
    settings.jwt_secret_key,
    algorithms=[settings.jwt_algorithm],
  )

def hash_password(password: str) -> str:
  return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, password_hash: str) -> bool:
  return bcrypt.checkpw(password.encode(), password_hash.encode())