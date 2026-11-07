from __future__ import annotations
from app.engine.catalogue import conventions as CV
from app.engine.catalogue import model as CM
from app.engine.measure import rule_registry as RR
from app.modules.drawings_boq.takeoff.completeness import derived_rules as DR
from app.modules.drawings_boq.takeoff.completeness import expected as EX
from app.modules.drawings_boq.takeoff.completeness import facts as F
from app.modules.drawings_boq.takeoff.questions import keys as QK

MEASURED, ASSUMED, ASKED, NOT_APPLICABLE, NOT_READ = CM.STATES
READ = "READ"
ALL = "ALL"
SET_NOT_SUPPLIED = "SET_NOT_SUPPLIED"
OUTSIDE_PACKAGE = "OUTSIDE_STRUCTURE_PACKAGE"
NO_SHEET = "NO_SHEET_OF_KIND"
NO_READER = "NO_READER"
NOT_DRAWN = "NOT_DRAWN"
NO_SYMBOLS = "NO_SYMBOLS_FOUND"
UNSURE_READ = "READ_NEEDS_CONFIRMATION"
NO_READ_ON_FLOOR = "NO_READ_ON_FLOOR"
FLOOR_UNKNOWN = "FLOOR_UNKNOWN"
DERIVED_FROM = "DERIVED_FROM"
DERIVED_NOT_COMPUTED = "DERIVED_NOT_COMPUTED"
METHOD = "METHOD"
ANSWERED = "ANSWERED"
DECLARED_OUT = "DECLARED_OUT_OF_SCOPE"
METHOD_DEFAULT = "METHOD_DEFAULT"
METHOD_NOT_BUILT = "METHOD_NOT_BUILT"
INFO_REASONS = ("LABELS_OUTLINED", "GLYPH_REPAIRED", "FONT_DECODED")
REASON_INPUT = {"NEEDS_STOREY_HEIGHT": "height"}
ENTRY_KEYS = ("element", "name", "section", "owner_pack", "floor", "state", "quantity", "members", "assumptions", "questions", "reasons")

def empty_evidence() -> dict:
  return {"members": [], "gaps": [], "sheets": [], "lines": [], "assumptions": [], "no_reader": []}

def _ask(about: str | None, text: str, key: str | None = None, kind: str = QK.INPUT, **more) -> dict:
  return {"about": about, "ask": text, "key": key, "kind": kind, **more}

def _answer(ctx: dict, key: str) -> str | None:
  row = ctx["answers"].get(key)
  return None if row is None else str(row.get("value"))

def _entry(item, floor: str, state: str, reasons: list, *, members: list | None = None, quantity: dict | None = None, assumptions: list | None = None, questions: list | None = None) -> dict:
  return {
    "element": item.id, "name": item.name, "section": item.section, "owner_pack": item.owner_pack, "floor": floor, "state": state,
    "quantity": quantity, "members": list(members or []), "assumptions": list(assumptions or []), "questions": list(questions or []), "reasons": list(dict.fromkeys(reasons)),
  }

def _missing_sets(item, facts: dict) -> list:
  present = list(facts["sets_present"]["value"] or [])
  need = EX.needed_sets(item)
  if not need:
    return []
  if item.applies_when.get("sets_present"):
    return [s for s in need if s not in present]
  return [] if any(s in present for s in need) else need

def _on_keys(item) -> set:
  return {k for r in item.reads if not r.support for k in r.on}

def _read_classes(item) -> set:
  return {r.cls for r in item.reads if not r.support}

def _members_on(item, floor: str, evidence: dict) -> tuple:
  classes = _read_classes(item)
  support = {r.cls for r in item.reads if r.support} - classes if RR.on("SUPPORT_CONFLICT_QUESTIONS") else set()
  every = [m for m in evidence["members"] if m["cls"] in classes]
  printed_twice = [m for m in evidence["members"] if m["cls"] in support and "CONFLICT_IN_DRAWING" in (m.get("reasons") or [])]
  here = [m for m in every + printed_twice if floor == ALL or m.get("floor") in (None, floor)]
  return every, here

def _lines_for(item, floor: str, evidence: dict) -> list:
  families = {q.line for q in item.billing.PRIVATE_QS}
  if not families:
    return []
  return [ln for ln in evidence["lines"] if ln["family"] in families and (floor == ALL or ln.get("floor") == floor)]

def _quantity(item, lines: list) -> dict | None:
  if not lines:
    return None
  units = {ln.get("unit") or item.unit for ln in lines}
  unit = item.unit if item.unit in units else sorted(units)[0]
  same = [ln for ln in lines if (ln.get("unit") or item.unit) == unit]
  return {"value": round(sum(float(ln["value"]) for ln in same), 3), "unit": unit, "range": None}

def _assumed(item, floor: str, evidence: dict) -> list:
  return [a for a in evidence["assumptions"] if a["item"] == item.id and a.get("floor") in (floor, ALL, None)]

def _convention_for(item, input_name: str, ctx: dict) -> str | None:
  """The switched-on convention that fills this input, when the project is of a type it covers."""
  ref = f"{item.id}.{input_name}"
  for cid in ctx["on"]:
    c = CV.get(cid)
    if c is not None and ref in c["fills"] and CV.in_scope(cid, ctx["type"]):
      return cid
  return None

def _widen(quantity: dict | None, covered: list) -> dict | None:
  """The quantity's range from the assumptions behind it, taking the quantity as proportional to each assumed input."""
  if not quantity or not covered:
    return quantity
  lo = hi = 1.0
  for a in covered:
    if a.get("value") and a.get("range"):
      lo *= a["range"][0] / a["value"]
      hi *= a["range"][1] / a["value"]
  v = quantity["value"]
  return {**quantity, "range": [round(v * lo, 3), round(v * hi, 3)]}

def _interval(q: dict) -> tuple:
  r = q.get("range")
  return (float(q["value"]), float(r[0]), float(r[1])) if r else DR.exact(q["value"])

def _unread(item, floor: str, every: list, evidence: dict) -> tuple:
  classes = _read_classes(item)
  if not classes:
    return NOT_READ, [NO_READER, f"OWNER_{item.owner_pack}"], []
  if every:
    return NOT_READ, [NO_READ_ON_FLOOR], []
  on = _on_keys(item)
  if on and not on & set(evidence["sheets"]):
    shown = sorted(on)[0]
    return ASKED, [NO_SHEET], [_ask(None, f"The set has no {shown} sheet. Supply it, or give the quantity.", QK.sheets_key(shown), QK.SUPPLY)]
  gaps = [g for g in evidence["gaps"] if g["cls"] in classes]
  reasons = [r for g in gaps for r in g.get("reasons") or []]
  if all(c in evidence["no_reader"] for c in classes):
    reasons.append(NO_READER)
  return NOT_READ, reasons or [NO_SYMBOLS], []

def _blocks(m: dict) -> bool:
  """A member blocks an assumption when it is not read and names no missing input, or carries a reason that is neither information nor a missing input."""
  if m["status"] != READ and not m.get("missing"):
    return True
  return any(r not in INFO_REASONS and r not in REASON_INPUT for r in m.get("reasons") or [])

def _settle(m: dict, floor: str, ctx: dict) -> tuple:
  """A member after the answers: None when its class's reading was rejected; otherwise the member with the inputs given removed from what it misses, and whether it still blocks."""
  rk = QK.reading_key(m["cls"])
  used: list = []
  if _answer(ctx, rk) == QK.REJECT:
    return None, [rk]
  accepted = _answer(ctx, rk) == QK.ACCEPT
  if accepted:
    used.append(rk)
  ck = QK.conflict_key(m["cls"], m.get("mark"))
  if "CONFLICT_IN_DRAWING" in (m.get("reasons") or []) and _answer(ctx, ck) in (QK.PRINTED, QK.DRAWN):
    accepted = True
    used.append(ck)
  missing = []
  for n in m.get("missing") or []:
    got = next((k for k in QK.answer_keys(n, None if floor == ALL else floor) if _answer(ctx, k) is not None), None)
    if got is not None:
      used.append(got)
    else:
      missing.append(n)
  blocks = not accepted and _blocks(m)
  return {**m, "missing": missing, "blocks": blocks, "ok": not blocks and not missing}, used

def _confirm_questions(item, blockers: list) -> list:
  out = []
  by_conflict: dict = {}
  by_class: dict = {}
  for m in blockers:
    others = [r for r in m.get("reasons") or [] if r not in INFO_REASONS and r not in REASON_INPUT and r != "CONFLICT_IN_DRAWING"]
    if "CONFLICT_IN_DRAWING" in (m.get("reasons") or []) and not others:
      by_conflict.setdefault((m["cls"], m.get("mark")), []).append(m)
    else:
      by_class.setdefault(m["cls"], []).append(m)
  for (cls, mark), ms in by_conflict.items():
    out.append(_ask(None, f"{item.name}: the drawing prints {mark or 'a member'} two ways ({len(ms)} member(s), first {ms[0]['id']}). Say which governs.", QK.conflict_key(cls, mark), QK.CONFLICT, cls=cls, mark=mark, members=[m["id"] for m in ms], reasons=["CONFLICT_IN_DRAWING"]))
  for cls, ms in by_class.items():
    why = sorted({r for m in ms for r in m.get("reasons") or [] if r not in INFO_REASONS and r not in REASON_INPUT})
    out.append(_ask(None, f"{item.name}: confirm the reading of {len(ms)} {cls.lower().replace('_', ' ')} member(s), first {', '.join(m['id'] for m in ms[:3])}" + (f" ({', '.join(why)})." if why else "."), QK.reading_key(cls), QK.CONFIRM, cls=cls, members=[m["id"] for m in ms], reasons=why))
  return out

def _regular(item, floor: str, evidence: dict, ctx: dict) -> dict:
  every, here = _members_on(item, floor, evidence)
  settled, used = [], []
  for m in here:
    got, keys = _settle(m, floor, ctx)
    used += keys
    if got is not None:
      settled.append(got)
  here_ids = [m["id"] for m in settled]
  live = [m for m in settled if m["ok"]]
  unsure = [m for m in settled if not m["ok"]]
  lines = _lines_for(item, floor, evidence)
  unknown = [FLOOR_UNKNOWN] if floor != ALL and any(m.get("floor") is None for m in settled) else []
  said = [f"{ANSWERED}:{k}" for k in dict.fromkeys(used)]
  if unsure:
    reasons = [UNSURE_READ] + [r for m in unsure for r in m.get("reasons") or []] + said
    asked: dict = {}
    for m in unsure:
      for n in m.get("missing") or []:
        asked.setdefault(n, []).append(m["id"])
    questions = [_ask(n, f"{item.name}: {n} is not read for {len(who)} member(s), first {', '.join(who[:3])}. Give it.", QK.input_key(n), QK.INPUT, members=who, floor=None if floor == ALL else floor) for n, who in asked.items()]
    questions += _confirm_questions(item, [m for m in unsure if m["blocks"]])
    return _finish_ask(item, floor, evidence, reasons + unknown, here_ids, questions, _quantity(item, lines), ctx)
  if live or lines:
    return _entry(item, floor, MEASURED, unknown + said, members=here_ids, quantity=_quantity(item, lines))
  state, reasons, questions = _unread(item, floor, every, evidence)
  if state == ASKED and all(_answer(ctx, q["key"]) == QK.NOT_IN_SCOPE for q in questions if q.get("key")) and any(q.get("key") for q in questions):
    return _entry(item, floor, NOT_APPLICABLE, [f"{DECLARED_OUT}:{q['key']}" for q in questions if q.get("key")])
  return _finish_ask(item, floor, evidence, reasons, here_ids, questions, None, ctx) if state == ASKED else _entry(item, floor, state, reasons, members=here_ids)

def _finish_ask(item, floor: str, evidence: dict, reasons: list, ids: list, questions: list, quantity: dict | None, ctx: dict) -> dict:
  """Assumed when every question is about an input a switched-on convention fills; asked otherwise, still listing the assumptions the conventions would make."""
  covered = _assumed(item, floor, evidence)
  for q in questions:
    cid = _convention_for(item, q["about"], ctx) if q["about"] else None
    if cid and not any(a["input"] == q["about"] for a in covered):
      covered.append(CV.assumption(cid, item.id, q["about"], None if floor == ALL else floor))
  names = {a["input"] for a in covered}
  left = [q for q in questions if q["about"] is None or q["about"] not in names]
  if covered and not left:
    return _entry(item, floor, ASSUMED, reasons, members=ids, quantity=_widen(quantity, covered), assumptions=covered)
  return _entry(item, floor, ASKED, reasons, members=ids, quantity=quantity, assumptions=covered, questions=left)

def _from_ids(item) -> list:
  src = (item.derived or {}).get("from") or []
  return [src] if isinstance(src, str) else list(src)

def _source_quantity(rows: list, floor: str) -> dict | None:
  """The summed quantity of one source over its floors; None when a live row has no quantity."""
  same = [e for e in rows if e["floor"] == floor] or rows
  live = [e for e in same if e["state"] != NOT_APPLICABLE]
  if not live or any(e["quantity"] is None for e in live):
    return None
  units = {e["quantity"]["unit"] for e in live}
  if len(units) != 1:
    return None
  ivs = [_interval(e["quantity"]) for e in live]
  v, lo, hi = (sum(x[k] for x in ivs) for k in range(3))
  return {"value": v, "unit": units.pop(), "range": None if lo == hi == v else [lo, hi]}

def _compute(item, floor: str, entries: dict, rule: dict, ctx: dict, tag: list, live_states: list) -> dict:
  src = _from_ids(item)
  quantities = {}
  for sid in src:
    rows = entries.get(sid) or []
    if all(e["state"] == NOT_APPLICABLE for e in (([e for e in rows if e["floor"] == floor]) or rows)):
      continue
    q = _source_quantity(rows, floor)
    if q is None:
      return _entry(item, floor, NOT_READ, tag + [DERIVED_NOT_COMPUTED])
    quantities[sid] = (q["value"], *_interval(q)[1:]), q["unit"]
  if not src or src[0] not in quantities:
    return _entry(item, floor, NOT_READ, tag + [DERIVED_NOT_COMPUTED])
  iv = {sid: x[0] for sid, x in quantities.items()}
  unit = quantities[src[0]][1]
  assumed = []
  pct = DR.exact(1.0)
  need = rule["input"]
  given = []
  if need:
    key = QK.input_key(need)
    cid = _convention_for(item, need, ctx)
    if _answer(ctx, key) is not None:
      value = float(_answer(ctx, key))
      pct = (value, value, value)
      given = [f"{ANSWERED}:{key}"]
    elif cid is None:
      return _entry(item, floor, ASKED, tag, questions=[_ask(need, f"{item.name}: {need} is not given. Give it, or switch on the convention that holds it.", key, QK.INPUT)])
    else:
      c = CV.get(cid)
      pct = (float(c["value"]), float(c["range"][0]), float(c["range"][1]))
      assumed = [CV.assumption(cid, item.id, need, None if floor == ALL else floor)]
  v, lo, hi = rule["fn"]([sid for sid in src if sid in iv], iv, pct)
  out_unit = item.unit if item.unit else unit
  quantity = {"value": round(v, 3), "unit": out_unit, "range": None if lo == hi == v else [round(lo, 3), round(hi, 3)]}
  derived_from_assumed = ASSUMED in live_states
  state = ASSUMED if assumed or derived_from_assumed else MEASURED
  return _entry(item, floor, state, tag + given, quantity=quantity, assumptions=assumed)

def _derived(item, floor: str, entries: dict, evidence: dict, ctx: dict) -> dict:
  picked = []
  for sid in _from_ids(item):
    rows = entries.get(sid) or []
    same = [e for e in rows if e["floor"] == floor]
    picked += same or rows
  states = [e["state"] for e in picked]
  tag = [f"{DERIVED_FROM}:{','.join(_from_ids(item))}"]
  live = [s for s in states if s != NOT_APPLICABLE]
  if not live:
    return _entry(item, floor, NOT_APPLICABLE, tag)
  if ASKED in live:
    return _entry(item, floor, ASKED, tag, questions=[q for e in picked if e["state"] == ASKED for q in e["questions"]][:6])
  if NOT_READ in live:
    return _entry(item, floor, NOT_READ, tag)
  rule = DR.RULES.get((item.derived or {}).get("rule"))
  if rule and rule["kind"] == DR.COMPUTED:
    return _compute(item, floor, entries, rule, ctx, tag, live)
  lines = _lines_for(item, floor, evidence)
  if lines:
    return _entry(item, floor, ASSUMED if ASSUMED in live else MEASURED, tag, quantity=_quantity(item, lines))
  return _entry(item, floor, NOT_READ, tag + [DERIVED_NOT_COMPUTED])

def _method(item, ctx: dict) -> dict | None:
  """The entry a decided or default method gives an item, or None when the method leaves the item to be read as usual."""
  m = CV.method_of_item(item.id)
  if m is None:
    return None
  name, effect, decided = CV.method_choice(m["id"], ctx["methods"])
  why = [f"{METHOD}:{m['id']}={name}"] + ([] if decided else [METHOD_DEFAULT])
  if effect == CV.RECORDED:
    return None
  if effect == "NOT_COUNTED":
    return _entry(item, ALL, NOT_APPLICABLE, why)
  if effect == "NOT_BUILT":
    return _entry(item, ALL, NOT_READ, why + [METHOD_NOT_BUILT])
  return None

def _single(item, facts: dict, evidence: dict, scope: str, entries: dict, ctx: dict) -> list:
  state, why = EX.applicability(item, facts)
  floors = EX.floor_scope(item, facts)
  held = _lines_for(item, ALL, evidence)
  if held and not any(ln.get("floor") for ln in held):
    floors = [ALL]
  if state == EX.NOT_APPLICABLE:
    return [_entry(item, ALL, NOT_APPLICABLE, why)]
  if item.owner_pack == "RATE":
    return [_entry(item, ALL, NOT_READ, [NOT_DRAWN])]
  chosen = _method(item, ctx)
  if chosen is not None:
    return [chosen]
  absent = _missing_sets(item, facts)
  if absent:
    if scope == "STRUCTURE_ONLY":
      return [_entry(item, ALL, NOT_APPLICABLE, [OUTSIDE_PACKAGE])]
    owed = [s for s in absent if _answer(ctx, QK.sets_key(s)) != QK.NOT_IN_SCOPE]
    if not owed:
      return [_entry(item, ALL, NOT_APPLICABLE, [f"{DECLARED_OUT}:{QK.sets_key(s)}" for s in absent])]
    return [_entry(item, ALL, ASKED, [SET_NOT_SUPPLIED], questions=[_ask(None, f"The {s.lower()} drawings are not in the set. Supply them, or say they are not part of this job.", QK.sets_key(s), QK.SUPPLY, set=s) for s in owed])]
  if item.derived:
    return [_derived(item, f, entries, evidence, ctx) for f in floors]
  return [_regular(item, f, evidence, ctx) for f in floors]

def build(items: list, facts: dict, evidence: dict, conventions: list | None = None, methods: dict | None = None, answers: dict | None = None) -> list:
  """The five-state ledger: one entry per catalogue item and floor. Items that are derived are settled after the items they come from. Conventions are the ids a company switched on; methods are the options a project decided; answers are the answers to questions, by question key."""
  scope = F.scope_of(facts)
  held = dict(answers or {})
  decided = {QK.method_id(k): str(a.get("value")) for k, a in held.items() if QK.kind_of(k) == QK.METHOD}
  ctx = {"on": list(conventions or []), "methods": {**dict(methods or {}), **decided}, "type": F.values(facts).get("type"), "answers": held}
  entries: dict = {}
  plain = [it for it in items if not it.derived]
  for it in plain:
    entries[it.id] = _single(it, facts, evidence, scope, entries, ctx)
  pending = [it for it in items if it.derived]
  derived_ids = {it.id for it in pending}
  while pending:
    ready = [it for it in pending if all(sid not in derived_ids or sid in entries for sid in _from_ids(it))] or pending
    for it in ready:
      entries[it.id] = _single(it, facts, evidence, scope, entries, ctx)
    pending = [it for it in pending if it.id not in entries]
  order = {it.id: n for n, it in enumerate(items)}
  out = [e for rows in entries.values() for e in rows]
  return sorted(out, key=lambda e: (order[e["element"]], F._floor_key(e["floor"]) if e["floor"] != ALL else (-1, "")))

def summary(entries: list) -> dict:
  states = {s: 0 for s in CM.STATES}
  reasons: dict = {}
  for e in entries:
    states[e["state"]] += 1
    for r in e["reasons"]:
      key = r.split(":")[0]
      reasons[key] = reasons.get(key, 0) + 1
  return {"entries": len(entries), "by_state": states, "by_reason": dict(sorted(reasons.items()))}
