"""The register of offices and of how each new set entered the benchmark: which firm texts belong to which office letter, who confirmed each office, which sets entered as first sight and when they moved to test or dev, with the checks that keep the register and sets.yaml in step and refuse a move back to first sight."""
from __future__ import annotations
import csv
import os
import re
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "offices.yaml")
SETS_PATH = os.path.join(HERE, "sets.yaml")
HISTORY_PATH = os.path.join(HERE, "history.csv")
FIRST_SIGHT, TEST, DEV = "FIRST_SIGHT", "TEST", "DEV"
LABELS = (FIRST_SIGHT, TEST, DEV)
LEAVES = (TEST, DEV)
FIRST_RUN = "PRODUCT"

def load(path: str = PATH) -> dict:
  """Reads the register of offices, with its settings, its offices and its log of set moves."""
  with open(path, encoding="utf-8") as fh:
    doc = yaml.safe_load(fh) or {}
  doc.setdefault("settings", {})
  doc.setdefault("offices", {})
  doc["set_log"] = doc.get("set_log") or {}
  return doc

def save(doc: dict, path: str = PATH) -> None:
  """Writes the register of offices."""
  with open(path, "w", encoding="utf-8", newline="\n") as fh:
    yaml.safe_dump({"settings": doc["settings"], "offices": doc["offices"], "set_log": doc["set_log"]}, fh, sort_keys=False, allow_unicode=True, width=200)

def norm(text) -> str:
  """Reduces a firm text to lower-case words with the punctuation removed, so two spellings of the same name compare equal."""
  return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(text or "").lower(), flags=re.U)).strip()

def office_for_firm(doc: dict, text) -> str | None:
  """Returns the office whose recorded firm text equals the given text or is contained in it (or contains it), once both are at least the minimum length; None when no office has such a firm."""
  want, least = norm(text), int(doc["settings"].get("min_match_chars") or 1)
  if len(want) < least:
    return None
  for letter, row in sorted(doc["offices"].items()):
    for firm in row.get("firms") or []:
      have = norm(firm)
      if len(have) >= least and (have == want or have in want or want in have):
        return letter
  return None

def next_letter(doc: dict) -> str:
  """Gives the letter after the highest one used, which is the letter a new firm's office takes."""
  used = [k for k in doc["offices"] if len(k) == 1]
  if not used:
    return "A"
  if max(used) >= "Z":
    raise ValueError("The letters A to Z are all used.")
  return chr(ord(max(used)) + 1)

def read_sets(path: str = SETS_PATH) -> dict:
  """Reads sets.yaml."""
  with open(path, encoding="utf-8") as fh:
    return yaml.safe_load(fh) or {}

def flow(value) -> str:
  """Writes a value in the one-line style sets.yaml uses for each set."""
  if isinstance(value, dict):
    return "{" + ", ".join(f"{k}: {flow(v)}" for k, v in value.items()) + "}"
  if isinstance(value, bool):
    return "true" if value else "false"
  return str(value)

def write_set_row(name: str, row: dict, path: str = SETS_PATH) -> str:
  """Puts one set's row into sets.yaml in place, or at the end of the sets when it is new, and keeps every other line as it was; gives 'added' or 'changed'."""
  with open(path, encoding="utf-8", newline="") as fh:
    text = fh.read()
  nl = "\r\n" if "\r\n" in text else "\n"
  lines = text.split(nl)
  new = f"  {name}: {flow(row)}"
  for n, ln in enumerate(lines):
    if re.match(rf"^  {re.escape(name)}:\s", ln):
      lines[n] = new
      out = "changed"
      break
  else:
    last = max(n for n, ln in enumerate(lines) if re.match(r"^  \S+: \{", ln))
    lines.insert(last + 1, new)
    out = "added"
  with open(path, "w", encoding="utf-8", newline="") as fh:
    fh.write(nl.join(lines))
  return out

def split_label(row: dict, group: str) -> str | None:
  """Returns the split a set's own row gives a section group, or None when the row gives none and the office decides."""
  return ((row or {}).get("split") or {}).get(group)

def history_rows(path: str = HISTORY_PATH) -> list:
  """Reads the benchmark's history file, or an empty list when it has none."""
  if not os.path.isfile(path):
    return []
  with open(path, encoding="utf-8", newline="") as fh:
    return list(csv.DictReader(fh))

def first_score(name: str, rows: list) -> dict | None:
  """Returns the earliest history line of the first (product) run of a set, which is its score before anyone looked at it, or None when the benchmark has not scored it."""
  mine = [r for r in rows if r["set"] == name and r["run"] == FIRST_RUN]
  return mine[0] if mine else None

def problems(sets_doc: dict | None = None, doc: dict | None = None, groups: list | None = None) -> list:
  """Returns a message for each fault: a set whose office the register does not have, an office nobody confirmed, a firm text two offices share, a split label that is not one of the three, a set's split that differs from the last line of its log, or a log that goes back to first sight after leaving it."""
  sets_doc = sets_doc if sets_doc is not None else read_sets()
  doc = doc or load()
  groups = groups if groups is not None else list((sets_doc.get("section_groups") or {}).keys())
  out, seen = [], {}
  for letter, row in sorted(doc["offices"].items()):
    if not row.get("confirmed_by"):
      out.append(f"office {letter} has no confirmed_by in offices.yaml")
    for firm in row.get("firms") or []:
      if norm(firm) in seen and seen[norm(firm)] != letter:
        out.append(f"the firm {firm!r} is under offices {seen[norm(firm)]} and {letter}")
      seen[norm(firm)] = letter
  for name, row in sorted((sets_doc.get("sets") or {}).items()):
    if row.get("office") not in doc["offices"]:
      out.append(f"{name}: office {row.get('office')} is not in offices.yaml")
    log = doc["set_log"].get(name) or []
    for group in sorted((row.get("split") or {})):
      label = split_label(row, group)
      if group not in groups:
        out.append(f"{name}: split names {group}, which is not a section group")
      if label not in LABELS:
        out.append(f"{name}: split {label!r} for {group} is not one of {', '.join(LABELS)}")
      mine = [e for e in log if e["group"] == group]
      if not mine:
        out.append(f"{name}: split for {group} has no entry in the set_log of offices.yaml")
      elif mine[-1]["split"] != label:
        out.append(f"{name}: split for {group} is {label} and the last log entry says {mine[-1]['split']}")
    for group in groups:
      left = False
      for e in [e for e in log if e["group"] == group]:
        if e["split"] == FIRST_SIGHT and left:
          out.append(f"{name}: {group} went back to first sight after it left; a set never returns to first sight")
        left = left or e["split"] in LEAVES
  for name in sorted(set(doc["set_log"]) - set(sets_doc.get("sets") or {})):
    out.append(f"offices.yaml logs {name}, which is not in sets.yaml")
  return out
