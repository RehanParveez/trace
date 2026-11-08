from __future__ import annotations
import os
import yaml
import re
import functools
from app.engine.catalogue import loader as CL

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vocabulary.yaml")
FIELDS = ("text", "item", "confirmed_by", "date")
MAX_TEXT = 80

class VocabularyError(Exception):
  """Raised when the vocabulary file is wrong or missing."""

def norm(raw) -> str:
  t = re.sub(r"[\"'`]", "", str(raw or "").lower())
  t = re.sub(r"[^a-z0-9:;/.+-]+", " ", t)
  return re.sub(r"\s+", " ", t).strip()

@functools.lru_cache(maxsize=1)
def _raw() -> dict:
  with open(PATH, encoding="utf-8") as fh:
    data = yaml.safe_load(fh)
  if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
    raise VocabularyError("vocabulary.yaml must hold a list of entries")
  return data

def reload() -> None:
  _raw.cache_clear()
  _by_key.cache_clear()

def problems(data: dict | None = None) -> list:
  data = data or _raw()
  have = {i.id for i in CL.items()}
  out, seen = [], set()
  
  for n, e in enumerate(data["entries"], 1):
    name = e.get("text", f"entry {n}")
    out += [f"{name}: no {f}" for f in FIELDS if not e.get(f)]
    key = norm(e.get("text"))
    out += [f"{name}: holds no word"] if not re.search(r"[a-z]{2}", key) else []
    out += [f"{name}: is longer than {MAX_TEXT} characters"] if len(str(e.get("text") or "")) > MAX_TEXT else []
    out += [f"{name}: written twice"] if key in seen else []
    seen.add(key)
    out += [f"{name}: {e.get('item')} is not a catalogue item"] if e.get("item") and e["item"] not in have else []
  return out

def entries() -> tuple:
  bad = problems()
  if bad:
    raise VocabularyError("; ".join(bad[:5]))
  return tuple(_raw()["entries"])

@functools.lru_cache(maxsize=1)
def _by_key() -> dict:
  return {norm(e["text"]): e for e in entries()}

def lookup(text) -> dict | None:
  return _by_key().get(norm(text)) if _raw()["entries"] else None

def item_for(text) -> str | None:
  hit = lookup(text)
  return hit["item"] if hit else None

def save(data: dict) -> None:
  bad = problems(data)
  if bad:
    raise VocabularyError("; ".join(bad[:5]))
  rows = sorted(({k: str(e[k]) for k in FIELDS} for e in data["entries"]), key=lambda e: norm(e["text"]))
  with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    yaml.safe_dump({"entries": rows}, fh, sort_keys=False, allow_unicode=True, width=1000, default_flow_style=False)
  reload()
