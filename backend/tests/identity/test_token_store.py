from __future__ import annotations
import pytest
from app.modules.identity.token_store import IdentityTokenStore
from tests.conftest import FakeRedis

@pytest.mark.unit
@pytest.mark.asyncio
class TestIdentityTokenStore:
  async def test_create_and_consume_roundtrip(self, fake_redis: FakeRedis):
    store = IdentityTokenStore(fake_redis)
    token = await store.create(
      prefix="email-verification",
      user_id="user-2368",
      ttl_seconds=60,
    )
    assert isinstance(token, str)
    assert len(token) > 20

    consumed = await store.consume(prefix="email-verification", token=token)
    assert consumed == "user-2368"

    again = await store.consume(prefix="email-verification", token=token)
    assert again is None