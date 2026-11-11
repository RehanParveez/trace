from __future__ import annotations
import re
from app.modules.drawings_boq.lab.aliases import bill_quantity
from app.modules.drawings_boq.takeoff.proof import score as SC
from app.modules.drawings_boq.takeoff.proof.bench import money_source as MS
from app.modules.drawings_boq.takeoff.completeness import ledger as LG
from app.engine.catalogue import loader as CL
from app.modules.drawings_boq.takeoff.run import completeness as RC
from app.engine.catalogue import tolerances as TOL

PRINTED, JOINED, AI_READ, DECISION, DEFAULT_RULE, DERIVED = "PRINTED", "JOINED", "AI_READ", "DECISION", "DEFAULT_RULE", "DERIVED"
WITHIN_PCT = 10.0

def answer_table(doc: dict | None) -> dict:
  out: dict = {}
  for it in (doc or {}).get("items") or []:
    if not it.get("confirmed"):
      continue
    q = float(it["quantity"])
    _q, si_unit, si_q = bill_quantity("", str(it.get("unit") or ""), q)
    slot = out.setdefault(it["element"], {"unit": it.get("unit"), "si_unit": si_unit, "floors": {}, "items": 0})
    slot["floors"][it.get("floor")] = slot["floors"].get(it.get("floor"), 0.0) + si_q
    slot["items"] += 1
  return out

def answer_in(answers: dict, element: str, floor: str, floors: set, unit: str | None) -> tuple:
  slot = answers.get(element)
  if slot is None:
    return None, None
  if floor == LG.ALL:
    si = sum(slot["floors"].values())
  else:
    si = slot["floors"].get(floor, 0.0)
    if floor not in slot["floors"]:
      return None, None
  use = unit or slot["unit"]
  got = SC.to_unit(si, slot["si_unit"], str(use)) if use else None
  if got is None:
    return None, "ANSWER_UNIT_MISMATCH"
  return got, None

def member_joins(plain: dict) -> dict:
  seen: dict = {}
  joined: dict = {}
  for i in plain["items"]:
    base = f"p{i['sheet']}:{i['mark'] or i['cls'].lower()}"
    seen[base] = seen.get(base, 0) + 1
    joined[f"{base}#{seen[base]}"] = bool(i.get("join"))
  return joined

def sources_of(entry: dict, joins: dict) -> list:
  out = []
  if entry["members"] or entry["quantity"]:
    out.append(JOINED if any(joins.get(m) for m in entry["members"]) else PRINTED)
  if any(r.startswith(LG.DERIVED_FROM) for r in entry["reasons"]):
    out.append(DERIVED)
  if entry["assumptions"]:
    out.append(DEFAULT_RULE)
  if any(r.startswith(f"{LG.ANSWERED}:") or r.startswith(f"{LG.METHOD}:") for r in entry["reasons"]) and not any(r == LG.METHOD_DEFAULT for r in entry["reasons"]):
    out.append(DECISION)
  return list(dict.fromkeys(out))

def pages_of(entry: dict, evidence: dict, pdfs: list, kinds: dict) -> list:
  sheets = set()
  for m in entry["members"]:
    mt = re.match(r"p(\d+):", m)
    if mt:
      sheets.add(int(mt.group(1)))
  if entry["state"] == LG.NOT_READ:
    item = CL.get(entry["element"])
    classes = {r.cls for r in item.reads if not r.support} if item is not None else set()
    sheets |= {g["page"] for g in evidence["gaps"] if g["cls"] in classes}
  if not sheets and entry["state"] == LG.NOT_READ:
    item = CL.get(entry["element"])
    wanted = set(item.page_roles) if item is not None else set()
    sheets = {int(k) for k, names in kinds.items() if wanted & names}
  out = []
  for s in sorted(sheets)[:3]:
    n = s // RC.SHEET_SHIFT
    out.append({"pdf": pdfs[n] if n < len(pdfs) else None, "page": s % RC.SHEET_SHIFT})
  return out

def diff_pct(trace, answer):
  if trace is None or answer is None:
    return None
  if answer == 0:
    return 0.0 if trace == 0 else None
  return (trace - answer) / answer * 100.0

def row_of(name: str, office: str, split_by_group: dict, group_of_section: dict, run: str, entry: dict, answers: dict, floors: set, joins: dict, evidence: dict, pdfs: list, kinds: dict) -> dict:
  q = entry["quantity"]
  trace = None if q is None else float(q["value"])
  unit = None if q is None else q["unit"]
  ans, why = answer_in(answers, entry["element"], entry["floor"], floors, unit)
  slot = answers.get(entry["element"])
  if unit is None and slot is not None:
    unit = slot["unit"]
    ans, why = answer_in(answers, entry["element"], entry["floor"], floors, unit)
  d = diff_pct(trace, ans)
  group = group_of_section.get(entry["section"])
  tol, tol_basis = TOL.pct_for(entry["element"])
  
  return {"set": name, "office": office, "split": split_by_group.get(group, "UNSPLIT"), "run": run, "group": group, "section": entry["section"], "owner_pack": entry["owner_pack"],
    "element": entry["element"], "floor": entry["floor"], "state": entry["state"], "unit": unit,
    "trace_qty": None if trace is None else round(trace, 3), "answer_qty": None if ans is None else round(ans, 3),
    "within_10": d is not None and abs(d) <= WITHIN_PCT, "tol_pct": tol, "tol_basis": tol_basis, "within_tol": d is not None and abs(d) <= tol, "diff_pct": None if d is None else round(d, 2),
    "reasons": list(entry["reasons"]) + ([why] if why else []), "sources": sources_of(entry, joins), "pages": pages_of(entry, evidence, pdfs, kinds), "money_source": MS.of_entry(entry, evidence)}

def rows_of(name: str, office: str, split_by_group: dict, group_of_section: dict, run: str, ledger: list, answers_doc: dict | None, plain: dict, evidence: dict, pdfs: list) -> tuple:
  answers = answer_table(answers_doc)
  joins = member_joins(plain)
  kinds = {str(r['page']): {x for x in (r['role'], r['plan_kind'], RC.sheet_key(r)) if x} for r in RC.page_rows(plain)}
  floors = {e["floor"] for e in ledger}
  rows = [row_of(name, office, split_by_group, group_of_section, run, e, answers, floors, joins, evidence, pdfs, kinds) for e in ledger]
  placed = {(r["element"]) for r in rows}
  lost = [el for el in answers if el not in placed]
  off_floor = sum(1 for el, slot in answers.items() for fl in slot["floors"] if fl is not None and fl not in floors)
  unconfirmed = sum(1 for it in (answers_doc or {}).get("items") or [] if not it.get("confirmed"))
  return rows, {"answers_elements": len(answers), "answers_not_in_ledger": lost, "answer_floors_not_in_project": off_floor, "answers_unconfirmed_items": unconfirmed}
