from __future__ import annotations
from datetime import datetime, timedelta, timezone
import uuid
import jwt
import pytest
from app.core.config import settings
from app.core.security import create_access_token, decode_token, hash_password, verify_password
from app.modules.identity.enums import TokenType

@pytest.mark.unit
class TestPasswordHashing:
  def test_hash_and_verify_roundtrip(self):
    raw = "SecurePass123!"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True

  def test_verify_rejects_wrong_password(self):
    hashed = hash_password("CorrectHorseBattery!")
    assert verify_password("wrong-password", hashed) is False

@pytest.mark.unit
class TestTokenCreationAndDecode:
  def test_access_token_contains_expected_claims(self):
    subject = str(uuid.uuid4())
    org_id = str(uuid.uuid4())
    token = create_access_token(subject=subject, organization_id=org_id)
    payload = decode_token(token)

    assert payload["sub"] == subject
    assert payload["org_id"] == org_id
    assert payload["type"] == TokenType.ACCESS
    assert "iat" in payload
    assert "exp" in payload

  def test_decode_rejects_wrong_secret(self):
    token = jwt.encode(
      {
        "sub": "u1",
        "type": "access",
        "org_id": "o1",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
      },
      "completely-wrong-secret",
      algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(jwt.InvalidTokenError):
      decode_token(token)