from __future__ import annotations

OTHER = "OTHER"
REASONS = {
  "correct": ("WRONG_NUMBER", "WRONG_UNIT", "WRONG_NAME", "WRONG_FLOOR", OTHER),
  "reject": ("NOT_ON_DRAWING", "ALREADY_COUNTED", "NOT_FOR_THIS_JOB", "DRAWING_IS_WRONG", OTHER),
}

def allowed(action: str) -> tuple:
  return REASONS.get(action, ())

def check(action: str, reason) -> tuple:
  if reason is None or not str(reason).strip():
    return None, None
  given = str(reason).strip().upper()
  if given not in allowed(action):
    return None, f"{given} is not a reason for '{action}'." + (f" Choose one of: {', '.join(allowed(action))}." if allowed(action) else " That action takes no reason.")
  return given, None
