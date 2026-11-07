from __future__ import annotations
import inspect
from app.modules.drawings_boq.takeoff.completeness import ledger as LG
from app.modules.drawings_boq.takeoff.first_run import job as JB
from app.modules.drawings_boq.takeoff.first_run import report as RP
from app.modules.drawings_boq.takeoff.first_run import service as SV
from app.modules.drawings_boq.takeoff.first_run import stages as ST
from app.modules.drawings_boq.takeoff.proof import completeness_run as CR
from app.modules.drawings_boq.takeoff.proof import first_run_run as FR
from app.modules.drawings_boq.takeoff.proof import gate16 as G16
from app.modules.drawings_boq.takeoff.questions import engine as QE

def _boom(state: dict) -> None:
  raise RuntimeError("injected failure")

def failure_problems(plain: dict, storeys, lines) -> list:
  """A stage that fails does not stop the job and does not leave a guess: every item that applies is NOT_READ and says which stage failed, and the stages after it still report."""
  bad = []
  for stage in JB.UPSTREAM:
    b = FR.offline_bindings(plains=[plain], lines=lines)
    b[stage] = _boom
    state, out, rep, _ = FR.run_project(plains=[plain], lines=lines, storeys=storeys, bindings=b)
    if stage not in out["failed"]:
      bad.append(f"{stage} raised and the job did not report it failed")
    if [s["name"] for s in out["stages"]] != list(JB.STAGES):
      bad.append(f"{stage} failed and a later stage did not report")
    wrong = [e for e in state["ledger"] if e["state"] != LG.NOT_APPLICABLE and (e["state"] != LG.NOT_READ or f"{JB.STAGE_FAILED}:" not in " ".join(e["reasons"]))]
    if wrong:
      bad.append(f"{stage} failed and {len(wrong)} item(s) are not NOT_READ with the failed stage named, first {wrong[0]['element']}/{wrong[0]['floor']} {wrong[0]['state']}")
    for later in ("ledger", "boq", "questions"):
      row = next(s for s in out["stages"] if s["name"] == later)
      if row["status"] != JB.DONE:
        bad.append(f"{stage} failed and {later} is {row['status']}")
  return bad

def rerun_problems(plain: dict, storeys, lines) -> tuple:
  """An answer re-runs only what it touches: no item outside the answer's closure changes, and the result is the one a whole run with the answer gives."""
  state, out, rep, b = FR.run_project(plains=[plain], lines=lines, storeys=storeys)
  given = {q["key"]: a for q in state["questions"] if q["state"] == QE.OPEN for a in [G16.default_answer(q)] if a}
  if not given:
    return [], 0, 0
  state["answers"] = dict(given)
  r = JB.rerun(b, state, sorted(given))
  bad = []
  if r["moved_outside"]:
    bad.append(f"an answer moved items outside the ones it touches: {', '.join(r['moved_outside'][:5])}")
  if [s["name"] for s in r["stages"]] != list(JB.RERUN_STAGES):
    bad.append("the re-run ran a stage other than the four that depend on answers")
  whole, _, _, _ = FR.run_project(plains=[plain], lines=lines, storeys=storeys, answers=given)
  if whole["ledger"] != state["ledger"]:
    bad.append("the re-run's ledger differs from a whole run with the same answers")
  if [q["key"] for q in whole["questions"]] != [q["key"] for q in state["questions"]]:
    bad.append("the re-run's questions differ from a whole run with the same answers")
  return bad, len(r["items"]), len(given)

def run_problems(plain: dict, storeys, lines) -> list:
  bad = []
  state, out, rep, _ = FR.run_project(plains=[plain], lines=lines, storeys=storeys)
  if out["failed"]:
    bad.append(f"stages failed on a good reading: {', '.join(out['failed'])}")
  if [s["name"] for s in out["stages"]] != list(JB.STAGES) or any(s["status"] != JB.DONE for s in out["stages"]):
    bad.append("not every stage reported DONE")
  direct = CR.run_set(plain, storeys, lines)
  if rep["items"] != direct["summary"]["by_state"]:
    bad.append(f"the report's item states {rep['items']} differ from the ledger's {direct['summary']['by_state']}")
  if sum(rep["items"].values()) != rep["entries"]:
    bad.append("the report's items do not add up to the ledger's entries")
  for unit, t in rep["boq"]["totals"].items():
    rows = [r for r in state["boq"]["rows"] if r["unit"] == unit]
    if abs(sum(r["quantity"] for r in rows if r["state"] == LG.MEASURED) - t[LG.MEASURED]) > 0.01:
      bad.append(f"the BOQ draft's {unit} total is not the sum of its rows")
  if not rep["boq"]["rates_loaded"] and rep["boq"]["money"] is not None:
    bad.append("a money total appears with no rates loaded")
  if any(r["amount"] is not None for r in state["boq"]["rows"]) and not rep["boq"]["rates_loaded"]:
    bad.append("a BOQ row has an amount with no rate")
  if rep["questions"]["open"] != len([q for q in state["questions"] if q["state"] == QE.OPEN]):
    bad.append("the report's open questions differ from the question list")
  text = RP.render(rep)
  if "stages:" not in text:
    bad.append("the rendered report does not list the stages")
  return bad

def source_problems() -> list:
  """The job knows no case: nothing under first_run reads a case folder or names one."""
  bad = []
  for mod in (JB, ST, RP, SV):
    src = inspect.getsource(mod)
    for word in ("case_io", "CASES", "decisions.yaml", "plot1", "191-C"):
      if word in src:
        bad.append(f"{mod.__name__} mentions {word}")
  return bad

def gate(collector: G16.Collector, score_dir: str | None = None) -> tuple:
  if not collector.sets:
    return False, "no set was read: gate 18 runs the job on the reading gate 14 collects", []
  merged = G16.projects(collector)
  problems = source_problems()
  ran = reran = touched = 0
  for case, plain in sorted(merged.items()):
    lines = CR.lines_of(score_dir, case)
    storeys = CR.storeys_of(case)
    problems += [f"{case}: {p}" for p in run_problems(plain, storeys, lines)]
    bad, n_items, n_answers = rerun_problems(plain, storeys, lines)
    problems += [f"{case}: {p}" for p in bad]
    reran += bool(n_answers)
    touched += n_items
    ran += 1
  first = sorted(merged)[0]
  problems += [f"{first}: {p}" for p in failure_problems(merged[first], CR.storeys_of(first), CR.lines_of(score_dir, first))]
  if problems:
    return False, f"{len(problems)} first-upload job problem(s) over {ran} project(s)", problems
  return True, f"{ran} projects run through all {len(JB.STAGES)} stages with no case folder; a failure in each of the {len(JB.UPSTREAM)} reading stages leaves every applicable item NOT_READ and naming it; {reran} re-run(s) after answers touched {touched} items and moved none outside them, and matched a whole run", []
