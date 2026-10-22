from __future__ import annotations
from app.modules.drawings_boq.takeoff.tuning import registry as R
import importlib.util
import re
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.tuning import decide as D
from app.modules.drawings_boq.takeoff.tuning import ledger as LG

def literal(p: R.Param, v) -> str:
  if p.kind == "int":
    return str(int(v))
  s = repr(float(v))
  return s if ("." in s or "e" in s) else s + ".0"

def source_of(module: str) -> tuple:
  spec = importlib.util.find_spec(module)
  path = spec.origin
  with open(path, "rb") as f:
    return path, f.read().decode("utf-8-sig")

def _line_for(text: str, attr: str) -> str | None:
  m = re.search(rf"(?m)^{re.escape(attr)} = ([^\r\n#]*?)[ \t]*(?:#.*)?\r?$", text)
  return None if m is None else f"{attr} = {m.group(1).strip()}"

def config_hunks(decisions: list) -> list:
  out = []
  
  for d in decisions:
    if d["action"] != D.CHANGE:
      continue
    p = R.get(d["key"])
    try:
      path, text = source_of(p.module)
    except Exception as e:
      out.append({"key": p.key, "error": f"The source of {p.module} could not be read ({type(e).__name__})."})
      continue
    find = _line_for(text, p.attr)
    if find is None or text.count(find) != 1:
      out.append({"key": p.key, "error": f"The line that sets {p.attr} was not found exactly once in {p.module}; change it by hand."})
      continue
    out.append({"key": p.key, "file": path.replace("\\", "/").split("/backend/", 1)[-1] if "/backend/" in path.replace("\\", "/") else path, "find": find,
      "replace": f"{p.attr} = {literal(p, d['proposed'])}"})
  return out

def version_hunk(current: int | None = None) -> dict:
  cur = C.EXTRACT_VERSION if current is None else current
  path, text = source_of(R.CONFIG_MODULE)
  find = f"EXTRACT_VERSION = {cur}"
  if text.count(find) != 1:
    return {"error": "EXTRACT_VERSION was not found exactly once; raise it by hand."}
  return {"file": "app/modules/drawings_boq/takeoff/extract/config.py", "find": find, "replace": f"EXTRACT_VERSION = {cur + 1}", "new_version": cur + 1}

def ledger_entries(decisions: list, sweep: dict, new_version: int, existing: list | None = None, date: str | None = None) -> list:
  rows = list(LG.load() if existing is None else existing)
  
  for d in decisions:
    if d["action"] != D.CHANGE:
      continue
    ev = d["evidence"]
    rows.append({"key": d["key"], "from": d["current"], "to": d["proposed"], "extract_version": new_version, "date": date,
      "evidence": {"affected_families": ev["affected_families"], "labels": ev["labels"], "complete_sheets": ev["complete_sheets"], "f1_before": ev["f1_now"],
        "f1_after": ev["chosen"]["f1"], "neighbours": ev["neighbours"], "cases": [c["name"] for c in sweep.get("cases", [])], "ladder": sweep.get("ladder"),
        "design": sweep.get("design"), "swept_at_extract_version": sweep.get("extract_version"), "decision_version": D.DECISION_VERSION,
        "kinds_moved_outside_the_rule": ev["kinds_moved_outside_the_rule"]}})
  return rows

def render(sweep: dict, decided: dict, joint: dict | None = None) -> str:
  ds, pol = decided["decisions"], decided["policy"]
  changes = [d for d in ds if d["action"] == D.CHANGE]
  L = ["# Calibration report", "",
    f"Swept at EXTRACT_VERSION {sweep.get('extract_version')} (code now {C.EXTRACT_VERSION}), ladder `{sweep.get('ladder')}`, one constant at a time"
    f"{' (stopped early: ' + str(sweep.get('stopped')) + ')' if sweep.get('partial') else ''}.", "",
    f"Rule: a value replaces the hand value only with a gain of {pol['min_gain']:g} F1 or more on the complete sheets, at least {pol['min_labels']} labelled members of the "
    f"kinds the constant is for, and no loss elsewhere (see tuning/decide.py). Constants that act together were not swept together.", ""]
  if sweep.get("extract_version") != C.EXTRACT_VERSION:
    L += [f"**The code has changed since this sweep (EXTRACT_VERSION {sweep.get('extract_version')} then, {C.EXTRACT_VERSION} now). Sweep again before applying.**", ""]
  L += ["## Cases", ""] + [f"- {c['name']} ({c['role']}): {c['sheets']} sheet(s), {c['labels']} label(s)" for c in sweep.get("cases", [])] + [""]
  L += ["## Result", "", "| Constant | Now | Decision | Proposed | Why |", "|---|---|---|---|---|"]
  
  for d in ds:
    L.append(f"| {d['key']} | {d['current']:g} | {d['action']} | {'' if d['proposed'] is None else format(d['proposed'], 'g')} | {d['reasons'][0] if d['reasons'] else ''} |")
  L.append("")
  if sweep.get("skipped"):
    L += ["## Not swept", ""] + [f"- {s['key']}: {s['reason']}" for s in sweep["skipped"]] + [""]
  if changes:
    L += ["## Changes", ""]
    if joint is not None:
      L += [f"Set together, the {len(changes)} changes {'hold' if joint['ok'] else 'do NOT hold'}: " + "; ".join(f"{g['name']} ({g['detail']})" for g in joint["guards"]), ""]
      if not joint["ok"]:
        L += ["Apply one change at a time (the one with the largest gain first) and run the scorecard after each.", ""]
    else:
      L += ["The changes were checked one at a time, not together. Run the scorecard after applying them; a regression there means take the smaller change back.", ""]
    hunks = config_hunks(ds)
    
    for h in hunks:
      if "error" in h:
        L += [f"### {h['key']}", "", h["error"], ""]
      else:
        L += [f"### {h['key']}", "", f"File `{h['file']}`. FIND (appears once):", "", f"```python\n{h['find']}\n```", "", "REPLACE WITH:", "", f"```python\n{h['replace']}\n```", ""]
    v = version_hunk()
    L += ["### EXTRACT_VERSION", "", "The reader's values change, so every stored read is stale:", ""]
    L += [f"FIND: `{v['find']}`  REPLACE WITH: `{v['replace']}`" if "error" not in v else v["error"], ""]
    new_version = v.get("new_version", C.EXTRACT_VERSION + 1)
    L += ["### ledger.json", "", "Replace `tuning/ledger.json` with:", "", "```json\n" + LG.dumps(ledger_entries(ds, sweep, new_version, date=None)).rstrip() + "\n```", ""]
  else:
    L += ["## Changes", "", "None. No hand value is replaced and EXTRACT_VERSION stays.", ""]
  return "\n".join(L) + "\n"
