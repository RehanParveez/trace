from __future__ import annotations
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.modules.ai_requests.models import AIEntityType, AIRequest, AIRequestPurpose, AIResponse,AIResponseStatus

class AIRequestRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(self, request: AIRequest) -> AIRequest:
    self.session.add(request)
    await self.session.flush()
    return request

  async def list_by_org(
    self,
    organization_id: UUID,
    *,
    purpose: AIRequestPurpose | None = None,
    entity_type: AIEntityType | None = None,
    entity_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
  ) -> list[AIRequest]:
    query = (
      select(AIRequest)
      .where(AIRequest.organization_id == organization_id)
      .options(selectinload(AIRequest.response))
    )
    if purpose is not None:
      query = query.where(AIRequest.purpose == purpose)
    if entity_type is not None:
      query = query.where(AIRequest.entity_type == entity_type)
    if entity_id is not None:
      query = query.where(AIRequest.entity_id == entity_id)

    query = (
      query
      .order_by(AIRequest.created_at.desc())
      .offset(skip)
      .limit(limit)
    )
    result = await self.session.execute(query)
    return list(result.scalars().unique())

  async def get_usage_summary(self, organization_id: UUID) -> dict:
    result = await self.session.execute(
      select(
        func.count(AIRequest.id),
        func.count(AIResponse.id).filter(
          AIResponse.status == AIResponseStatus.SUCCEEDED
        ),
        func.count(AIResponse.id).filter(
          AIResponse.status == AIResponseStatus.FAILED
        ),
        func.avg(AIResponse.latency_ms),
      )
      .select_from(AIRequest)
      .join(
        AIResponse,
        AIResponse.ai_request_id == AIRequest.id,
        isouter=True,
      )
      .where(AIRequest.organization_id == organization_id)
    )
    total, succeeded, failed, avg_latency = result.one()
    return {
      "total_requests": total or 0,
      "succeeded": succeeded or 0,
      "failed": failed or 0,
      "average_latency_ms": (
        float(avg_latency) if avg_latency is not None else None
      ),
    }

class AIResponseRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(self, response: AIResponse) -> AIResponse:
    self.session.add(response)
    await self.session.flush()
    return response