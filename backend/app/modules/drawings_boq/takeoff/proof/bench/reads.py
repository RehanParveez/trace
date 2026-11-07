from __future__ import annotations
import hashlib
import json
import os
from app.modules.drawings_boq.takeoff.run import reading_adapter as AD
from app.modules.drawings_boq.takeoff.run import completeness as RC

def cache_key(case: dict, with_overrides: bool) -> str:
  shas = [str((case.get("sha256") or {}).get(n) or n) for n in case["pdfs"]]
  return hashlib.sha256((",".join(shas) + ("|proof" if with_overrides else "|product")).encode("utf-8")).hexdigest()[:24]

def plain_of(case: dict, found: dict, with_overrides: bool, cache_dir: str | None = None) -> dict:
  path = os.path.join(cache_dir, cache_key(case, with_overrides) + ".json") if cache_dir else None
  if path and os.path.isfile(path):
    with open(path, encoding="utf-8") as fh:
      return json.load(fh)
  rows = AD.read_case({**case, "overrides": case.get("overrides") if with_overrides else None}, found)
  plain = RC.merge([RC.plain_read(AD.items_of(rows[n])) for n in case["pdfs"]])
  if path:
    os.makedirs(cache_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
      json.dump(plain, fh, sort_keys=True)
  return plain

def both(case: dict, found: dict, cache_dir: str | None = None) -> tuple:
  proof = plain_of(case, found, True, cache_dir)
  product = plain_of(case, found, False, cache_dir) if case.get("overrides") else proof
  return product, proof
