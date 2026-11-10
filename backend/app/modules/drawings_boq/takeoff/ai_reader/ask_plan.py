from __future__ import annotations
import json
import os
from app.engine.catalogue import note_keys as NK

FILE = "ai_plan.json"

def path_of(folder: str) -> str:
  return os.path.join(folder, FILE)

def write(folder: str, plan: dict) -> str:
  target = path_of(folder)
  with open(target, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(plan, fh, indent=1, sort_keys=True)
    fh.write("\n")
  return target

def load(folder: str) -> dict | None:
  target = path_of(folder)
  if not os.path.isfile(target):
    return None
  with open(target, encoding="utf-8") as fh:
    return json.load(fh)

def usable(plan: dict | None) -> tuple:
  if plan is None:
    return False, "no ai_plan.json: run `proof.ai_plan --write` first; a missing-only run never asks a whole set"
  if plan.get("keys_state") != NK.state():
    return False, f"the plan was made for note keys {plan.get('keys_state')} and note_keys.yaml is {NK.state()}: plan again"
  return True, ""

def spec_of(pages: list) -> str:
  return ",".join(str(p) for p in pages)
