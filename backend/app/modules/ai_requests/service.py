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
  ai_request_id: UUID | None = None
  input_tokens: int | None = None
  output_tokens: int | None = None
  model: str | None = None
  provider: str | None = None
  seconds: float | None = None

@dataclass
class AIState:
  enabled: bool
  consent: str
  provider: AIProvider | None = None
  model: str | None = None

  @property
  def ready(self) -> bool:
    return self.enabled and self.provider is not None

CONSENT_OFF, CONSENT_LOCAL, CONSENT_OUTSIDE = "OFF", "LOCAL", "OUTSIDE"
CONSENTS = (CONSENT_OFF, CONSENT_LOCAL, CONSENT_OUTSIDE)
CONSENT_PROVIDER = {CONSENT_LOCAL: AIProvider.OLLAMA, CONSENT_OUTSIDE: AIProvider.ANTHROPIC}
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TIMEOUT_S = {AIProvider.OLLAMA: 30.0, AIProvider.ANTHROPIC: 180.0}

def model_of(provider: AIProvider) -> str:
  return settings.ollama_model if provider == AIProvider.OLLAMA else settings.ai_model

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
   images: list[bytes] | None = None,
   max_tokens: int | None = None,
   timeout_s: float | None = None,
) -> AIRunResult:
   state = await self.state(organization_id)
   if not state.enabled:
    return AIRunResult(
      success=False, error_message="AI is not enabled for this organization."
    )
   if state.provider is None:
    return AIRunResult(
      success=False, error_message="AI consent is OFF for this organization."
    )

   provider = state.provider
   if provider not in self.SUPPORTED_PROVIDERS:
    return AIRunResult(
      success=False,
      error_message=f"AI provider {provider.value} is not yet implemented.",
    )
    
   if provider == AIProvider.ANTHROPIC and not settings.ai_api_key:
      return AIRunResult(
        success=False,
        error_message="AI_API_KEY is not configured for the Anthropic provider.",
      )
   try:
    await self.subscriptions.check_quota(organization_id, "ai_requests")
   except Exception as exc:
    return AIRunResult(success=False, error_message=str(exc))

   resolved_model = model or model_of(provider)
   pictures = ([(image_bytes, image_mime_type or "image/png")] if image_bytes is not None else []) + [(png, "image/png") for png in (images or [])]

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
    called = await self._call_provider(
      provider, resolved_model, prompt, pictures, max_tokens or DEFAULT_MAX_TOKENS, timeout_s or DEFAULT_TIMEOUT_S[provider],
    )
    raw_response, parsed_output = called[0], called[1]
    usage = called[2] if len(called) > 2 and called[2] else {}
    latency_ms = int((time.monotonic() - started_at) * 1000)
    ai_request.input_tokens = usage.get("input_tokens")
    ai_request.output_tokens = usage.get("output_tokens")

    await self.responses.create(
      AIResponse(
        id=uuid4(),
        organization_id=organization_id,
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
      success=True, parsed_output=parsed_output, raw_response=raw_response, ai_request_id=ai_request.id,
      input_tokens=ai_request.input_tokens, output_tokens=ai_request.output_tokens, model=resolved_model, provider=provider.value, seconds=latency_ms / 1000.0,
    )

   except Exception as exc:
    latency_ms = int((time.monotonic() - started_at) * 1000)
    await self.responses.create(
      AIResponse(
        id=uuid4(),
        organization_id=organization_id,
        ai_request_id=ai_request.id,
        status=AIResponseStatus.FAILED,
        error_message=str(exc)[:2000],
        latency_ms=latency_ms,
      )
    )
    await self.subscriptions.increment_usage(organization_id, "ai_requests")
    await self.session.commit()
    return AIRunResult(success=False, error_message=str(exc), ai_request_id=ai_request.id, model=resolved_model, provider=provider.value, seconds=latency_ms / 1000.0)

  async def state(self, organization_id: UUID) -> AIState:
    row = (await self.session.execute(
      select(Organization.ai_enabled, Organization.ai_consent).where(Organization.id == organization_id)
    )).one_or_none()
    if row is None:
      return AIState(enabled=False, consent=CONSENT_OFF)
    enabled, consent = bool(row[0]), str(row[1] or CONSENT_OFF).upper()
    provider = CONSENT_PROVIDER.get(consent)
    return AIState(enabled=enabled, consent=consent, provider=provider, model=model_of(provider) if provider else None)

  @staticmethod
  async def _call_provider(
    provider: AIProvider, model: str, prompt: str,
    pictures: list | None = None, max_tokens: int = DEFAULT_MAX_TOKENS, timeout_s: float | None = None,
  ) -> tuple[str, dict | None, dict]:
    pictures = pictures or []
    timeout = timeout_s or DEFAULT_TIMEOUT_S.get(provider, 30.0)
    if provider == AIProvider.OLLAMA:
     return await AIOrchestratorService._call_ollama(model, prompt, pictures, max_tokens, timeout)
    if provider == AIProvider.ANTHROPIC:
     return await AIOrchestratorService._call_anthropic(model, prompt, pictures, max_tokens, timeout)
    raise NotImplementedError(
     f"AI provider {provider.value} is not yet implemented."
   )

  @staticmethod
  async def _call_ollama(
    model: str, prompt: str, pictures: list, max_tokens: int, timeout_s: float,
  ) -> tuple[str, dict | None, dict]:
    payload: dict = {
      "model": model,
      "prompt": prompt,
      "stream": False,
      "format": "json",
      "options": {"num_predict": int(max_tokens)},
    }
    if pictures:
      payload["images"] = [base64.b64encode(data).decode("ascii") for data, _mime in pictures]

    async with httpx.AsyncClient(timeout=timeout_s) as client:
      response = await client.post(
        f"{settings.ollama_base_url}/api/generate",
        json=payload,
      )
      response.raise_for_status()
      body = response.json()
      raw_text = body["response"]
      try:
        parsed = json.loads(raw_text)
      except (json.JSONDecodeError, TypeError):
        parsed = None
      usage = {"input_tokens": body.get("prompt_eval_count"), "output_tokens": body.get("eval_count")}
      return raw_text, parsed, usage
   
  @staticmethod
  async def _call_anthropic(
    model: str, prompt: str, pictures: list, max_tokens: int, timeout_s: float,
  ) -> tuple[str, dict | None, dict]:
   if not settings.ai_api_key:
    raise RuntimeError("AI_API_KEY is not configured for the Anthropic provider.")

   content: list[dict] = []
   for data, mime in pictures:
    content.append({
      "type": "image",
      "source": {
        "type": "base64",
        "media_type": mime,
        "data": base64.b64encode(data).decode("ascii"),
      },
    })
   content.append({"type": "text", "text": prompt})

   async with httpx.AsyncClient(timeout=timeout_s) as client:
    response = await client.post(
      settings.ai_anthropic_url,
      headers={
        "x-api-key": settings.ai_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
      },
      json={
        "model": model,
        "max_tokens": int(max_tokens),
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
    used = payload.get("usage") or {}
    return raw_text, parsed, {"input_tokens": used.get("input_tokens"), "output_tokens": used.get("output_tokens")}  

  async def list_requests(
    self, organization_id: UUID, **kwargs
  ) -> list[AIRequest]:
    return await self.requests.list_by_org(organization_id, **kwargs)

  async def get_usage_summary(self, organization_id: UUID) -> dict:
    return await self.requests.get_usage_summary(organization_id)