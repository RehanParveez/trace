from __future__ import annotations
import hashlib
from app.modules.drawings_boq.takeoff.model.types import Fact, Decision

SLAB, BEAM, COUNT = "SLAB_THICKNESS", "BEAM_SECTION", "SOURCE_COUNT"

SCHEDULE, DETAIL, NOTE, PLAN = "SCHEDULE", "DETAIL_OR_SECTION", "NOTE", "PLAN"
TRUST = (SCHEDULE, DETAIL, NOTE, PLAN)
BASIS_TRUST = {"SCHEDULE": SCHEDULE, "DETAIL": DETAIL, "SECTION_LABEL": DETAIL, "SECTIONS": DETAIL, "PLAN_NOTE": NOTE, "OTHER_SHEET": PLAN, "FLOOR_PLAN": PLAN, "ALL_PLANS_SHEET": PLAN}

TOLERANCE = {SLAB: {"unit": "mm", "tolerance": 1.0, "why": "5 in and 6 in differ by 25 mm; a rounding of the same inch figure does not reach 1 mm"},
  BEAM: {"unit": "mm", "tolerance": 1.0, "why": "a listed beam section is its mark and its depth; two readings are one value only when both are the same"},
  COUNT: {"unit": "nos", "tolerance": 0.0, "why": "a count of doors or windows is whole; any difference between two sheets is a difference"}}

def trust_of(basis: str) -> str:
  return BASIS_TRUST.get(str(basis).split("+")[0], PLAN)

def rank(sources: list) -> int:
  return min((TRUST.index(trust_of(s.get("basis", ""))) for s in sources), default=len(TRUST))

def token(kind: str, value: dict) -> str:
  if kind == BEAM:
    return str(value.get("mark"))
  if kind == COUNT:
    return str(value.get("count"))
  return f"{round(float(value['value_mm']) / TOLERANCE[SLAB]['tolerance']):g}"

def decision_id(kind: str, values: list) -> str:
  toks = sorted({token(kind, v) + ("@" + f"{float(v['value_mm']):g}" if kind == BEAM and v.get("value_mm") is not None else "") for v in values})
  return hashlib.sha1(("|".join([kind, *toks])).encode()).hexdigest()[:16]

def scope_of(c: dict) -> str:
  return str(c.get("floor") or "") if c["kind"] != BEAM else str(c["subject"]).split(" · ")[0]

def point(kind: str, scope: str, values: list) -> dict:
  distinct = {token(kind, v) for v in values}
  return {"key": f"{kind}:{scope}", "kind": kind, "scope": scope, "decision_id": decision_id(kind, values) if len(distinct) > 1 else None}

def build(readings: list) -> tuple:
  facts_of: dict = {}
  groups: dict = {}
  for r in readings:
    kind, scope = r["kind"], r["scope"]
    key = f"{kind}:{scope}"
    toks = {token(kind, v) for v in r["values"]}
    if len(toks) <= 1:
      v = r["values"][0] if r["values"] else {}
      facts_of.setdefault((kind, scope), {"value": v.get("count") if kind == COUNT else v.get("value_mm"), "sources": tuple(s.get("basis", "") for s in v.get("sources") or []), "decision_id": None})
      continue
  
    did = decision_id(kind, r["values"])
    g = groups.setdefault(did, {"kind": kind, "values": {}, "facts": [], "rows": [], "chosen": []})
    for v in r["values"]:
      slot = g["values"].setdefault(token(kind, v), {"value": token(kind, v), "value_mm": v.get("value_mm"), "count": v.get("count"), "mark": v.get("mark"), "label": v.get("label"), "sources": []})
      for s in v.get("sources") or []:
        twin = next((x for x in slot["sources"] if (x.get("discipline"), x.get("page_no")) == (s.get("discipline"), s.get("page_no"))), None)
        if twin is None:
          slot["sources"].append(dict(s))
        else:
          twin["basis"] = "+".join(dict.fromkeys([*str(twin.get("basis", "")).split("+"), *str(s.get("basis", "")).split("+")]))
    if key not in g["facts"]:
      g["facts"].append(key)
    g["rows"].append(r["row_id"])
    if r.get("chosen") is not None:
      g["chosen"].append(r["chosen"])
    cur = facts_of.get((kind, scope))
    
    if cur is None or cur["decision_id"] is None:
      facts_of[(kind, scope)] = {"value": None, "sources": (), "decision_id": did}
  facts = [Fact(key=f"{k}:{sc}", value=v["value"], unit=TOLERANCE[k]["unit"], sources=v["sources"], decision_id=v["decision_id"]) for (k, sc), v in sorted(facts_of.items())]
  
  decisions: list = []
  for did, g in sorted(groups.items()):
    opts = sorted(g["values"].values(), key=lambda o: (o["value_mm"] is None, o["value_mm"] or 0, o["value"]))
    ranks = [rank(o["sources"]) for o in opts]
    best = min(ranks)
    top = [o for o, rk in zip(opts, ranks) if rk == best]
    default = top[0]["value"] if len(top) == 1 and best < len(TRUST) else None
    for o, rk in zip(opts, ranks):
      o["trust"] = TRUST[rk] if rk < len(TRUST) else None
      o["default"] = o["value"] == default
    chosen = g["chosen"][0] if g["chosen"] and all(c == g["chosen"][0] for c in g["chosen"]) else None
    decisions.append(Decision(id=did, question=_question(g["kind"], g["facts"]), options=tuple(opts), chosen=chosen, kind=g["kind"], facts=tuple(g["facts"]), rows=tuple(sorted(set(g["rows"]))), default=default))
  held = {d.id: d for d in decisions}
  
  fixed = []
  for f in facts:
    d = held.get(f.decision_id) if f.decision_id else None
    val = f.value
    if d is not None and d.chosen is not None:
      o = next((o for o in d.options if o["value"] == d.chosen), None)
      val = (o.get("count") if d.kind == COUNT else o.get("value_mm")) if o else None
    fixed.append(Fact(key=f.key, value=val, unit=f.unit, sources=f.sources, decision_id=f.decision_id))
  return fixed, decisions

def _question(kind: str, fact_keys: list) -> str:
  names = sorted({k.split(":", 1)[1] for k in fact_keys if k.split(":", 1)[1]})
  scopes = (", ".join(names[:3]) + (f" and {len(names) - 3} more" if len(names) > 3 else "")) if names else "the building"
  if kind == SLAB:
    return f"Which slab thickness is right for {scopes}? The sheets print it differently."
  if kind == BEAM:
    return f"Which listed section is beam {scopes}? The drawing lists several and the plan does not say which beam is which."
  return f"How many does {scopes} have? The sheets count them differently."
