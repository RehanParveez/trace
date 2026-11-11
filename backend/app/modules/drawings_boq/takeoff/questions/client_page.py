from __future__ import annotations
from app.modules.drawings_boq.takeoff.questions import keys as QK

OPEN, ANSWERED = "OPEN", "ANSWERED"
KINDS = (QK.SITE, QK.CHOICE)
INTERNAL = ("choice.USE_QS_DEFAULTS",)

def _asked(view: dict, state: str) -> list:
  return [q for q in view.get("questions") or [] if q["kind"] in KINDS and q["key"] not in INTERNAL and q["state"] == state]

def _fallback(q: dict) -> str | None:
  d = q.get("default")
  if not d or d.get("value") in (None, ""):
    return None
  if d.get("range"):
    lo, hi = d["range"]
    unit = f" {q['unit']}" if q.get("unit") else ""
    return f"If you cannot say, the estimate shows {lo:g} to {hi:g}{unit} and says it is assumed."
  label = next((o["label"] for o in q.get("options") or [] if o["value"] == d["value"]), str(d["value"]))
  return f"If you cannot say, the estimate takes: {label}, and says it is assumed."

def _block(n: int, q: dict) -> list:
  out = [f"{n}. {q['prompt']}"]
  unit = f" (in {q['unit']})" if q.get("unit") else ""
  if q.get("options"):
    for o in q["options"]:
      out.append(f"   - {o['text'] or o['label']}")
  else:
    out.append(f"   Answer: a number{unit}.")
  fb = _fallback(q)
  if fb:
    out.append(f"   {fb}")
  if q.get("blocks"):
    out.append(f"   It affects {len(q['blocks'])} line(s) of the estimate.")
  return out

def render(view: dict, project: str | None = None, today: str | None = None) -> str:
  site = [q for q in _asked(view, OPEN) if q["kind"] == QK.SITE]
  choices = [q for q in _asked(view, OPEN) if q["kind"] == QK.CHOICE]
  done = _asked(view, ANSWERED)
  head = ["# Questions for the client", ""]
  if project or today:
    head += [" - ".join(x for x in (project, today) if x), ""]
  if not (site or choices):
    return "\n".join(head + ["Nothing is open. Every site question and project choice that this estimate waits on has an answer.", ""] + _answered(done))
  out = head + ["The drawings do not give these. Each answer changes the estimate, and until it is answered the lines that depend on it are marked as waiting.", ""]
  n = 0
  if site:
    out += ["## About the site", ""]
    for q in site:
      n += 1
      out += _block(n, q) + [""]
  if choices:
    out += ["## Choices for this project", ""]
    for q in choices:
      n += 1
      out += _block(n, q) + [""]
  return "\n".join(out + _answered(done))

def _answered(done: list) -> list:
  if not done:
    return []
  return ["## Already answered", ""] + [f"- {q['prompt']} Answer: {(q.get('answer') or {}).get('value')}" for q in done] + [""]
