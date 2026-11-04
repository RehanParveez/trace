from __future__ import annotations
from decimal import Decimal as D
from app.engine.measure.rebar import FORMULA_BBS, FORMULA_ESTIMATE
from app.modules.drawings_boq.rebar import bbs_report as BR

FORMULA_AUDITED = "REBAR_BBS_AUDITED"
SOURCE_AUDITED, SOURCE_BBS, SOURCE_ESTIMATE = "BBS_AUDITED", "BBS_WEIGHT", "RULE_ESTIMATE"
SOURCES = (SOURCE_AUDITED, SOURCE_BBS, SOURCE_ESTIMATE)
SOURCE_FORMULA = {SOURCE_AUDITED: FORMULA_AUDITED, SOURCE_BBS: FORMULA_BBS, SOURCE_ESTIMATE: FORMULA_ESTIMATE}
DEFAULT_SOURCE = SOURCE_AUDITED
APPLIED_STATUS = "ACCEPTED"
NOT_AUDITED = "not audited"
LEDGER_GAP_SHARE = D("0.005")
ZERO = D(0)
MM_PER_BAR_NO = D("25.4") / 8

def check_steel_source(value) -> dict:
  src = value.get("source") if isinstance(value, dict) and set(value) == {"source"} else None
  if src not in SOURCES:
    raise ValueError(f"steel_source is {{source: one of {', '.join(SOURCES)}}}")
  return {"source": src}

def applied(f: dict) -> bool:
  return f.get("status") == APPLIED_STATUS and f.get("effect_basis") in BR.BASES and BR.d(f.get("diff_kg")) is not None

def _label(dia) -> str:
  return f"#{int(dia)}" if dia is not None else "?"

def _mm(dia) -> D | None:
  return None if dia is None else (MM_PER_BAR_NO * int(dia)).quantize(D("0.1"))

def rows_of_findings(rows: list, findings: list) -> dict:
  out: dict = {id(f): [] for f in findings}
  for no, hits in BR.findings_by_row(rows, findings).items():
    for f in hits:
      out[id(f)].append(no)
  return out

def by_diameter(rows: list, findings: list) -> tuple:
  by_no = {r["row_no"]: r for r in rows}
  size: dict = {}
  for r in rows:
    size[r.get("dia")] = size.get(r.get("dia"), ZERO) + (BR.d(r.get("total_kg")) or ZERO)
    
  move: dict = {}
  loose = ZERO
  shared = ZERO
  named = rows_of_findings(rows, findings)
  for f in findings:
    if not applied(f):
      continue
    
    amount = BR.d(f["diff_kg"])
    weights: dict = {}
    for no in named.get(id(f)) or []:
      dia = by_no[no].get("dia")
      if dia is not None:
        weights[dia] = weights.get(dia, ZERO) + (BR.d(by_no[no].get("total_kg")) or ZERO)
        
    total = sum(weights.values(), ZERO)
    if len(weights) == 1:
      dia = next(iter(weights))
      move[dia] = move.get(dia, ZERO) + amount
    elif len(weights) > 1 and total > 0:
      for dia, w in weights.items():
        move[dia] = move.get(dia, ZERO) + amount * w / total
      shared += amount
    else:
      loose += amount
      
  out = []
  for dia in sorted((k for k in set(size) | set(move) if k is not None), key=int):
    base, eff = size.get(dia, ZERO), move.get(dia, ZERO)
    out.append({"dia": int(dia), "label": _label(dia), "mm": _mm(dia), "bbs_kg": BR.q2(base), "applied_kg": BR.q2(eff), "audited_kg": BR.q2(base + eff)})
  return out, BR.q2(loose + size.get(None, ZERO)), BR.q2(shared)

def _to_the_cent(table: list, unattributed, audited) -> list:
  residual = audited - (sum((r["audited_kg"] for r in table), ZERO) + unattributed)
  if table and residual != 0 and abs(residual) <= D("0.05"):
    big = max(table, key=lambda r: r["audited_kg"])
    big["audited_kg"] += residual
    big["applied_kg"] += residual
  return table

def open_findings(findings: list) -> dict:
  rows = [f for f in findings if f.get("status") == "OPEN"]
  by_class: dict = {}
  by_code: dict = {}
  effect = ZERO
  for f in rows:
    by_class[f["finding_class"]] = by_class.get(f["finding_class"], 0) + 1
    by_code[f["code"]] = by_code.get(f["code"], 0) + 1
    if f.get("effect_basis") in BR.BASES and BR.d(f.get("diff_kg")) is not None:
      effect += BR.d(f["diff_kg"])
  return {"count": len(rows), "by_class": dict(sorted(by_class.items(), key=lambda t: BR.CLASS_RANK.get(t[0], 9))), "by_code": dict(sorted(by_code.items(), key=lambda t: (-t[1], t[0]))),
    "effect_kg": BR.q2(effect)}

def _kg(x) -> str:
  return "none" if x is None else f"{x:,.2f} kg"

def _open_note(op: dict) -> str:
  if not op["count"]:
    return "No finding is open."
  classes = ", ".join(f"{n} {k}" for k, n in op["by_class"].items())
  return f"{op['count']} finding(s) are still open ({classes}); their effect of {BR.q2(op['effect_kg']):+,} kg is not applied."

def resolve(requested: str | None, audited, bbs, estimate) -> tuple:
  want = requested if requested in SOURCES else DEFAULT_SOURCE
  have = {SOURCE_AUDITED: audited, SOURCE_BBS: bbs, SOURCE_ESTIMATE: estimate}
  order = {SOURCE_AUDITED: (SOURCE_AUDITED, SOURCE_BBS, SOURCE_ESTIMATE), SOURCE_BBS: (SOURCE_BBS, SOURCE_ESTIMATE), SOURCE_ESTIMATE: (SOURCE_ESTIMATE, SOURCE_BBS)}[want]
  for s in order:
    if have[s] is not None:
      return s, (want if s != want else None)
  return None, want

def build(rows: list | None, sheets: list | None, findings: list, *, has_run: bool, ledger_bbs_kg=None, ledger_estimate_kg=None, requested: str | None = None, wastage_pct=None,
    document: dict | None = None) -> dict:
  has_doc = rows is not None
  doc_kg = BR.q2(sum((BR.d(r.get("total_kg")) or ZERO for r in rows), ZERO)) if has_doc else None
  ledger_bbs = BR.q2(BR.d(ledger_bbs_kg)) if ledger_bbs_kg else None
  estimate = BR.q2(BR.d(ledger_estimate_kg)) if ledger_estimate_kg else None
  bbs = doc_kg if has_doc else ledger_bbs
  audited = effect = None
  
  table: list = []
  unattributed = allocated = None
  if has_doc and has_run:
    effect = BR.q2(sum((BR.d(f["diff_kg"]) for f in findings if applied(f)), ZERO))
    audited = BR.q2(doc_kg + effect)
    table, unattributed, allocated = by_diameter(rows, findings)
    table = _to_the_cent(table, unattributed, audited)
  elif has_doc:
    table, unattributed, allocated = by_diameter(rows, [])
  op = open_findings(findings) if has_run else {"count": 0, "by_class": {}, "by_code": {}, "effect_kg": ZERO}
  n_applied = sum(1 for f in findings if applied(f))
  signed = sum(1 for f in findings if f.get("status") == "SIGNED")
  source, fell_from = resolve(requested, audited, bbs, estimate)
  
  notes: list = []
  if source == SOURCE_AUDITED:
    notes.append(f"The schedule's {_kg(doc_kg)} with {n_applied} accepted finding(s) applied ({BR.q2(effect):+,} kg).")
    notes.append(_open_note(op))
  elif source == SOURCE_BBS:
    if has_doc and not has_run:
      notes.append(f"The schedule's {_kg(doc_kg)}, {NOT_AUDITED}: no audit has been run on it.")
    elif has_doc:
      notes.append(f"The schedule's {_kg(doc_kg)} as billed, with no finding applied.")
    else:
      notes.append(f"The bar schedule weight of the calculation run, {_kg(ledger_bbs)}.")
    if has_run:
      notes.append(_open_note(op))
  elif source == SOURCE_ESTIMATE:
    notes.append(f"Trace's rule estimate, {_kg(estimate)}.")
  if fell_from:
    why = {SOURCE_AUDITED: NOT_AUDITED if has_doc else "there is no bar schedule", SOURCE_BBS: "there is no bar schedule weight", SOURCE_ESTIMATE: "there is no rule estimate"}[fell_from]
    notes.append(f"The project chose {fell_from}; it is not available ({why}), so the line uses {source or 'nothing'}.")
  gap = None
  if has_doc and ledger_bbs is not None and doc_kg and abs(ledger_bbs - doc_kg) > LEDGER_GAP_SHARE * doc_kg:
    gap = BR.q2(ledger_bbs - doc_kg)
    notes.append(f"The calculation run's REBAR_BBS_WEIGHT is {_kg(ledger_bbs)}, {BR.q2(gap):+,} kg from the schedule document above.")
  quantity = {SOURCE_AUDITED: audited, SOURCE_BBS: bbs, SOURCE_ESTIMATE: estimate}.get(source)
  wastage = None
  if wastage_pct is not None:
    pct = D(str(wastage_pct))
    kg = None if quantity is None else BR.q2(quantity * pct / 100)
    wastage = {"pct": pct, "kg": kg, "total_kg": None if quantity is None else BR.q2(quantity + kg)}
    
  return {
    "figures": {
      FORMULA_BBS: {"formula": FORMULA_BBS, "kg": bbs, "origin": "SCHEDULE" if has_doc else ("LEDGER" if bbs is not None else None), "note": None if bbs is not None else "no bar schedule weight"},
      FORMULA_AUDITED: {"formula": FORMULA_AUDITED, "kg": audited, "origin": "AUDIT" if audited is not None else None, "applied_count": n_applied, "applied_kg": effect, "signed_count": signed,
        "note": None if audited is not None else (NOT_AUDITED if has_doc else "no bar schedule")},
      FORMULA_ESTIMATE: {"formula": FORMULA_ESTIMATE, "kg": estimate, "origin": "LEDGER" if estimate is not None else None, "note": None if estimate is not None else "no rule estimate in the run"},
    },
    "requested_source": requested if requested in SOURCES else None, "source": source, "fell_back_from": fell_from,
    "line": {"formula": SOURCE_FORMULA.get(source), "source": source, "quantity_kg": quantity, "unit": "kg", "note": " ".join(notes), "audited": source == SOURCE_AUDITED},
    "open_findings": {**op, "effect_kg": BR.q2(op["effect_kg"])}, "by_diameter": table, "unattributed_kg": unattributed, "allocated_kg": allocated, "wastage": wastage, "ledger_gap_kg": gap, "ledger_bbs_kg": ledger_bbs,
    "document": document, "has_document": has_doc, "has_audit": bool(has_doc and has_run)}
