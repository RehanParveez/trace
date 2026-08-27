from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.permissions import require_permission
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from app.modules.subscriptions.schemas import CancelSubscriptionRequest,ChangePlanRequest, PlanResponse, SubscriptionResponse, UsageResponse
from app.modules.subscriptions.service import SubscriptionService

router = APIRouter(
  prefix="/subscriptions",
  tags=["Subscriptions"],
)

def _service(
  session: AsyncSession,
) -> SubscriptionService:
  return SubscriptionService(session)

@router.get(
  "/plans",
  response_model=list[PlanResponse],
)
async def list_plans(
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.list_plans()

@router.get(
  "/me",
  response_model=SubscriptionResponse,
)
async def get_subscription(
  current_user: User = Depends(
    require_permission(
      PermissionKey.SUBSCRIPTION_READ
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.get_subscription(
    current_user.organization_id
  )

@router.get(
  "/me/usage",
  response_model=UsageResponse,
)
async def get_usage(
  current_user: User = Depends(
    require_permission(
      PermissionKey.SUBSCRIPTION_READ
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.get_usage(
    current_user.organization_id
  )

@router.patch(
  "/me/plan",
  response_model=SubscriptionResponse,
)
async def change_plan(
  payload: ChangePlanRequest,
  current_user: User = Depends(
    require_permission(
      PermissionKey.SUBSCRIPTION_MANAGE
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.change_plan(
    current_user.organization_id,
    payload,
  )

@router.post(
  "/me/cancel",
  response_model=SubscriptionResponse,
)
async def cancel_subscription(
  payload: CancelSubscriptionRequest,
  current_user: User = Depends(
    require_permission(
      PermissionKey.SUBSCRIPTION_BILLING_MANAGE
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.cancel_subscription(
    current_user.organization_id,
    payload.cancel_at_period_end,
  )