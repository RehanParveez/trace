from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any
import bcrypt
import jwt
from app.core.config import settings

def create_token(
  *,
  subject: str,
  token_type: str,
  expires_delta: timedelta,
  organization_id: str | None = None,
) -> str:
  now = datetime.now(timezone.utc)

  payload: dict[str, Any] = {
    "sub": subject,
    "type": token_type,
    "iat": now,
    "exp": now + expires_delta,
  }

  if organization_id is not None:
    payload["org_id"] = organization_id

  return jwt.encode(
    payload,
    settings.jwt_secret_key,
    algorithm=settings.jwt_algorithm,
  )

def create_access_token(
  *,
  subject: str,
  organization_id: str,
) -> str:
  return create_token(
    subject=subject,
    token_type="access",
    organization_id=organization_id,
    expires_delta=timedelta(
      minutes=settings.access_token_expire_minutes
    ),
  )

def create_refresh_token(
  *,
  subject: str,
  organization_id: str,
) -> str:
  return create_token(
    subject=subject,
    token_type="refresh",
    organization_id=organization_id,
    expires_delta=timedelta(
      days=settings.refresh_token_expire_days
    ),
  )

def decode_token(token: str) -> dict[str, Any]:
  return jwt.decode(
    token,
    settings.jwt_secret_key,
    algorithms=[settings.jwt_algorithm],
  )

def hash_password(password: str) -> str:
  return bcrypt.hashpw(
    password.encode("utf-8"),
    bcrypt.gensalt(),
  ).decode("utf-8")

def verify_password(
  password: str,
  password_hash: str,
) -> bool:
  try:
    return bcrypt.checkpw(
      password.encode("utf-8"),
      password_hash.encode("utf-8"),
    )
  except (ValueError, TypeError):
    return False