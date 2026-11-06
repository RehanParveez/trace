from __future__ import annotations
import os
from app.engine.catalogue import conventions as CV
from app.engine.catalogue import loader as CAT
from app.engine.catalogue import model as CM
from app.engine.measure import readings as RD
from app.modules.drawings_boq.takeoff.completeness import expected as EX
from app.modules.drawings_boq.takeoff.completeness import facts as F
from app.modules.drawings_boq.takeoff.completeness import ledger as LG
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.proof import completeness_run as CR
from app.modules.drawings_boq.takeoff.questions import answers as AN
from app.modules.drawings_boq.takeoff.questions import engine as QE
from app.modules.drawings_boq.takeoff.questions import keys as QK

class Collector:
  """Gathers each set's reading as gate 14 reads it, so gate 16 judges the same reading without reading the PDFs a second time."""
  def __init__(self) -> None:
    self.sets: dict = {}

  def __call__(self, ref, read) -> None:
    self.sets[ref.pdf_key] = (ref.case, CR.plain_read(read))

def silent_gaps(plain: dict) -> list:
  """Pages whose sheet kind expects reader classes but whose coverage leaves one out: a class neither read nor reported as not read."""
  out = []
  for key, p in sorted(plain["pages"].items(), key=lambda kv: int(kv[0])):
    reg = p.get("register") or {}
    role, kind = reg.get("role"), reg.get("plan_kind")
    name = f"PLAN/{kind}" if role == "PLAN" and kind else role
    for cls in RD.EXPECTED_CLASSES.get(name or "", ()):
      if cls not in (p.get("coverage") or {}):
        out.append(f"sheet {p.get('sheet') or key} ({name}): {cls} is expected and not reported")
  return out

def assumption_problems(result: dict, on: bool) -> list:
  """With conventions off nothing is ASSUMED; with them on every assumption names its source and a range the value lies inside, and a quantity built on one carries a range."""
  bad = []
  
  for e in result["ledger"]:
    tag = f"{e['element']}/{e['floor']}"
    if not on and e["state"] == LG.ASSUMED:
      bad.append(f"{tag}: ASSUMED with the conventions off")
    for a in e["assumptions"]:
      rng = a.get("range")
      if not a.get("source") or not rng or len(rng) != 2 or not rng[0] <= a["value"] <= rng[1]:
        bad.append(f"{tag}: assumption {a.get('input')} has no source or no range holding its value")
    if e["state"] == LG.ASSUMED and e["quantity"] is not None and not e["quantity"].get("range"):
      bad.append(f"{tag}: ASSUMED with a quantity and no range")
  return bad

def invariants(result: dict, plain: dict) -> list:
  items = CAT.items()
  by_id = {it.id: it for it in items}
  floors = set(F.values(result["facts"])["floors"] or []) | {LG.ALL}
  bad = []
  seen = {e["element"] for e in result["ledger"]}
  
  for it in items:
    if it.id not in seen:
      bad.append(f"{it.id} has no ledger entry")
  for e in result["ledger"]:
    tag = f"{e['element']}/{e['floor']}"
    item = by_id.get(e["element"])
    if e["state"] not in CM.STATES:
      bad.append(f"{tag}: state {e['state']} is not one of the five")
    if e["state"] in (LG.NOT_READ, LG.ASKED, LG.NOT_APPLICABLE) and not e["reasons"]:
      bad.append(f"{tag}: {e['state']} with no reason")
    if e["state"] == LG.ASKED and not e["questions"]:
      bad.append(f"{tag}: ASKED with no question")
    if e["state"] == LG.MEASURED and not (e["members"] or e["quantity"]):
      bad.append(f"{tag}: MEASURED with no member and no quantity")
    if e["state"] == LG.ASSUMED and not e["assumptions"]:
      bad.append(f"{tag}: ASSUMED with no assumption")
    if e["floor"] not in floors:
      bad.append(f"{tag}: floor is not a floor of the project")
    if item is not None and item.derived and e["state"] != LG.NOT_APPLICABLE and LG.SET_NOT_SUPPLIED not in e["reasons"] and not any(r.startswith(LG.DERIVED_FROM) for r in e["reasons"]):
      bad.append(f"{tag}: a derived item that does not say what it is derived from")
    if result["scope"] == "STRUCTURE_ONLY" and item is not None:
      need = EX.needed_sets(item)
      if need and F.STRUCTURE not in need and e["state"] != LG.NOT_APPLICABLE:
        bad.append(f"{tag}: needs {', '.join(need)} yet is {e['state']} in a structure-only set")
      if LG.SET_NOT_SUPPLIED in e["reasons"]:
        bad.append(f"{tag}: asks for a set in a structure-only set")
  bad += silent_gaps(plain)
  return bad

def default_answer(q: dict) -> dict | None:
  """The answer that takes a question's own default: the convention's value, the first option that takes the reading as read, or the default option."""
  if q["kind"] == QK.INPUT:
    return None if not q["default"] else {"value": str(q["default"]["value"]), "by": "gate", "at": "-"}
  want = {QK.CONFIRM: QK.ACCEPT, QK.CONFLICT: QK.PRINTED, QK.SUPPLY: QK.NOT_IN_SCOPE}.get(q["kind"])
  if q["kind"] == QK.METHOD:
    want = next((o["value"] for o in q["options"] if o.get("is_default")), None)
  return {"value": want, "by": "gate", "at": "-"} if want else None

def question_problems(case: str, plain: dict, res: dict, lines: list, on: list, answers: dict) -> tuple:
  """Every ASKED entry's questions have a key and a kind and are in the list of questions; no input is asked once per item; answering with the defaults never adds a question or an ASKED entry, never leaves an answered question open, and keeps every invariant."""
  bad = []
  qs = QE.build(res["ledger"], answers, on)
  keys = {q["key"] for q in qs}
  for e in res["ledger"]:
    for q in e["questions"]:
      if not q.get("key") or q.get("kind") not in QK.KINDS:
        bad.append(f"{e['element']}/{e['floor']}: a question with no key or kind: {q['ask'][:60]}")
      elif q["key"] not in keys:
        bad.append(f"{e['element']}/{e['floor']}: question {q['key']} is not in the project's list")
        
  for q in qs:
    if q["state"] == QE.OPEN and not q["blocks"] and q["kind"] != QK.METHOD:
      bad.append(f"question {q['key']} blocks no item")
  inputs = [q["key"] for q in qs if q["kind"] == QK.INPUT]
  if len(inputs) != len(set(inputs)):
    bad.append("an input is asked more than once")
  given = {q["key"]: a for q in qs if q["state"] == QE.OPEN for a in [default_answer(q)] if a}
  after = CR.run_set(plain, CR.storeys_of(case), lines, conventions=on, answers={**answers, **given})
  more = QE.build(res["ledger"], {**answers, **given}, on)
  still = [q["key"] for q in more if q["key"] in given and q["state"] == QE.OPEN]
  
  if still:
    bad.append(f"answered and still open: {', '.join(still)}")
  was, now = res["summary"]["by_state"], after["summary"]["by_state"]
  if now[LG.ASKED] > was[LG.ASKED]:
    bad.append(f"answering with the defaults raised ASKED from {was[LG.ASKED]} to {now[LG.ASKED]}")
  after_open = [q for q in QE.build(after["ledger"], {**answers, **given}, on) if q["state"] == QE.OPEN]
  if len(after_open) > len([q for q in qs if q["state"] == QE.OPEN]):
    bad.append("answering with the defaults left more questions open")
  bad += [f"after the defaults: {p}" for p in invariants(after, plain)]
  return bad, len([q for q in qs if q["state"] == QE.OPEN]), len(after_open)

def projects(collector: Collector) -> dict:
  out: dict = {}
  for _key, (case, plain) in collector.sets.items():
    out.setdefault(case, []).append(plain)
  return {case: CR.merge(plains) for case, plains in out.items()}

def gate(collector: Collector, score_dir: str | None = None) -> tuple:
  if not collector.sets:
    return False, "no set was read: gate 16 judges the reading gate 14 collects", []
  problems, totals, entries = [], {s: 0 for s in CM.STATES}, 0
  structure_only = assumed_on = computed = open_total = after_total = 0
  merged = projects(collector)
  for case, plain in sorted(merged.items()):
    lines = CR.lines_of(score_dir, case)
    res = CR.run_set(plain, CR.storeys_of(case), lines)
    on_res = CR.run_set(plain, CR.storeys_of(case), lines, conventions=CV.ids())
    problems += [f"{case}: {p}" for p in invariants(res, plain)]
    problems += [f"{case}: {p}" for p in assumption_problems(res, False)]
    problems += [f"{case} (conventions on): {p}" for p in invariants(on_res, plain) + assumption_problems(on_res, True)]
    case_dir = os.path.join(CIO.HERE, case)
    answers = AN.split_case(CIO.load_decisions(case_dir))[1] if os.path.isdir(case_dir) else {}
    for tag, run, on in (("", res, []), (" (conventions on)", on_res, CV.ids())):
      bad, n_open, n_after = question_problems(case, plain, run, lines, on, answers)
      problems += [f"{case}{tag}: {p}" for p in bad]
      
      if not on:
        open_total += n_open
        after_total += n_after
    assumed_on += on_res["summary"]["by_state"][LG.ASSUMED]
    computed += sum(1 for e in res["ledger"] if e["state"] in (LG.MEASURED, LG.ASSUMED) and any(r.startswith(LG.DERIVED_FROM) for r in e["reasons"]) and e["quantity"])
    entries += res["summary"]["entries"]
    structure_only += res["scope"] == "STRUCTURE_ONLY"
    for s, n in res["summary"]["by_state"].items():
      totals[s] += n
  shown = ", ".join(f"{n} {s}" for s, n in totals.items())
  if problems:
    return False, f"{len(problems)} completeness problem(s) over {len(merged)} project(s)", problems
  return True, f"{len(collector.sets)} PDFs in {len(merged)} projects, {entries} ledger entries ({shown}), {structure_only} structure-only; {computed} derived items computed from the engine's lines, {assumed_on} ASSUMED with the conventions on and none with them off; {open_total} questions open over the projects, {after_total} after answering with the defaults; every item accounted for, no silent gap", []
