from __future__ import annotations
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
  "SHEET": Task("SHEET", TITLE_BLOCK, AIRequestPurpose.SHEET_CLASSIFICATION, C.PROMPT_NAME, C.PROMPT_NAME, ("quote_printed",)),
  "NOTE_FACT": Task("NOTE_FACT", BOX, AIRequestPurpose.NOTE_FACT, None, None, ()),
  "SCHEDULE_ROW": Task("SCHEDULE_ROW", BOX, AIRequestPurpose.SCHEDULE_ROW, None, None, ()),
  "LEGEND_ENTRY": Task("LEGEND_ENTRY", BOX, AIRequestPurpose.LEGEND_ENTRY, None, None, ()),
  "VOCAB": Task("VOCAB", TEXT, AIRequestPurpose.VOCAB, "vocab.v1", "vocab.v1", ("choice_offered",)),
  "EXPLAIN": Task("EXPLAIN", PAGE, AIRequestPurpose.EXPLAIN, None, None, ()),
}

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
