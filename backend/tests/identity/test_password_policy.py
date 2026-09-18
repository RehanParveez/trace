from __future__ import annotations
import pytest
from app.core.exceptions import TraceException
from app.modules.identity.password_policy import validate_password

@pytest.mark.unit
class TestPasswordPolicy:
  def test_accepts_strong_password(self):
    validate_password("StrongPass123!")

  def test_rejects_too_short(self):
    with pytest.raises(TraceException) as exc:
      validate_password("Short1!")
    assert exc.value.code == "WEAK_PASSWORD"
    assert "12 characters" in exc.value.message

  def test_rejects_too_long(self):
    with pytest.raises(TraceException) as exc:
      validate_password("A1!" + "x" * 130)
    assert exc.value.code == "WEAK_PASSWORD"

  def test_rejects_missing_uppercase(self):
    with pytest.raises(TraceException) as exc:
      validate_password("nouppercase1!")
    assert "uppercase" in exc.value.message.lower()

  def test_rejects_missing_lowercase(self):
    with pytest.raises(TraceException) as exc:
      validate_password("NOLOWERCASE1!")
    assert "lowercase" in exc.value.message.lower()

  def test_rejects_missing_digit(self):
    with pytest.raises(TraceException) as exc:
      validate_password("NoDigitsHere!")
    assert "number" in exc.value.message.lower()

  def test_rejects_missing_special(self):
    with pytest.raises(TraceException) as exc:
      validate_password("NoSpecialChar1")
    assert "special" in exc.value.message.lower()