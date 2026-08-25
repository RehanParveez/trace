from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.exceptions import TraceException
from app.core.security import decode_token

bearer = HTTPBearer(auto_error=False)

async def get_current_subject(
  credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
  if not credentials:
    raise TraceException("Authentication required.", 401, "AUTH_REQUIRED")

  try:
    payload = decode_token(credentials.credentials)
  except Exception as exc:
    raise TraceException("wrong or expired token.", 401, "INVALID_TOKEN") from exc

  if payload.get("type") != "access" or not payload.get("sub"):
    raise TraceException("wrong access token.", 401, "INVALID_ACCESS_TOKEN")

  return str(payload["sub"])