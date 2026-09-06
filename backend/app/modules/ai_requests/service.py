from __future__ import annotations
import base64
import json
import time
from dataclasses import dataclass
from uuid import UUID, uuid4
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.modules.ai_requests.models import AIEntityType, AIProvider, AIRequest, AIRequestPurpose, AIResponse, AIResponseStatus
from app.modules.ai_requests.repository import AIRequestRepository, AIResponseRepository
from app.modules.identity.models import Organization
from app.modules.subscriptions.service import SubscriptionService

@dataclass
class AIRunResult:
  success: bool
  parsed_output: dict | None = None
  raw_response: str | None = None
  error_message: str | None = None

class AIOrchestratorService:
  SUPPORTED_PROVIDERS = {AIProvider.OLLAMA, AIProvider.ANTHROPIC}
  
  def __init__(self, session: AsyncSession):
    self.session = session
    self.requests = AIRequestRepository(session)
    self.responses = AIResponseRepository(session)
    self.subscriptions = SubscriptionService(session)

  async def run(
   self,
   *,
   organization_id: UUID,
   purpose: AIRequestPurpose,
   prompt: str,
   entity_type: AIEntityType | None = None,
   entity_id: UUID | None = None,
   requested_by: UUID | None = None,
   model: str | None = None,
   image_bytes: bytes | None = None,
   image_mime_type: str | None = None,
) -> AIRunResult:
   if not await self._is_ai_enabled(organization_id):
    return AIRunResult(
      success=False, error_message="AI is not enabled for this organization."
    )

   provider = AIProvider(settings.ai_provider.upper())
   if provider not in self.SUPPORTED_PROVIDERS:
    return AIRunResult(
      success=False,
      error_message=f"AI provider {provider.value} is not yet implemented.",
    )

   try:
    await self.subscriptions.check_quota(organization_id, "ai_requests")
   except Exception as exc:
    return AIRunResult(success=False, error_message=str(exc))

   resolved_model = model or (
    settings.ollama_model if provider == AIProvider.OLLAMA else settings.ai_model
  )

   ai_request = await self.requests.create(
    AIRequest(
      id=uuid4(),
      organization_id=organization_id,
      purpose=purpose,
      entity_type=entity_type,
      entity_id=entity_id,
      provider=provider,
      model=resolved_model,
      prompt_text=prompt,
      requested_by=requested_by,
    )
  )
   await self.session.commit()

   started_at = time.monotonic()
   try:
    raw_response, parsed_output = await self._call_provider(
      provider, resolved_model, prompt, image_bytes, image_mime_type,
    )
    latency_ms = int((time.monotonic() - started_at) * 1000)

    await self.responses.create(
      AIResponse(
        id=uuid4(),
        ai_request_id=ai_request.id,
        status=AIResponseStatus.SUCCEEDED,
        raw_response=raw_response,
        parsed_output=parsed_output,
        latency_ms=latency_ms,
      )
    )
    await self.subscriptions.increment_usage(organization_id, "ai_requests")
    await self.session.commit()
    return AIRunResult(
      success=True, parsed_output=parsed_output, raw_response=raw_response
    )

   except Exception as exc:
    latency_ms = int((time.monotonic() - started_at) * 1000)
    await self.responses.create(
      AIResponse(
        id=uuid4(),
        ai_request_id=ai_request.id,
        status=AIResponseStatus.FAILED,
        error_message=str(exc)[:2000],
        latency_ms=latency_ms,
      )
    )
    await self.subscriptions.increment_usage(organization_id, "ai_requests")
    await self.session.commit()
    return AIRunResult(success=False, error_message=str(exc))

  async def _is_ai_enabled(self, organization_id: UUID) -> bool:
    result = await self.session.execute(
      select(Organization.ai_enabled).where(
        Organization.id == organization_id
      )
    )
    return bool(result.scalar_one_or_none())

  async def _call_provider(
    self, provider: AIProvider, model: str, prompt: str,
    image_bytes: bytes | None = None, image_mime_type: str | None = None,
  ) -> tuple[str, dict | None]:
    if provider == AIProvider.OLLAMA:
     return await self._call_ollama(model, prompt, image_bytes, image_mime_type)
    if provider == AIProvider.ANTHROPIC:
     return await self._call_anthropic(model, prompt, image_bytes, image_mime_type)
    raise NotImplementedError(
     f"AI provider {provider.value} is not yet implemented."
   )

  @staticmethod
  async def _call_ollama(
    model: str, prompt: str,
    image_bytes: bytes | None = None, image_mime_type: str | None = None,
  ) -> tuple[str, dict | None]:
    payload: dict = {
      "model": model,
      "prompt": prompt,
      "stream": False,
      "format": "json",
    }
    if image_bytes is not None:
      payload["images"] = [base64.b64encode(image_bytes).decode("ascii")]

    async with httpx.AsyncClient(timeout=30.0) as client:
      response = await client.post(
        f"{settings.ollama_base_url}/api/generate",
        json=payload,
      )
      response.raise_for_status()
      raw_text = response.json()["response"]
      try:
        parsed = json.loads(raw_text)
      except (json.JSONDecodeError, TypeError):
        parsed = None
      return raw_text, parsed
   
  @staticmethod
  async def _call_anthropic(
    model: str, prompt: str,
    image_bytes: bytes | None = None, image_mime_type: str | None = None,
  ) -> tuple[str, dict | None]:
   if not settings.ai_api_key:
    raise RuntimeError("AI_API_KEY is not configured for the Anthropic provider.")

   content: list[dict] = []
   if image_bytes is not None and image_mime_type is not None:
    content.append({
      "type": "image",
      "source": {
        "type": "base64",
        "media_type": image_mime_type,
        "data": base64.b64encode(image_bytes).decode("ascii"),
      },
    })
   content.append({"type": "text", "text": prompt})

   async with httpx.AsyncClient(timeout=180.0) as client:
    response = await client.post(
      "https://api.anthropic.com/v1/messages",
      headers={
        "x-api-key": settings.ai_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
      },
      json={
        "model": model,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": content}],
      },
    )
    response.raise_for_status()
    payload = response.json()
    raw_text = "".join(
      block.get("text", "")
      for block in payload.get("content", [])
      if block.get("type") == "text"
    )
    try:
      parsed = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
      parsed = None
    return raw_text, parsed  

  async def list_requests(
    self, organization_id: UUID, **kwargs
  ) -> list[AIRequest]:
    return await self.requests.list_by_org(organization_id, **kwargs)

  async def get_usage_summary(self, organization_id: UUID) -> dict:
    return await self.requests.get_usage_summary(organization_id)