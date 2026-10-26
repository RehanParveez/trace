from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.ai_reader.contract import KEYS, TEXT_KEYS

AGREE, DISAGREE, AI_ONLY, RULE_ONLY = "AGREE", "DISAGREE", "AI_ONLY", "RULE_ONLY"
AGREEMENTS = (AGREE, DISAGREE, AI_ONLY, RULE_ONLY)

def _norm(value) -> str:
  return re.sub(r"[^A-Z0-9]+", " ", str(value).upper()).strip()

def _empty(value) -> bool:
  return value is None or str(value).strip() == ""

def compare(rule: dict | None, ai: dict | None) -> list[dict]:
  rule, ai = rule or {}, ai or {}
  out: list[dict] = []

  for key in KEYS:
    r, a = rule.get(key), ai.get(key)
    if _empty(r) and _empty(a):
      continue
    if _empty(r):
      verdict = AI_ONLY
      
    elif _empty(a):
      verdict = RULE_ONLY
    elif key in TEXT_KEYS:
      rn, an = _norm(r), _norm(a)
      verdict = AGREE if rn and an and (rn == an or rn in an or an in rn) else DISAGREE
    else:
      verdict = AGREE if str(r).upper() == str(a).upper() else DISAGREE
    out.append({"fact_key": key, "rule_value": None if _empty(r) else r, "ai_value": None if _empty(a) else a, "agreement": verdict})
  return out

def totals(records: list[dict]) -> dict:
  out = {k: 0 for k in AGREEMENTS}
  for r in records:
    out[r["agreement"]] = out.get(r["agreement"], 0) + 1
  return out
