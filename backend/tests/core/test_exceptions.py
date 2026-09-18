from __future__ import annotations
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from app.core.exceptions import TraceException, trace_exception_handler

@pytest.mark.unit
def test_trace_exception_attributes():
  exc = TraceException("Something broke", status_code=422, code="CUSTOM_CODE")
  assert exc.message == "Something broke"
  assert exc.status_code == 422
  assert exc.code == "CUSTOM_CODE"
  assert str(exc) == "Something broke"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_exception_handler_returns_structured_json():
  app = FastAPI()
  app.add_exception_handler(TraceException, trace_exception_handler)

  @app.get("/boom")
  async def boom():
    raise TraceException("Nope", status_code=403, code="FORBIDDEN_ACTION")

  transport = ASGITransport(app=app)
  async with AsyncClient(transport=transport, base_url="http://test") as client:
    resp = await client.get("/boom")

  assert resp.status_code == 403
  assert resp.json() == {
    "error": {"code": "FORBIDDEN_ACTION", "message": "Nope"}
  }