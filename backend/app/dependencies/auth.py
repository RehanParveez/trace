from __future__ import annotations
from uuid import UUID
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.exceptions import TraceException
from app.core.redis import IdentityTokenStore, redis_client
from app.core.security import decode_token
from app.dependencies.tenancy import scope_session_to_org
from app.modules.identity.enums import TokenType
from app.modules.identity.models import User
from app.modules.identity.service import IdentityService

bearer_scheme = HTTPBearer(
  auto_error=False,
)

async def get_current_user(
  credentials: HTTPAuthorizationCredentials | None = Depends(
    bearer_scheme
  ),
  session: AsyncSession = Depends(get_db),
) -> User:
  if credentials is None:
    raise TraceException(
      "Authentication required.",
      status_code=401,
      code="AUTHENTICATION_REQUIRED",
    )

  try:
    payload = decode_token(
      credentials.credentials
    )
  except Exception as exc:
    raise TraceException(
      "Invalid or expired access token.",
      status_code=401,
      code="INVALID_ACCESS_TOKEN",
    ) from exc

  if payload.get("type") != TokenType.ACCESS:
    raise TraceException(
      "Invalid access token.",
      status_code=401,
      code="INVALID_ACCESS_TOKEN",
    )

  subject = payload.get("sub")
  organization_id = payload.get("org_id")

  if not subject or not organization_id:
    raise TraceException(
      "Invalid access token claims.",
      status_code=401,
      code="INVALID_ACCESS_TOKEN",
    )

  try:
    user_id = UUID(subject)
    token_organization_id = UUID(
      organization_id
    )
  except ValueError as exc:
    raise TraceException(
      "Invalid access token claims.",
      status_code=401,
      code="INVALID_ACCESS_TOKEN",
    ) from exc

  await scope_session_to_org(session, token_organization_id)
  token_store = IdentityTokenStore(
    redis_client
  )

  service = IdentityService(
    session=session,
    token_store=token_store,
  )
  user = await service.get_current_user(
    user_id
  )

  if user.organization_id != token_organization_id:
    raise TraceException(
      "Authentication context mismatch.",
      status_code=401,
      code="AUTHENTICATION_CONTEXT_MISMATCH",
    )

  return user

async def get_current_user_id(
  current_user: User = Depends(
    get_current_user
  ),
) -> UUID:
  return current_user.id