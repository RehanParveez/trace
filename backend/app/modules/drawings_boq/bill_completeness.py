from __future__ import annotations
from app.modules.drawings_boq import bill_completeness_steps as BS

FAMILIES = (
  ("EARTHWORK", "Excavation and filling", ("EXC-",)),
  ("CONCRETE", "Concrete", ("CON-",)),
  ("STEEL", "Reinforcement steel", ("STL-",)),
  ("FORMWORK", "Formwork", ("FRM-",)),
  ("MASONRY", "Masonry", ("MAS-",)),
  ("ROOF", "Roof treatment", ("FIN-ROOF", "ROOF-")),
  ("FINISHES", "Plaster, paint and floor finishes", ("FIN-",)),
  ("OPENINGS", "Doors and windows", ("DOR-", "WIN-", "JOI-")),
)
NEEDS = (
  ("CONCRETE", "STEEL", "STEEL_MISSING", "The bill has concrete but no reinforcement steel.",
   "Steel comes from the derived works of the run. Switch derived works on (see the skipped stages above) and run again, or read the bar schedule."),
  ("CONCRETE", "FORMWORK", "FORMWORK_MISSING", "The bill has concrete but no formwork.",
   "Formwork comes from the derived works of the run. Switch derived works on and run again."),
  ("CONCRETE", "EARTHWORK", "EARTHWORK_MISSING", "The bill has concrete but no excavation or filling.",
   "Excavation, PCC and backfill come from the derived works. Switch derived works on, or accept the excavation items read from the plan."),
  ("MASONRY", "FINISHES", "FINISHES_MISSING", "The bill has masonry but no plaster, paint or floor finish.",
   "Wall finishes come from the derived works and the room schedule. Switch derived works on and accept the rooms."),
  ("CONCRETE", "ROOF", "ROOF_TREATMENT_MISSING", "The bill has slabs but no roof treatment.",
   "Roof treatment comes from the derived works. Switch derived works on and enter the roof treatment."),
)

STAGE_NOTES = {
  "pdf_takeoff": ("The measurements from the PDF drawings", "Accept and confirm the measurements of the PDF drawing, then run again."),
  "derived_works": ("Excavation, PCC, backfill, damp-proof course, plaster and paint, formwork, steel, roof treatment and floor works",
  "A run with a PDF drawing switches derived works on by itself (ENGINE_PDF_DERIVED_AUTO, on by default). If that setting was turned off, add this company's id (or *) to ENGINE_DERIVED_ORG_IDS and ENGINE_SPEC_ORG_IDS in the server settings; restart the API and the calculation worker; run again."),
  "pdf_space": ("The cut and net of the PDF quantities by room and floor", "It runs when derived works or stage mode is switched on."),
  "layer_split": ("The split of floor and roof layers", "Set ENGINE_LAYER_ORG_IDS (it also needs ENGINE_SPEC_ORG_IDS) if you want it."),
  "stage_split": ("The split of the quantities into work stages", "Set ENGINE_STAGE_ORG_IDS (it also needs ENGINE_SPEC_ORG_IDS) if you want it."),
}

HELD_FIX = {
  "VALUE_MISSING": "A size is missing (a height or a depth). Type it once for the project on the approve screen.",
  "ASSUMED": "The reader assumed a value. Review them, then approve with 'accept assumed'.",
  "WARNING": "The reader has a warning on the item. Review them, then approve with 'accept warned'.",
  "CHECK_WARNS": "A cross-check has a warning on the item. Review it, then approve with 'accept warned'.",
  "ADDED_FROM_SECOND_SHEET": "Read again from a second sheet. Approve with 'accept added' once you have looked.",
  "FLOOR_SOURCE_UNDECIDED": "A floor is printed on several sheets. Choose the sheet that governs it.",
  "LAYOUT_SOURCE_UNDECIDED": "A plan is printed on several sheets. Choose the sheet that governs it.",
  "MARK_ACCEPTED_ELSEWHERE": "The same mark was accepted from another sheet.",
  "MARK_ON_SEVERAL_SHEETS": "The same mark is shown on another sheet with the same count and size. Choose the sheet in the list of marks.",
  "MARK_SHEETS_DISAGREE": "The same mark is shown on several sheets with a different count or size. Choose the sheet in the list of marks.",
  "NOT_A_PLAN_SHEET": "Read from a sheet that is not a plan (a detail, a section or a schedule). These are not measured on purpose.",
  "NOT_MEASURABLE": "Not a thing that can be measured from the drawing.",
  "ERROR": "The item has an error and can not be accepted.",
}

HELD_LABEL = {
  "VALUE_MISSING": "need a size typed", "ASSUMED": "carry an assumed value", "WARNING": "carry a warning", "CHECK_WARNS": "carry a cross-check warning",
  "ADDED_FROM_SECOND_SHEET": "were added from a second sheet", "FLOOR_SOURCE_UNDECIDED": "wait for the sheet of their floor to be chosen",
  "LAYOUT_SOURCE_UNDECIDED": "wait for the governing sheet of their plan to be chosen", "MARK_ACCEPTED_ELSEWHERE": "were accepted from another sheet",
  "MARK_ON_SEVERAL_SHEETS": "are the same mark as one on another sheet", "MARK_SHEETS_DISAGREE": "are marks whose sheets show different counts or sizes",
  "NOT_A_PLAN_SHEET": "are on sheets that are not plans", "NOT_MEASURABLE": "can not be measured", "ERROR": "have an error",
}

def _family_of(code: str) -> str | None:
  for key, _, prefixes in FAMILIES:
    if any(code.startswith(p) for p in prefixes):
      return key
  return None

def families(ledger: list) -> list:
  rows: dict = {k: 0 for k, _, _ in FAMILIES}
  codes: dict = {k: [] for k, _, _ in FAMILIES}
  for r in ledger:
    k = _family_of(str(r.get("code") or ""))
    if k:
      rows[k] += int(r.get("rows") or 0)
      codes[k].append(r["code"])
  return [{"family": k, "label": label, "present": rows[k] > 0, "rows": rows[k], "codes": sorted(set(codes[k]))} for k, label, _ in FAMILIES]

def _skipped(stages: list) -> list:
  out = []
  for s in stages:
    if s.get("status") != "SKIPPED":
      continue
    reason = str((s.get("counts") or {}).get("reason") or "skipped in this run")
    lost, fix = STAGE_NOTES.get(s["stage"], (None, None))
    out.append({"stage": s["stage"], "reason": reason, "lost": lost, "fix": fix})
  return out

def build(*, stages: list, run_settings: dict, ledger: list, funnel: dict | None, held_by_reason: dict | None, derived: dict | None = None, boq_error: str | None = None) -> dict:
  run_settings = run_settings or {}
  fam = families(ledger)
  present = {f["family"] for f in fam if f["present"]}
  total_rows = sum(int(r.get("rows") or 0) for r in ledger)
  skipped = _skipped(stages)
  skipped_names = {s["stage"] for s in skipped}
  step_rows = BS.steps(derived)
  findings: list = []

  def add(code: str, severity: str, title: str, detail: str, fix: str | None) -> None:
    findings.append({"code": code, "severity": severity, "title": title, "detail": detail, "fix": fix})

  funnel = funnel or {}
  confirmed, draft, undecided = int(funnel.get("confirmed") or 0), int(funnel.get("draft") or 0), int(funnel.get("undecided") or 0)
  has_pdf = (confirmed + draft + undecided) > 0 or "pdf_takeoff" in {s["stage"] for s in stages if s.get("status") != "SKIPPED"}

  if has_pdf and confirmed == 0:
    add("NO_CONFIRMED_MEASUREMENTS", "BLOCKER", "No PDF measurement is confirmed",
      f"The run counts only confirmed measurements. This project has {draft} accepted but not confirmed and {undecided} read but not accepted.",
      "Approve the PDF drawing (with the accept options you trust), then run again.")
  elif has_pdf:
    if draft:
      add("DRAFT_NOT_CONFIRMED", "WARNING", f"{draft} accepted measurements are not confirmed",
        "A measurement that is accepted but not confirmed is not in the run.", "Confirm them on the approve screen, then run again.")
    total = confirmed + draft + undecided
    if undecided and confirmed / total < 0.5:
      add("MOST_ITEMS_NOT_ACCEPTED", "WARNING", f"Only {confirmed} of {total} read items are in the run",
        f"{undecided} items were read from the drawing and never accepted, so they are not in the bill.",
        "Open the approve screen and clear the reasons below, largest first.")
    elif undecided:
      add("SOME_ITEMS_NOT_ACCEPTED", "INFO", f"{undecided} read items are not accepted", f"{confirmed} of {total} read items are in the run.", None)
  for code, n in sorted((held_by_reason or {}).items(), key=lambda kv: -kv[1]):
    if n and code in HELD_FIX and code not in ("ALREADY_DECIDED",):
      sev = "INFO" if code in ("NOT_A_PLAN_SHEET", "NOT_MEASURABLE") else "WARNING"
      add(f"HELD_{code}", sev, f"{n} items {HELD_LABEL.get(code, 'are held')}", HELD_FIX[code], None)

  for s in skipped:
    if s["stage"] == "derived_works" and has_pdf:
      add("DERIVED_WORKS_SKIPPED", "BLOCKER", "Derived works did not run", f"Reason recorded: {s['reason']}. Missing because of it: {s['lost']}.", s["fix"])
    elif s["stage"] == "pdf_takeoff" and has_pdf and confirmed:
      add("PDF_TAKEOFF_SKIPPED", "BLOCKER", "The PDF measurements were not used", f"Reason recorded: {s['reason']}.", s["fix"])
    elif s["stage"] in ("pdf_space", "layer_split", "stage_split"):
      add(f"{s['stage'].upper()}_SKIPPED", "INFO", f"{s['stage']} did not run", f"Reason recorded: {s['reason']}. Not done: {s['lost']}.", s["fix"])

  if has_pdf and "derived_works" not in skipped_names and not run_settings.get("derived") and not any(f["code"] == "DERIVED_WORKS_SKIPPED" for f in findings):
    add("DERIVED_OFF", "WARNING", "Derived works were not switched on for this run", "The settings of the run do not include derived works.", STAGE_NOTES["derived_works"][1])
  if has_pdf and not run_settings.get("spec"):
    add("SPEC_OFF", "INFO", "Specifications were not switched on for this run", "Layer and stage splits need it.", "Set ENGINE_SPEC_ORG_IDS to this company's id or *.")

  if boq_error:
    add("BOQ_BUILD_FAILED", "BLOCKER", "The bill could not be built from the ledger of this run",
      f"The calculation finished and its ledger rows are saved, but building the bill from them failed: {boq_error}",
      "Run again. If it fails again, send this message to support.")

  covered: set = set()
  for driver, need, code, title, fix in NEEDS:
    if driver in present and need not in present:
      why = BS.why_missing(step_rows, need)
      if why:
        covered.add(need)
      add(code, "WARNING", title, why[0] if why else "Checked against the rows of this run.",
        (why[1] or "The derived step ran and added nothing for the reason above.") if why
        else ("The derived works ran and added none of this. Check the held items on the approve screen." if step_rows else fix))
  for code, severity, title, detail, fix in BS.findings(step_rows, set(present), covered):
    add(code, severity, title, detail, fix)

  if total_rows <= 2:
    verdict = "EMPTY"
  elif any(f["severity"] in ("BLOCKER", "WARNING") for f in findings):
    verdict = "PARTIAL"
  else:
    verdict = "NO_KNOWN_GAPS"
  order = {"BLOCKER": 0, "WARNING": 1, "INFO": 2}
  findings.sort(key=lambda f: order[f["severity"]])
  return {"verdict": verdict, "ledger_rows": total_rows, "families": fam, "skipped_stages": skipped, "funnel": {"confirmed": confirmed, "draft": draft, "undecided": undecided},
    "held_by_reason": dict(held_by_reason or {}), "derived_steps": step_rows, "boq_error": boq_error, "findings": findings,
    "note": "This lists known gaps. A bill with no known gaps is not proven complete: compare it with a bill you trust."}
