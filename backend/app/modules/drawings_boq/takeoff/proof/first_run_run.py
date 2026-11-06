from __future__ import annotations
import argparse
import json
import os
import sys
from app.engine.catalogue import conventions as CV
from app.modules.drawings_boq.takeoff.completeness import facts as F
from app.modules.drawings_boq.takeoff.first_run import job as JB
from app.modules.drawings_boq.takeoff.first_run import report as RP
from app.modules.drawings_boq.takeoff.first_run import stages as ST
from app.modules.drawings_boq.takeoff.profile import convention as CVN
from app.modules.drawings_boq.takeoff.profile import run as PRUN
from app.modules.drawings_boq.takeoff.proof import completeness_run as CR
from app.modules.drawings_boq.takeoff.proof.reading import adapter as AD

def offline_bindings(pdfs: list | None = None, plains: list | None = None, lines: list | None = None, page_facts: list | None = None) -> dict:
  """The job's stages on the offline reader: the PDFs are read, or the readings are handed in (gate 16 hands in the reading gate 14 collected, so nothing is read twice). The engine's lines come in at the quantities stage. Nothing here names a case."""
  def register(state: dict) -> None:
    got = plains if plains is not None else [CR.plain_read(AD.read_items(p)) for p in pdfs or []]
    if not got:
      raise JB.Upstream("no PDF was given")
    state["plain"] = CR.merge(got)
    state["pages"] = CR.page_rows(state["plain"])
    if page_facts is not None:
      state["page_facts"] = page_facts
    elif pdfs:
      state["page_facts"] = [f for n, p in enumerate(pdfs) for f in PRUN.facts_of_pdf(p, n * CR.SHEET_SHIFT)]

  def need(state: dict) -> dict:
    if "plain" not in state:
      raise JB.Upstream("the register stage gave no reading")
    return state["plain"]

  def profile(state: dict) -> None:
    plain = need(state)
    state["facts"] = F.project_facts(state["pages"], state.get("decisions"), state.get("storeys"), CR.join_floors_of(plain))
    if state.get("page_facts"):
      state["convention"] = CVN.build(state["page_facts"], state["pages"])

  def scale(state: dict) -> None:
    plain = need(state)
    pages = list(plain["pages"].values())
    state["scale"] = {"pages": len(pages), "with_scale": sum(1 for p in pages if p.get("mm_per_pt"))}

  def read(state: dict) -> None:
    state["read_counts"] = {"items": len(need(state)["items"]), "pages": len(need(state)["pages"])}

  def members(state: dict) -> None:
    state["evidence"] = CR.evidence_of(need(state), None)

  def quantities(state: dict) -> None:
    if lines is not None and "evidence" in state:
      state["evidence"]["lines"] = [dict(ln) for ln in lines if ln.get("family") and ln.get("value") is not None]
      ST.ledger_stage(state)

  return {"register": register, "profile": profile, "scale": scale, "read": read, "members": members, "ledger": ST.ledger_stage, "quantities": quantities, "boq": ST.boq_stage, "questions": ST.questions_stage}

def run_project(pdfs: list | None = None, plains: list | None = None, lines: list | None = None, storeys: list | None = None, conventions: list | None = None,
  answers: dict | None = None, methods: dict | None = None, progress=None, bindings: dict | None = None) -> tuple:
  state = {"storeys": storeys, "conventions": list(conventions or []), "answers": dict(answers or {}), "methods": dict(methods or {})}
  b = bindings if bindings is not None else offline_bindings(pdfs, plains, lines)
  out = JB.run(b, state, progress=progress)
  return state, out, RP.build(state, out), b

def corpus(cases_dir: str | None, scores: str | None, only: list | None, out_dir: str | None) -> int:
  from app.modules.drawings_boq.takeoff.proof import case_io as CIO
  total, bad = 0.0, 0
  rows = []
  for name in only or CIO.list_cases():
    case = CIO.load_case(os.path.join(CIO.HERE, name))
    if not case.get("pdfs"):
      continue
    found, problems = CIO.find_files(case, CIO.cases_dir(cases_dir))
    if problems:
      print(f"{name}: {'; '.join(problems)}")
      bad += 1
      continue
    state, out, rep, _b = run_project(pdfs=[found[n] for n in case["pdfs"]], lines=CR.lines_of(scores, name) if scores else None, storeys=CR.storeys_of(name))
    total += out["seconds"]
    print(RP.render(rep, name))
    rows.append({"case": name, "report": rep})
    bad += bool(rep["failed"])
  if out_dir:
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "first_run.json"), "w", encoding="utf-8") as fh:
      json.dump(rows, fh, indent=1, default=str)
  print(f"{len(rows)} project(s), {total:.1f}s, {bad} with a failed stage")
  return 1 if bad else 0

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Run the first-upload job on PDFs with the offline reader and print the report. With --corpus, on every case folder's PDFs.")
  ap.add_argument("pdfs", nargs="*")
  ap.add_argument("--corpus", action="store_true")
  ap.add_argument("--cases-dir")
  ap.add_argument("--scores", help="a score output folder whose engine lines feed the quantities stage")
  ap.add_argument("--only", nargs="*")
  ap.add_argument("--out")
  ap.add_argument("--conventions", action="store_true", help="switch every Pakistan convention on")
  args = ap.parse_args(argv)
  if args.corpus:
    return corpus(args.cases_dir, args.scores, args.only, args.out)
  state, out, rep, _b = run_project(pdfs=args.pdfs, conventions=CV.ids() if args.conventions else None)
  print(RP.render(rep))
  return 1 if rep["failed"] else 0

if __name__ == "__main__":
  sys.exit(main())
