from __future__ import annotations
from app.modules.drawings_boq.takeoff.completeness import ledger as LG
from app.modules.drawings_boq.takeoff.questions import engine as QE
from app.modules.drawings_boq.takeoff.completeness import facts as F

TOP = 5

def build(state: dict, run: dict) -> dict:
  facts = state.get("facts")
  summary = LG.summary(state["ledger"])
  boq = state.get("boq") or {"rows": [], "totals": {}, "money": None, "rates_loaded": False}
  open_q = [q for q in state.get("questions") or [] if q["state"] == QE.OPEN]
  
  return {"project": F.values(facts) if facts else None, "scope": F.scope_of(facts) if facts else None, "sets_found": list((F.values(facts)["sets_present"] if facts else []) or []),
    "items": summary["by_state"], "entries": summary["entries"], "by_reason": summary["by_reason"],
    "boq": {"lines": len(boq["rows"]), "totals": boq["totals"], "money": boq["money"], "rates_loaded": boq["rates_loaded"]},
    "questions": {"open": len(open_q), "top": [{"key": q["key"], "kind": q["kind"], "prompt": q["prompt"], "blocks": q["blocks"]} for q in open_q[:TOP]]},
    "stages": [{"name": s["name"], "status": s["status"], "seconds": s["seconds"], "error": s["error"]} for s in run["stages"]],
    "failed": list(run["failed"]), "unread": list(state.get("unread") or []), "seconds": run["seconds"]}

def render(rep: dict, name: str = "") -> str:
  p = rep["project"] or {}
  head = f"{name}: " if name else ""
  
  lines = [f"{head}type {p.get('type')}, structure {p.get('structure')}, floors {','.join(p.get('floors') or []) or '-'}, sets {','.join(rep['sets_found']) or '-'}, scope {rep['scope']}",
    "  items: " + ", ".join(f"{n} {s}" for s, n in rep["items"].items()),
    f"  BOQ draft: {rep['boq']['lines']} lines" + ("; " + "; ".join(f"{u} {t['MEASURED']:g} measured, {t['ASSUMED']:g} assumed" for u, t in sorted(rep["boq"]["totals"].items())) if rep["boq"]["totals"] else "") + ("" if rep["boq"]["rates_loaded"] else " (no rate book loaded: quantities only)"),
    f"  questions open: {rep['questions']['open']}" + (" (" + "; ".join(q["key"] for q in rep["questions"]["top"]) + ")" if rep["questions"]["top"] else ""),
    "  stages: " + ", ".join(f"{s['name']} {s['seconds']:.1f}s{'' if s['status'] == 'DONE' else ' ' + s['status']}" for s in rep["stages"]) + f"; total {rep['seconds']:.1f}s"]
  if rep.get("unread"):
    lines.append("  NOT READ: " + "; ".join(f"{u['file']} ({u['error']})" for u in rep["unread"]))
  if rep["failed"]:
    lines.append("  FAILED: " + ", ".join(rep["failed"]) + "; the items they feed are NOT_READ")
  return "\n".join(lines)
