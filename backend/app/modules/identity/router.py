from __future__ import annotations
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.modules.identity.models import User
from app.modules.identity.schemas import ChangePasswordRequest, CurrentUserResponse, ForgotPasswordRequest, LoginRequest, LoginResponse, LogoutRequest, MessageResponse, RefreshRequest, RegisterRequest, RegistrationResponse, ResetPasswordRequest, TokenResponse, VerifyEmailRequest
from app.modules.identity.service import IdentityService

router = APIRouter(
  prefix="/auth",
  tags=["Identity / Authentication"],
)

@router.post(
  "/login",
  response_model=LoginResponse,
)
async def login(
  payload: LoginRequest,
  session: AsyncSession = Depends(get_db),
) -> LoginResponse:
  service = IdentityService(session)

  return await service.login(
    email=payload.email,
    password=payload.password,
  )

@router.post(
  "/refresh",
  response_model=TokenResponse,
)
async def refresh(
  payload: RefreshRequest,
  session: AsyncSession = Depends(get_db),
) -> TokenResponse:
  service = IdentityService(session)

  return await service.refresh(
    raw_refresh_token=payload.refresh_token,
  )

@router.post(
  "/logout",
  response_model=MessageResponse,
)
async def logout(
  payload: LogoutRequest,
  session: AsyncSession = Depends(get_db),
) -> MessageResponse:
  service = IdentityService(session)

  await service.logout(
    raw_refresh_token=payload.refresh_token,
  )
  return MessageResponse(
    message="Successfully logged out."
  )

@router.get(
  "/me",
  response_model=CurrentUserResponse,
)
async def me(
  current_user: User = Depends(
    get_current_user
  ),
) -> CurrentUserResponse:
  return CurrentUserResponse(
    user=current_user
  )

@router.post(
  "/logout-all",
  response_model=MessageResponse,
)
async def logout_all(
  current_user: User = Depends(
    get_current_user
  ),
  session: AsyncSession = Depends(get_db),
) -> MessageResponse:
  service = IdentityService(session)

  await service.logout_all(
    current_user.id
  )
  return MessageResponse(
    message="All active sessions have been revoked."
  )