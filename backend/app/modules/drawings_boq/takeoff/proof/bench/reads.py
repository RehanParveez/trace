from __future__ import annotations
import hashlib
import json
import os
import pickle
from app.modules.drawings_boq.takeoff.run import reading_adapter as AD
from app.modules.drawings_boq.takeoff.run import completeness as RC
from app.modules.drawings_boq.takeoff.run import engine_lines as EL

def cache_key(case: dict, with_overrides: bool) -> str:
  shas = [str((case.get("sha256") or {}).get(n) or n) for n in case["pdfs"]]
  return hashlib.sha256((",".join(shas) + ("|proof" if with_overrides else "|product")).encode("utf-8")).hexdigest()[:24]

def plain_of(case: dict, found: dict, with_overrides: bool, cache_dir: str | None = None) -> dict:
  path = os.path.join(cache_dir, cache_key(case, with_overrides) + ".json") if cache_dir else None
  if path and os.path.isfile(path):
    with open(path, encoding="utf-8") as fh:
      return json.load(fh)
  rows = dict(read_rows(case, found, with_overrides, cache_dir))
  plain = RC.merge([RC.plain_read(AD.items_of(rows[n])) for n in case["pdfs"]])
  if path:
    os.makedirs(cache_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
      json.dump(plain, fh, sort_keys=True)
  return plain


def rules_key(rules: list | None) -> str:
  return hashlib.sha256(json.dumps([[r["key"], r.get("scope") or {}, r["value"]] for r in rules or []], sort_keys=True).encode("utf-8")).hexdigest()[:12]

def read_rows(case: dict, found: dict, with_overrides: bool, cache_dir: str | None = None) -> list:
  path = os.path.join(cache_dir, cache_key(case, with_overrides) + ".rows.pkl") if cache_dir else None
  if path and os.path.isfile(path):
    with open(path, "rb") as fh:
      return pickle.load(fh)
    
  rows = AD.read_case({**case, "overrides": case.get("overrides") if with_overrides else None}, found)
  held = [(n, rows[n]) for n in case["pdfs"]]
  if path:
    os.makedirs(cache_dir, exist_ok=True)
    with open(path, "wb") as fh:
      pickle.dump(held, fh)
  return held

def product_rows(case: dict, found: dict, cache_dir: str | None = None) -> list:
  return read_rows(case, found, False, cache_dir)

def product_lines(case: dict, found: dict, cache_dir: str | None = None, rules: list | None = None) -> list:
  path = os.path.join(cache_dir, cache_key(case, False) + (f".{rules_key(rules)}" if rules else "") + ".lines.json") if cache_dir else None
  if path and os.path.isfile(path):
    with open(path, encoding="utf-8") as fh:
      return json.load(fh)
  lines = EL.lines_of_reads(product_rows(case, found, cache_dir), rules=rules)["lines"]
  if path:
    os.makedirs(cache_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
      json.dump(lines, fh, sort_keys=True)
  return lines

def proof_lines(case: dict, found: dict, cache_dir: str | None = None, rules: list | None = None) -> list:
  path = os.path.join(cache_dir, cache_key(case, True) + (f".{rules_key(rules)}" if rules else "") + ".lines.json") if cache_dir else None
  if path and os.path.isfile(path):
    with open(path, encoding="utf-8") as fh:
      return json.load(fh)
  lines = EL.lines_of_reads(read_rows(case, found, True, cache_dir), rules=rules)["lines"]
  if path:
    os.makedirs(cache_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
      json.dump(lines, fh, sort_keys=True)
  return lines

def both(case: dict, found: dict, cache_dir: str | None = None) -> tuple:
  proof = plain_of(case, found, True, cache_dir)
  product = plain_of(case, found, False, cache_dir) if case.get("overrides") else proof
  return product, proof
