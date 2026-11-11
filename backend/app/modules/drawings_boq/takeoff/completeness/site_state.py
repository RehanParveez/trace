from __future__ import annotations
from app.engine.catalogue import site_inputs as SI
from app.engine.catalogue import model as CM
from app.engine.catalogue import choices as CH
from app.engine.measure import rule_registry as RR
from app.modules.drawings_boq.takeoff.questions import keys as QK

RULE = "SITE_INPUTS_ASKED"
MEASURED, ASSUMED, ASKED, NOT_APPLICABLE, NOT_READ = CM.STATES
NOT_DRAWN = "NOT_DRAWN"
WAITS_ON = "SITE_INPUT"
PRINTED = "SITE_PRINTED"
NOT_BILLED = "SITE_NOT_BILLED"
ANSWERED = "ANSWERED"

def _given(answers: dict, key: str):
  row = (answers or {}).get(key)
  return None if row is None else (row.get("value") if isinstance(row, dict) else row)

def _widen(quantity: dict | None, assumptions: list) -> dict | None:
  if not quantity:
    return quantity
  lo = hi = 1.0
  for a in assumptions:
    s = SI.get(str(a.get("rule")))
    if s and s.get("proportional") and a.get("range") and a.get("value"):
      lo *= a["range"][0] / a["value"]
      hi *= a["range"][1] / a["value"]
  if lo == hi == 1.0:
    return quantity
  base = quantity.get("range") or [quantity["value"], quantity["value"]]
  return {**quantity, "range": [round(base[0] * lo, 3), round(base[1] * hi, 3)]}

def _question(s: dict) -> dict:
  return {"about": s["id"].lower(), "ask": s["asks"], "key": SI.key_of(s["id"]), "kind": QK.SITE, "site": s["id"]}

def _split(item, waits: list, ctx: dict, evidence: dict, use: bool, floor: str | None) -> tuple:
  asks, assumed, reasons, left_out = [], [], [], []
  for s in waits:
    key = SI.key_of(s["id"])
    got = _given(ctx["answers"], key)
    if got is not None and SI.check(s["id"], got) is None:
      reasons.append(f"{ANSWERED}:{key}")
    elif SI.printed_value(s["id"], evidence.get("printed")) is not None:
      reasons.append(f"{PRINTED}:{s['id']}")
    elif use and s.get("fallback"):
      if s["fallback"]["kind"] == SI.NOT_BILLED:
        left_out.append(s["id"])
      else:
        assumed.append(SI.fallback_assumption(s["id"], item.id, floor))
    else:
      asks.append(s)
  return asks, assumed, reasons, left_out

def _one(item, e: dict, waits: list, ctx: dict, evidence: dict, use: bool) -> dict:
  floor = None if e["floor"] == "ALL" else e["floor"]
  asks, assumed, reasons, left_out = _split(item, waits, ctx, evidence, use, floor)
  if e["state"] == ASKED:
    if not item.derived:
      return e
    have = {q.get("key") for q in e["questions"]}
    more = [s for s in asks if SI.key_of(s["id"]) not in have]
    if not more:
      return e
    return {**e, "reasons": list(dict.fromkeys(e["reasons"] + [f"{WAITS_ON}:{s['id']}" for s in more])), "questions": list(e["questions"]) + [_question(s) for s in more]}

  live = e["state"] in (MEASURED, ASSUMED)
  undrawn = e["state"] == NOT_READ and NOT_DRAWN in e["reasons"]
  if not (live or undrawn):
    return e
  waiting = [f"{WAITS_ON}:{s['id']}" for s in asks]
  if asks:
    return {**e, "state": ASKED, "reasons": list(dict.fromkeys(e["reasons"] + waiting + reasons)), "questions": list(e["questions"]) + [_question(s) for s in asks]}
  if left_out and undrawn and not assumed:
    return {**e, "state": NOT_APPLICABLE, "reasons": list(dict.fromkeys(e["reasons"] + [f"{NOT_BILLED}:{i}" for i in left_out] + reasons))}
  if assumed and live:
    every = list(e["assumptions"]) + assumed
    return {**e, "state": ASSUMED, "quantity": _widen(e["quantity"], every), "assumptions": every, "reasons": list(dict.fromkeys(e["reasons"] + [f"SITE_DEFAULT:{a['rule']}" for a in assumed] + reasons))}
  return {**e, "reasons": list(dict.fromkeys(e["reasons"] + reasons))} if reasons else e

def apply(item, entries: list, ctx: dict, evidence: dict) -> list:
  if not RR.on(RULE):
    return entries
  waits = SI.waiting_on(item.id)
  if not waits:
    return entries
  use = CH.use_qs_defaults(ctx["answers"])
  return [_one(item, e, waits, ctx, evidence, use) for e in entries]
