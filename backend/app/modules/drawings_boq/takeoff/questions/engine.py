from __future__ import annotations
from app.engine.catalogue import conventions as CV
from app.engine.catalogue import loader as CAT
from app.modules.drawings_boq.takeoff.questions import keys as QK

OPEN, ANSWERED, RETIRED = "OPEN", "ANSWERED", "RETIRED"
UNIT_BOUNDS = {"mm": (1.0, 30000.0), "percent": (0.0, 100.0), "kg_per_m2": (0.0, 200.0)}
INPUT_TEXT = {
  "height": "What is the floor to floor height of the storeys, in millimetres? Answer for all storeys, or for one storey by its own key.",
}
OPTIONS = {
  QK.CONFIRM: [{"value": QK.ACCEPT, "label": "Take the reading as it is", "text": "The members are used as read, though the reader was not sure of them."},
    {"value": QK.REJECT, "label": "Ignore these members", "text": "The members are left out; the items they feed are then not read."}],
  QK.CONFLICT: [{"value": QK.PRINTED, "label": "The printed figure", "text": "The figure written on the drawing governs."},
    {"value": QK.DRAWN, "label": "The figure drawn", "text": "The figure measured from the drawn shape governs."}],
  QK.SUPPLY: [{"value": QK.NOT_IN_SCOPE, "label": "Not part of this job", "text": "The items that need it are left out of this job."}],
}

def _items() -> dict:
  return {i.id: i for i in CAT.items()}

def _input_facts(about: str, blocked: list) -> tuple:
  items = _items()
  unit, rule = None, None
  for iid in blocked:
    it = items.get(iid)
    if it is None:
      continue
    for inp in it.inputs:
      if inp.name == about:
        unit = unit or inp.unit
        rule = rule or inp.default_rule
  return unit, rule

def _default_of(rule: str | None, on: list) -> dict | None:
  c = CV.get(rule) if rule else None
  if c is None:
    return None
  return {"value": c["value"], "unit": c["unit"], "range": list(c["range"]), "rule": c["id"], "source": c["source"]["label"], "switched_on": c["id"] in on}

def blocked_money(entries: list, rates: dict | None) -> float | None:
  if not rates:
    return None
  total = 0.0
  for e in entries:
    q, r = e.get("quantity"), rates.get(e["element"])
    if q and r:
      total += float(q["value"]) * float(r)
  return round(total, 2)

def _prompt(kind: str, key: str, q: dict, unit: str | None) -> str:
  cls = str(q.get("cls") or "").lower().replace("_", " ")
  if kind == QK.INPUT:
    return INPUT_TEXT.get(q.get("about"), f"Give {str(q.get('about')).replace('_', ' ')}" + (f", in {unit}" if unit else "") + ".")
  if kind == QK.CONFIRM:
    return f"The reader was not sure of {len(q['members'])} {cls} member(s). Take the reading as it is, or leave them out?"
  if kind == QK.CONFLICT:
    return f"The drawing prints {q.get('mark') or 'a member'} two ways. Which figure governs?"
  if kind == QK.SUPPLY and key.startswith("sheets."):
    return f"The set has no {key.split('.', 1)[1]} sheet. Supply it, or say it is not part of this job."
  if kind == QK.SUPPLY:
    return f"The {QK.set_name(key).lower()} drawings are not in the set. Supply them, or say they are not part of this job."
  return q["ask"]

def _method_questions(ledger: list, answers: dict, on: list) -> list:
  out = []
  
  have = {e["element"]: e for e in ledger}
  for m in CV.methods():
    e = have.get(m["item"])
    key = QK.method_key(m["id"])
    if e is None:
      continue
    recorded = all(o["effect"] == CV.RECORDED for o in m["options"].values())
    asked = e["state"] in ("MEASURED", "ASSUMED", "ASKED") if recorded else any(r.startswith("METHOD:") for r in e["reasons"])
    if not (asked or key in answers):
      continue
    out.append({"key": key, "kind": QK.METHOD, "about": m["id"], "ask": f"How is {e['name'].lower()} counted?", "elements": [e["element"]], "entries": [e], "members": [], "floors": [],
      "options": [{"value": n, "label": n.replace("_", " ").capitalize(), "text": o["text"], "is_default": n == m["default"], "effect": o["effect"]} for n, o in m["options"].items()], "default": ({"value": m["default"], "rule": m["id"]} if m["default"] else None)})
  return out

def build(ledger: list, answers: dict | None = None, conventions: list | None = None, rates: dict | None = None) -> list:
  answers = dict(answers or {})
  on = list(conventions or [])
  groups: dict = {}
  
  for e in ledger:
    for q in e.get("questions") or []:
      key = q.get("key")
      if not key:
        continue
      
      g = groups.setdefault(key, {"key": key, "kind": q.get("kind") or QK.kind_of(key), "about": q.get("about"), "ask": q["ask"], "entries": [], "elements": [], "members": [], "floors": [], "options": None, "default": None})
      g["entries"].append(e)
      if e["element"] not in g["elements"]:
        g["elements"].append(e["element"])
      g["members"] += [m for m in q.get("members") or [] if m not in g["members"]]
      if e["floor"] != "ALL" and e["floor"] not in g["floors"]:
        g["floors"].append(e["floor"])
      if q.get("mark"):
        g["mark"] = q["mark"]
      if q.get("cls"):
        g["cls"] = q["cls"]
  for g in _method_questions(ledger, answers, on):
    groups.setdefault(g["key"], g)
  out = []
  
  for key, g in groups.items():
    kind = g["kind"]
    unit, rule = _input_facts(g["about"], g["elements"]) if kind == QK.INPUT else (None, None)
    row = {"key": key, "kind": kind, "prompt": _prompt(kind, key, g, unit), "unit": unit, "default": g["default"] or _default_of(rule, on),
      "options": g["options"] or [dict(o) for o in OPTIONS.get(kind, [])], "blocks": sorted(g["elements"]), "floors": g["floors"], "members": len(g["members"]), "entries": len(g["entries"]),
      "why": f"{len(g['elements'])} item(s) wait on this", "money": blocked_money(g["entries"], rates)}
    
    if kind == QK.METHOD:
      row["options"] = g["options"]
      row["why"] = f"{', '.join(g['elements'])} is counted differently by each option"
    row["answer"] = answers.get(key)
    row["state"] = ANSWERED if row["answer"] else OPEN
    out.append(row)
  seen = {r["key"] for r in out}
  for key, a in answers.items():
    if key not in seen and QK.is_question_key(key):
      out.append({"key": key, "kind": QK.kind_of(key), "prompt": "No longer asked: nothing now waits on this answer. It is kept.", "unit": None, "default": None, "options": [], "blocks": [], "floors": [], "members": 0, "entries": 0, "why": "retired", "money": None, "answer": a, "state": RETIRED})
  return sorted(out, key=lambda r: (r["state"] != OPEN, -(r["money"] or 0.0), -len(r["blocks"]), r["key"]))

def check(question: dict, value) -> str | None:
  kind = question["kind"]
  if kind == QK.INPUT:
    try:
      v = float(value)
    except (TypeError, ValueError):
      return "Give a number."
    lo, hi = UNIT_BOUNDS.get(question.get("unit"), (0.0, float("inf")))
    if not (v > 0 and lo <= v <= hi):
      return f"Give a number between {lo:g} and {hi:g}" + (f" {question['unit']}" if question.get("unit") else "") + "."
    return None
  if str(value) not in {o["value"] for o in question["options"]}:
    return "That is not one of the options."
  return None
