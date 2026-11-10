from __future__ import annotations
import json
from dataclasses import dataclass
from app.core.config import settings
from app.modules.ai_requests.models import AIRequestPurpose
from app.modules.drawings_boq.takeoff.ai_reader import contract as C
from app.modules.drawings_boq.takeoff.ai_reader import prompts as P

TITLE_BLOCK, PAGE, BOX, TEXT = "TITLE_BLOCK", "PAGE", "BOX", "TEXT"
REGIONS = (TITLE_BLOCK, PAGE, BOX, TEXT)

@dataclass(frozen=True)
class Task:
  name: str
  region: str
  purpose: AIRequestPurpose
  prompt: str | None
  schema: str | None
  validators: tuple

TASKS = {
  "SHEET": Task("SHEET", TITLE_BLOCK, AIRequestPurpose.SHEET_CLASSIFICATION, C.PROMPT_NAME, C.PROMPT_NAME, ("quote_printed", "value_in_quote", "scale_parses", "choice_offered", "box_on_page")),
  "NOTE_FACT": Task("NOTE_FACT", BOX, AIRequestPurpose.NOTE_FACT, "note.v1", "note.v1", ("quote_supported", "number_printed", "unit_parses", "value_in_range", "choice_offered")),
  "SCHEDULE_ROW": Task("SCHEDULE_ROW", BOX, AIRequestPurpose.SCHEDULE_ROW, "schedule.v1", "schedule.v1", ("quote_supported", "fields_given", "cells_in_quote", "mark_in_vocab", "floor_known", "size_parses", "size_in_range")),
  "LEGEND_ENTRY": Task("LEGEND_ENTRY", BOX, AIRequestPurpose.LEGEND_ENTRY, "legend.v1", "legend.v1", ("quote_printed", "choice_offered", "meaning_given", "symbol_present", "meaning_not_contradicted")),
  "VOCAB": Task("VOCAB", TEXT, AIRequestPurpose.VOCAB, "vocab.v1", "vocab.v1", ("choice_offered",)),
  "FIND": Task("FIND", PAGE, AIRequestPurpose.REGION_FIND, "find.v1", "find.v1", ("box_on_page", "choice_offered")),
  "EXPLAIN": Task("EXPLAIN", TEXT, AIRequestPurpose.EXPLAIN, "explain.v1", "explain.v1", ("cause_given", "cause_short", "evidence_exists", "evidence_named", "choice_offered", "numbers_in_facts")),
}

CHEAP, STRONG = "cheap", "strong"
TIERS = {CHEAP: "ai_model", STRONG: "ai_model_strong"}
ROUTES = {
  "SCHEDULE_ROW": {"scales": (1.0, 1.6), "escalate": True, "support": True},
  "NOTE_FACT": {"scales": (1.0, 1.6), "escalate": True, "support": True},
  "FIND": {"scales": (1.0,), "escalate": False, "support": False},
}

def route(name: str) -> dict:
  if name not in ROUTES:
    raise KeyError(f"There is no route for AI task {name}.")
  return ROUTES[name]

def route_problems() -> list:
  out = []
  
  for name, r in ROUTES.items():
    if name not in TASKS:
      out.append(f"{name}: a route for a task that does not exist")
    scales = r.get("scales") or ()
    if not scales or any(not isinstance(s, (int, float)) or isinstance(s, bool) or s <= 0 for s in scales):
      out.append(f"{name}: scales must be numbers above zero")
    if r.get("escalate") and len(scales) < 2:
      out.append(f"{name}: a task that escalates needs two readings to disagree")
  return out

def model_of(tier: str) -> str | None:
  if tier == CHEAP:
    return None
  return str(getattr(settings, TIERS[tier], "") or "") or None

def get(name: str) -> Task:
  if name not in TASKS:
    raise KeyError(f"There is no AI task {name}.")
  return TASKS[name]

def switched_on() -> set:
  names = {s.strip().upper() for s in (settings.ai_tasks_enabled or "").split(",") if s.strip()}
  return {n for n in names if n in TASKS and TASKS[n].prompt}

def is_on(name: str) -> bool:
  return name in switched_on()

def prompt_version(task: Task) -> str:
  return P.load(task.prompt)["version"]

def prompt_name(name: str) -> str:
  chosen = json.loads(settings.ai_prompt_names or "{}").get(name)
  if chosen is None:
    return get(name).prompt
  if chosen not in P.names() or P.load(chosen)["task"] != name:
    raise KeyError(f"{chosen} is not a prompt file of the task {name}.")
  return str(chosen)
