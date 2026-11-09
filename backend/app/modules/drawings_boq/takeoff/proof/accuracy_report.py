from __future__ import annotations
import argparse
import json
import os
import sys
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.run import reading_adapter as AD
from app.modules.drawings_boq.takeoff.proof.reading import sets as S
from app.modules.drawings_boq.takeoff.run import completeness as RC
from app.modules.drawings_boq.takeoff.proof import completeness_run as CR
from app.engine.catalogue import conventions as CV
from app.modules.drawings_boq.takeoff.completeness import confidence as CONF
from app.modules.drawings_boq.takeoff.review import rows as RW
from app.engine.catalogue import confidence as CFG
from app.modules.drawings_boq.takeoff.accuracy import render as RN
from app.modules.drawings_boq.takeoff.accuracy import report as ACC
from app.modules.drawings_boq.takeoff.accuracy import track as TRK
from app.modules.drawings_boq.takeoff.run import first_run_bindings as FR
from app.modules.drawings_boq.takeoff.completeness import ledger as LG

def read_case(name: str, cases_dir: str | None = None) -> dict:
  case = CIO.load_case(os.path.join(CIO.HERE, name))
  found, problems = CIO.find_files(case, CIO.cases_dir(cases_dir))
  if problems:
    raise SystemExit(f"{name}: {' '.join(problems)}")
  rows = AD.read_case(case, found)
  refs = [r for r in S.find_sets(cases_dir) if r.case == name and not r.link]
  plains = [RC.plain_read(AD.items_of(rows[r.pdf])) for r in refs if r.pdf in rows]
  if not plains:
    raise SystemExit(f"{name}: no PDF of the case was read")
  return RC.merge(plains)

def run_state(plain: dict, name: str, score_dir: str | None, conventions: bool) -> dict:
  state, _out, _rep, _b = FR.run_project(plains=[plain], lines=CR.lines_of(score_dir, name), storeys=CR.storeys_of(name), conventions=CV.ids() if conventions else [])
  return state

def offline_lines(state: dict, rows: list, conf_shown: bool) -> list:
  checks = state.get("checks") or []
  bands = CONF.of_entries(state["ledger"], state["evidence"], checks)
  names = {}
  open_by = {}
  
  for r in rows:
    if r.get("state") == "OPEN":
      for el in r.get("touches") or []:
        open_by[el] = open_by.get(el, 0) + 1
        
  out = []
  for b in state["boq"]["rows"]:
    share = 1.0 if b["state"] == LG.ASSUMED else 0.0
    band, why = CONF.line_band([b["element"]], bands, share)
    amount = b.get("amount")
    out.append({"code": b["element"], "description": b["name"], "floor": b["floor"], "unit": b["unit"], "qty": b["quantity"], "amount": amount,
      "measured_amount": None if amount is None else round(amount * (1 - share), 2), "assumed_amount": None if amount is None else round(amount * share, 2), "assumed_share": share,
      "band": band, "band_why": why, "elements": [b["element"]], "open_rows": open_by.get(b["element"], 0)})
  return out

def report_for(name: str, cases_dir: str | None = None, score_dir: str | None = None, conventions: bool = False, plain: dict | None = None) -> dict:
  plain = plain or read_case(name, cases_dir)
  state = run_state(plain, name, score_dir, conventions)
  rows = RW.build(ledger=state["ledger"], questions=state["questions"], evidence=state["evidence"], reads=[], answers=state.get("answers") or {}, review={}, crops={}, rates=state.get("rates"))["rows"]
  conf = {"shown": CFG.shown()}
  track = TRK.current(ACC.TEXT)
  rep = ACC.build(project={"case": name, "conventions": "ON" if conventions else "OFF"}, lines=offline_lines(state, rows, conf["shown"]), entries=state["ledger"], rows=rows, conf=conf, track=track)
  rep["figures"] = figures(rep)
  return rep

def figures(rep: dict) -> dict:
  c, m, q, k = rep["coverage"]["total"], rep["money"], rep["questions"], rep["check_first"]
  return {"items": c["total"], "measured": c["MEASURED"], "assumed": c["ASSUMED"], "asked": c["ASKED"], "not_read": c["NOT_READ"], "with_quantity_pct": c["with_quantity_pct"], "priced": m["priced"],
    "lines": m["lines"], "open_questions": q["open"], "assumption_inputs": rep["assumptions"]["count"], "confidence_shown": rep["confidence"]["shown"], "check_first": len(k["lines"]), "ranked_by": k["ranked_by"],
    "track_state": rep["track_record"]["state"]}

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Write the client accuracy report of each case from the benchmark: reading, first-upload job, calibration and history.csv.")
  ap.add_argument("cases", nargs="+")
  ap.add_argument("--cases-dir")
  ap.add_argument("--score-dir", help="a proof.score output folder; its engine lines let the quantity checks run")
  ap.add_argument("--conventions", action="store_true", help="switch every Pakistan convention on, as a company can")
  ap.add_argument("--out", default="accuracy_out")
  a = ap.parse_args(argv)
  
  os.makedirs(a.out, exist_ok=True)
  for name in a.cases:
    rep = report_for(name, a.cases_dir, a.score_dir, a.conventions)
    tag = f"{name}{'_conventions' if a.conventions else ''}"
    with open(os.path.join(a.out, f"accuracy_{tag}.json"), "w", encoding="utf-8") as fh:
      json.dump(rep, fh, indent=1, sort_keys=True, ensure_ascii=False, default=str)
    with open(os.path.join(a.out, f"accuracy_{tag}.md"), "w", encoding="utf-8") as fh:
      fh.write(RN.markdown(rep))
    f = rep["figures"]
    print(f"{name}: {f['items']} items: {f['measured']} measured, {f['assumed']} assumed, {f['asked']} asked, {f['not_read']} not read; {f['open_questions']} open questions; confidence {'shown' if f['confidence_shown'] else 'not shown'}; track record {f['track_state']}")
  return 0

if __name__ == "__main__":
  sys.exit(main())
