from __future__ import annotations
import hashlib
import re
from app.modules.drawings_boq.takeoff import corrections as CR
from app.modules.drawings_boq.takeoff.learning import pattern as PT

REVIEW_KINDS = (CR.REVIEW_ACCEPTED, CR.REVIEW_CORRECTED, CR.REVIEW_REJECTED)
IDENTITY_FIELDS = ("role", "plan_kind", "floor", "discipline", "sheet_type")
MAX_TEXT = 60
_EMAIL = re.compile(r"\S+@\S+")
_LONG_DIGITS = re.compile(r"\d{5,}")

def source_of(org, salt: str) -> str:
  return hashlib.sha256(f"{salt}:{org}".encode("utf-8")).hexdigest()[:10]

def clean(text) -> str:
  out = _LONG_DIGITS.sub("#", _EMAIL.sub("", str(text if text is not None else "")))
  return re.sub(r"\s+", " ", out).strip()[:MAX_TEXT]

def review_record(row, source: str) -> dict | None:
  ctx = row.context or {}
  
  task = ctx.get("task")
  if row.kind not in REVIEW_KINDS or not task:
    return None
  action = {CR.REVIEW_ACCEPTED: "accept", CR.REVIEW_CORRECTED: "correct", CR.REVIEW_REJECTED: "reject"}[row.kind]
  before, after = (row.before or {}).get("read"), (row.after or {}).get("value")
  out = {"source": source, "type": "REVIEW", "task": task, "action": action, "reason": ctx.get("reason"), "subject": clean(ctx.get("subject")),
    "from": PT.shape(before), "to": PT.shape(after) if action == "correct" else None}
  if task == PT.LEGEND_ENTRY:
    out["label"] = clean((row.before or {}).get("label"))
    out["to_text"] = clean(after) if action == "correct" else None
  return out

def identity_record(row, source: str) -> list:
  before, after = row.before or {}, row.after or {}
  out = []
  
  for f in IDENTITY_FIELDS:
    a, b = before.get(f), after.get(f)
    if a is not None and b is not None and a != b and (f in (after.get("person_set") or [])):
      out.append({"source": source, "type": "IDENTITY", "field": f, "from": clean(a), "to": clean(b)})
  return out

def records(rows: list, source: str) -> list:
  out: list = []
  for r in rows:
    if r.kind == CR.IDENTITY_SET:
      out += identity_record(r, source)
    else:
      one = review_record(r, source)
      if one:
        out.append(one)
  return out
