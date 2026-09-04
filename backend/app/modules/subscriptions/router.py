from __future__ import annotations
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.permissions import require_permission, require_platform_admin
from app.dependencies.tenancy import scope_session_as_platform_admin
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from app.modules.subscriptions.models import SubscriptionStatus
from app.modules.subscriptions.repository import SubscriptionRepository
from app.modules.subscriptions.schemas import (CancelSubscriptionRequest, ChangePlanRequest, PlanResponse, SubscriptionListResponse,
  SubscriptionResponse, SubscriptionSummaryResponse, UsageResponse,
)
from app.modules.subscriptions.service import SubscriptionService
from app.shared.idempotency import get_cached_response, store_response

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
    current_user.active_membership.organization_id
  )

@router.get(
  "/me/summary",
  response_model=SubscriptionSummaryResponse,
)
async def get_subscription_summary(
  current_user: User = Depends(
    require_permission(
      PermissionKey.SUBSCRIPTION_READ
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  subscription = await service.get_subscription_summary(current_user.active_membership.organization_id)
  return SubscriptionSummaryResponse(subscription=subscription, plan=subscription.plan)

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
    current_user.active_membership.organization_id
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
  idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
  organization_id = current_user.active_membership.organization_id
  scope = "subscription_change_plan"

  if idempotency_key:
    cached = await get_cached_response(organization_id, scope, idempotency_key)
    if cached is not None:
      return SubscriptionResponse(**cached)

  service = _service(session)
  subscription = await service.change_plan(organization_id, payload, current_user.id)
  response = SubscriptionResponse.model_validate(subscription)

  if idempotency_key:
    await store_response(organization_id, scope, idempotency_key, response.model_dump())

  return response

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
  idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
  organization_id = current_user.active_membership.organization_id
  scope = "subscription_cancel"

  if idempotency_key:
    cached = await get_cached_response(organization_id, scope, idempotency_key)
    if cached is not None:
      return SubscriptionResponse(**cached)

  service = _service(session)
  subscription = await service.cancel_subscription(organization_id, payload.cancel_at_period_end)
  response = SubscriptionResponse.model_validate(subscription)

  if idempotency_key:
    await store_response(organization_id, scope, idempotency_key, response.model_dump())

  return response

@router.post(
  "/me/reactivate",
  response_model=SubscriptionResponse,
)
async def reactivate_subscription(
  current_user: User = Depends(
    require_permission(
      PermissionKey.SUBSCRIPTION_BILLING_MANAGE
    )
  ),
    session: AsyncSession = Depends(get_db),
):
  organization_id = current_user.active_membership.organization_id

  service = _service(session)
  subscription = await service.reactivate_subscription(
    organization_id
  )

  return SubscriptionResponse.model_validate(subscription)

@router.get("/admin", response_model=SubscriptionListResponse)
async def list_all_subscriptions(
  status_filter: SubscriptionStatus | None = Query(default=None, alias="status"),
  page: int = Query(default=1, ge=1),
  page_size: int = Query(default=20, ge=1, le=100),
  _admin: User = Depends(require_platform_admin()),
  session: AsyncSession = Depends(get_db),
):
  await scope_session_as_platform_admin(session)

  repository = SubscriptionRepository(session)
  offset = (page - 1) * page_size
  items, total = await repository.list_all_subscriptions(
    status=status_filter, limit=page_size, offset=offset,
  )

  return SubscriptionListResponse(
    items=[SubscriptionResponse.model_validate(item) for item in items],
    total=total,
    page=page,
    page_size=page_size,
  )