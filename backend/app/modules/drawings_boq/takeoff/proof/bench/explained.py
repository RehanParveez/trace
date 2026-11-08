from __future__ import annotations
import os
from app.modules.drawings_boq.takeoff.proof.answers import answers as AN
from app.modules.drawings_boq.takeoff.ai_reader import cost as COST

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "explanations.yaml")
HOW_TO = ("Each entry is one difference between Trace and the QS file with the facts a model was shown (pack) and the cause it drafted (draft). Mark every draft: right: true when the cause is the real one, "
  "right: false when it is not; write what the real cause was in note when you know it. Nothing here changes a case file or a rule. The benchmark prints how many marked drafts were right.")

def load(path: str = PATH) -> dict:
  doc = AN.read_yaml(path) or {}
  doc.setdefault("entries", [])
  return doc

def save(doc: dict, path: str = PATH) -> None:
  AN.write_yaml(path, {"how_to": HOW_TO, "run": doc.get("run"), "made": doc.get("made"), "entries": doc["entries"]})

def hit_rate(doc: dict) -> dict:
  entries = doc.get("entries") or []
  drafted = [e for e in entries if e.get("draft")]
  right = sum(1 for e in drafted if e.get("right") is True)
  wrong = sum(1 for e in drafted if e.get("right") is False)
  named = [e for e in drafted if e["draft"].get("owner")]
  same = sum(1 for e in named if e["draft"]["owner"] == e.get("suggested_owner"))
  spent = COST.summarise([e["draft"] for e in drafted if e["draft"].get("model")])
  
  return {"differences": len(entries), "drafted": len(drafted), "right": right, "wrong": wrong, "waiting": len(drafted) - right - wrong,
    "failed_checks": sum(1 for e in drafted if e["draft"].get("checks_failed")), "owner_named": len(named), "owner_same_as_group": same,
    "hit_rate": None if not (right + wrong) else round(100.0 * right / (right + wrong), 1), "pkr": spent["pkr"], "usd": spent["usd"]}

def hit_line(doc: dict) -> str:
  h = hit_rate(doc)
  if not h["drafted"]:
    return "Difference explanations: none drafted yet (python -m app.modules.drawings_boq.takeoff.proof.explain collect, then propose)."
  rate = "not published until a draft is marked" if h["hit_rate"] is None else f"hit rate {h['hit_rate']}% ({h['right']} right of {h['right'] + h['wrong']} marked)"
  return (f"Difference explanations: {h['drafted']} drafted of {h['differences']}, {h['waiting']} not marked; {rate}; {h['failed_checks']} failed a check; "
    f"{h['owner_same_as_group']} of {h['owner_named']} named owners are the one the failure group suggests; cost {h['pkr']:.2f} PKR.")
