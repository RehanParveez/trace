from __future__ import annotations
import hashlib
import json
import os

FOLDER = "ai_cache"
SUFFIX = ".json"

def pdf_sha256(contents: bytes) -> str:
  return hashlib.sha256(contents).hexdigest()

def key(pdf_sha: str, page: int, region: dict, task: str, prompt_version: str, model: str) -> str:
  body = json.dumps([str(pdf_sha), int(page), region, str(task), str(prompt_version), str(model)], sort_keys=True, separators=(",", ":"))
  return hashlib.sha256(body.encode("utf-8")).hexdigest()

def folder(case_dir: str) -> str:
  return os.path.join(case_dir, FOLDER)

def path(case_dir: str, cache_key: str) -> str:
  return os.path.join(folder(case_dir), cache_key + SUFFIX)

def write(case_dir: str, entry: dict) -> str:
  target = path(case_dir, entry["cache_key"])
  os.makedirs(os.path.dirname(target), exist_ok=True)
  with open(target, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(entry, fh, indent=2, sort_keys=True, ensure_ascii=False)
    fh.write("\n")
  return target

def read(case_dir: str, cache_key: str) -> dict | None:
  target = path(case_dir, cache_key)
  if not os.path.isfile(target):
    return None
  with open(target, encoding="utf-8") as fh:
    return json.load(fh)

def read_all(case_dir: str) -> list:
  where = folder(case_dir)
  if not os.path.isdir(where):
    return []
  out = []
  for name in sorted(os.listdir(where)):
    if name.endswith(SUFFIX):
      with open(os.path.join(where, name), encoding="utf-8") as fh:
        out.append(json.load(fh))
  return out
