from __future__ import annotations
from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.redis import IdentityTokenStore, get_redis
from app.dependencies.auth import get_current_user
from app.modules.identity.models import User
from app.modules.identity.schemas import ChangePasswordRequest, CurrentUserResponse, ForgotPasswordRequest, LoginRequest, LoginResponse, LogoutRequest, MessageResponse, RefreshRequest, RegisterRequest, RegistrationResponse, ResendVerificationRequest, ResetPasswordRequest, TokenResponse, VerifyEmailRequest
from app.modules.identity.service import IdentityService
from fastapi import APIRouter, Depends, Request
from app.core.config import settings
from app.modules.identity.rate_limit import RateLimiter

router = APIRouter(
  prefix="/auth",
  tags=["Identity / Authentication"],
)

def build_identity_service(
  session: AsyncSession,
  redis: Redis,
) -> IdentityService:
  return IdentityService(
    session,
    IdentityTokenStore(redis),
  )
  
async def enforce_auth_rate_limit(
  request: Request,
  redis: Redis = Depends(get_redis),
) -> None:
  limiter = RateLimiter(redis)
  client_ip = request.client.host if request.client else "unknown"

  await limiter.check(
    key=f"auth:{request.url.path}:{client_ip}",
    limit=settings.rate_limit_auth_per_minute,
    window_seconds=60,
  )

@router.post(
  "/register",
  response_model=RegistrationResponse,
)
async def register(
  payload: RegisterRequest,
  session: AsyncSession = Depends(get_db),
  redis: Redis = Depends(get_redis),
  _: None = Depends(enforce_auth_rate_limit),
) -> RegistrationResponse:
  service = build_identity_service(
    session,
    redis,
  )
  return await service.register(
    first_name=payload.first_name,
    last_name=payload.last_name,
    email=payload.email,
    organization_name=payload.organization_name,
    password=payload.password,
    password_confirmation=payload.password_confirmation,
  )

@router.post(
  "/login",
  response_model=LoginResponse,
)
async def login(
  payload: LoginRequest,
  session: AsyncSession = Depends(get_db),
  redis: Redis = Depends(get_redis),
  _: None = Depends(enforce_auth_rate_limit),
) -> LoginResponse:
  service = build_identity_service(
    session,
    redis,
  )
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
  redis: Redis = Depends(get_redis),
) -> TokenResponse:
  service = build_identity_service(session, redis,)

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
  redis: Redis = Depends(get_redis),
) -> MessageResponse:
  service = build_identity_service(session, redis,)

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
  redis: Redis = Depends(get_redis),
) -> MessageResponse:
  service = build_identity_service(session, redis,)
  await service.logout_all(
    current_user.id
  )
  return MessageResponse(
    message="All active sessions have been revoked."
  )

@router.post(
  "/forgot-password",
  response_model=MessageResponse,
)
async def forgot_password(
  payload: ForgotPasswordRequest,
  session: AsyncSession = Depends(get_db),
  redis: Redis = Depends(get_redis),
  _: None = Depends(enforce_auth_rate_limit),
) -> MessageResponse:
  service = build_identity_service(
    session,
    redis,
  )
  await service.forgot_password(
    email=payload.email,
  )
  return MessageResponse(
    message=(
      "If an account exists for that email, "
      "password reset instructions have been sent."
    )
  )

@router.post(
  "/reset-password",
  response_model=MessageResponse,
)
async def reset_password(
  payload: ResetPasswordRequest,
  session: AsyncSession = Depends(get_db),
  redis: Redis = Depends(get_redis),
) -> MessageResponse:
  service = build_identity_service(
    session,
    redis,
  )
  await service.reset_password(
    token=payload.token,
    new_password=payload.password,
  )
  return MessageResponse(
    message="Password has been reset successfully."
  )

@router.post(
  "/verify-email",
  response_model=MessageResponse,
)
async def verify_email(
  payload: VerifyEmailRequest,
  session: AsyncSession = Depends(get_db),
  redis: Redis = Depends(get_redis),
) -> MessageResponse:
  service = build_identity_service(
    session,
    redis,
  )
  await service.verify_email(
    token=payload.token,
  )
  return MessageResponse(
    message="Email address verified successfully."
  )

@router.post(
  "/resend-verification",
  response_model=MessageResponse,
)
async def resend_verification(
  payload: ResendVerificationRequest,
  session: AsyncSession = Depends(get_db),
  redis: Redis = Depends(get_redis),
  _: None = Depends(enforce_auth_rate_limit),
) -> MessageResponse:
  service = build_identity_service(
    session,
    redis,
  )
  await service.resend_verification(
    email=payload.email,
  )
  return MessageResponse(
    message=(
      "If the account exists and is not verified, "
      "a new verification email has been sent."
    )
  )

@router.post(
  "/change-password",
  response_model=MessageResponse,
)
async def change_password(
  payload: ChangePasswordRequest,
  current_user: User = Depends(
    get_current_user
  ),
  session: AsyncSession = Depends(get_db),
  redis: Redis = Depends(get_redis),
) -> MessageResponse:
  service = build_identity_service(session, redis,)

  await service.change_password(
    user=current_user,
    current_password=payload.current_password,
    new_password=payload.new_password,
    new_password_confirmation=(
      payload.new_password_confirmation
    ),
  )
  return MessageResponse(
    message="Password changed successfully."
  )