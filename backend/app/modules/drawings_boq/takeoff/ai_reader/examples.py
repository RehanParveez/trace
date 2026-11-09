from __future__ import annotations
import hashlib
import json
import os
import re
from dataclasses import dataclass

TASKS = ("SCHEDULE_ROW", "NOTE_FACT")
MAX_EXAMPLES = 3
MAX_WORDS = 80
STATE_LEN = 8
FOLDER = "ai_examples"
SUFFIX = ".json"
LEAVE_OUT = "-loo"
WORD = re.compile(r"[A-Za-z0-9#@/.\"'+-]{2,}")

@dataclass(frozen=True)
class Example:
  task: str
  office: str | None
  kind: str | None
  crop_ref: dict
  words: tuple
  answer: dict
  checked_by: str
  date: str
  drawing: str
  shared: bool = False

  @property
  def id(self) -> str:
    body = json.dumps([self.task, self.office, self.kind, self.crop_ref, list(self.words), self.answer, self.drawing], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]

  def to_json(self) -> dict:
    return {"id": self.id, "task": self.task, "office": self.office, "kind": self.kind, "crop_ref": self.crop_ref, "words": list(self.words), "answer": self.answer,
      "checked_by": self.checked_by, "date": self.date, "drawing": self.drawing, "shared": self.shared}

class ExampleError(ValueError):
  pass

def words_of(text) -> tuple:
  seen: dict = {}
  for w in WORD.findall(str(text or "").upper()):
    seen.setdefault(w, None)
  return tuple(list(seen)[:MAX_WORDS])

def make(*, task: str, office, kind, crop_ref: dict, text, answer: dict, checked_by: str, date: str, drawing: str, shared: bool = False) -> Example:
  if task not in TASKS:
    raise ExampleError(f"{task} takes no examples; only {', '.join(TASKS)} do.")
  if not str(checked_by or "").strip() or not str(date or "").strip():
    raise ExampleError("An example is a checked answer: it needs checked_by and a date.")
  if not isinstance(answer, dict) or not answer:
    raise ExampleError("An example needs the answer.")
  if not str(drawing or "").strip():
    raise ExampleError("An example names the drawing it comes from, so that it is never given for that drawing.")
  return Example(task=task, office=(str(office) if office else None), kind=(str(kind) if kind else None), crop_ref=dict(crop_ref or {}), words=words_of(text),
    answer=answer, checked_by=str(checked_by).strip(), date=str(date).strip(), drawing=str(drawing), shared=bool(shared))

def from_json(data: dict) -> Example:
  return Example(task=data["task"], office=data.get("office"), kind=data.get("kind"), crop_ref=dict(data.get("crop_ref") or {}), words=tuple(data.get("words") or ()),
    answer=data["answer"], checked_by=data["checked_by"], date=data["date"], drawing=data["drawing"], shared=bool(data.get("shared")))

def pick(bank: list, *, task: str, office=None, kind=None, words=(), drawing: str, leave_out_office: bool = False, k: int = MAX_EXAMPLES) -> list:
  have = {str(w).upper() for w in words}
  rows = []
  for e in bank:
    if e.task != task or e.drawing == str(drawing):
      continue
    if leave_out_office and office and e.office == office:
      continue
    rows.append((0 if office and e.office == office else 1, 0 if kind and e.kind == kind else 1, -len(have.intersection(e.words)), e.id, e))
  rows.sort(key=lambda r: r[:4])
  return [r[4] for r in rows[:k]]

def state(examples: list, leave_out_office: bool = False) -> str:
  if not examples:
    return ""
  body = ",".join(sorted(e.id for e in examples))
  return hashlib.sha256(body.encode("utf-8")).hexdigest()[:STATE_LEN] + (LEAVE_OUT if leave_out_office else "")

def prompt_version(version: str, examples: list, leave_out_office: bool = False) -> str:
  s = state(examples, leave_out_office).replace(LEAVE_OUT, "")
  return f"{version}+{s}" if s else str(version)

def variant(version: str, examples: list, leave_out_office: bool = False) -> str:
  if not examples:
    return str(version)
  return f"{version}+ex" + (LEAVE_OUT if leave_out_office else "")

def record(version: str, examples: list, leave_out_office: bool = False) -> dict:
  return {"variant": variant(version, examples, leave_out_office), "version": str(version), "ids": [e.id for e in examples], "state": state(examples, leave_out_office), "leave_out_office": bool(leave_out_office and examples)}

def render(examples: list) -> str:
  if not examples:
    return ""
  lines = ["Here are answers a person has checked, for other pictures from other drawings. They show the shape of a good answer and how the words are copied; the picture you are given is a different one, so give only what it prints.", ""]
  for n, e in enumerate(examples, 1):
    lines.append(f"Example {n}. Words printed in its picture: {' '.join(e.words[:MAX_WORDS])}")
    lines.append(f"Checked answer: {json.dumps(e.answer, ensure_ascii=False, separators=(',', ':'))}")
    lines.append("")
  return "\n".join(lines).rstrip() + "\n"

def kind_hint(task: str, words) -> str | None:
  if task != "SCHEDULE_ROW":
    return None
  from app.engine.catalogue import schedule_kinds as SK
  have = {str(w).upper().strip(".:") for w in words}
  fit = [e["key"] for e in SK.kinds() if all(part in have for part in e["key"].split("_"))]
  return fit[0] if len(fit) == 1 else None

def page_words(contents: bytes, page: int) -> tuple:
  from app.modules.drawings_boq.takeoff.ai_reader import regions as R
  page_pt = R.page_picture(contents, page, 64)[1]["page_pt"]
  return words_of(R.page_text(contents, page, page_pt))

def for_page(*, bank: list, task: str, name: str | None, contents: bytes, page: int, office, drawing: str, leave_out_office: bool = False) -> list:
  if not bank or task not in TASKS:
    return []
  from app.modules.drawings_boq.takeoff.ai_reader import prompts as P, tasks as T
  if "{examples}" not in P.load(name or T.prompt_name(task))["text"]:
    return []
  words = page_words(contents, page)
  return pick(bank, task=task, office=office, kind=kind_hint(task, words), words=words, drawing=drawing, leave_out_office=leave_out_office)

def folder(case_dir: str) -> str:
  return os.path.join(case_dir, FOLDER)

def save(case_dir: str, example: Example) -> str:
  target = os.path.join(folder(case_dir), example.id + SUFFIX)
  os.makedirs(os.path.dirname(target), exist_ok=True)
  with open(target, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(example.to_json(), fh, indent=2, sort_keys=True, ensure_ascii=False)
    fh.write("\n")
  return target

def load_folder(case_dir: str) -> list:
  where = folder(case_dir)
  if not os.path.isdir(where):
    return []
  out = []
  for name in sorted(os.listdir(where)):
    if name.endswith(SUFFIX):
      with open(os.path.join(where, name), encoding="utf-8") as fh:
        out.append(from_json(json.load(fh)))
  return out

def load_root(root: str) -> list:
  if not os.path.isdir(root):
    return []
  return load_all(root, sorted(n for n in os.listdir(root) if os.path.isdir(os.path.join(root, n))))

def load_all(root: str, cases: list) -> list:
  out: list = []
  for name in cases:
    out.extend(load_folder(os.path.join(root, name)))
  return out

def from_review(*, task: str, office, kind, crop_ref: dict, text, row: dict, corrected: dict | None, checked_by: str, date: str, drawing: str, shared: bool) -> Example:
  return make(task=task, office=office, kind=kind, crop_ref=crop_ref, text=text, answer=corrected or row, checked_by=checked_by, date=date, drawing=drawing, shared=shared)
