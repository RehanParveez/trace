from __future__ import annotations
import re
from app.core.exceptions import TraceException

COMMON_PASSWORDS = {
  "password",
  "password123",
  "password123!",
  "admin123",
  "admin123!",
  "qwerty123",
  "12345678",
  "123456789",
  "1234567890",
}

def validate_password(
  password: str,
  *,
  email: str | None = None,
  first_name: str | None = None,
  last_name: str | None = None,
) -> None:
  if len(password) < 12:
    raise TraceException(
      "Password must contain at least 12 characters.",
      status_code=422,
      code = "WEAK_PASSWORD",
    )
  if len(password) > 128:
    raise TraceException(
      "Password is too long.",
      status_code=422,
      code = "WEAK_PASSWORD",
    )
  lowered = password.lower()

  if lowered in COMMON_PASSWORDS:
    raise TraceException(
      "Password is too common.",
      status_code=422,
      code = "WEAK_PASSWORD",
    )
  identity_values = [
    email,
    first_name,
    last_name,
  ]

  for value in identity_values:
    if value:
      normalized = value.lower().strip()

      if len(normalized) >= 4 and normalized in lowered:
        raise TraceException(
          "Password must not contain personal information.",
          status_code=422,
          code = "WEAK_PASSWORD",
        )

  if not re.search(r"[A-Z]", password):
    raise TraceException(
      "Password must contain an uppercase letter.",
      status_code=422,
      code = "WEAK_PASSWORD",
    )
  if not re.search(r"[a-z]", password):
    raise TraceException(
      "Password must contain a lowercase letter.",
      status_code=422,
      code = "WEAK_PASSWORD",
    )
  if not re.search(r"\d", password):
    raise TraceException(
      "Password must contain a number.",
      status_code=422,
      code = "WEAK_PASSWORD",
    )
  if not re.search(r"[^\w\s]", password):
    raise TraceException(
      "Password must contain a special character.",
      status_code=422,
      code = "WEAK_PASSWORD",
    )