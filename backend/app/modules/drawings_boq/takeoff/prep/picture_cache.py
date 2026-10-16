from __future__ import annotations
import hashlib
import json
import os
import tempfile

READER_VERSION = "1"
MAX_FILES = 400

def _dir() -> str | None:
  if (os.environ.get("TRACE_PICTURE_CACHE") or "").lower() in ("off", "0", "false", "no"):
    return None
  return os.environ.get("TRACE_PICTURE_CACHE_DIR") or os.path.join(tempfile.gettempdir(), "trace_picture_cache")

def key_of(kind: str, img) -> str:
  h = hashlib.sha256()
  h.update(f"{READER_VERSION}|{kind}|{img.size[0]}x{img.size[1]}|{img.mode}|".encode())
  h.update(img.tobytes())
  return h.hexdigest()

def get(key: str):
  d = _dir()
  if d is None:
    return None
  try:
    with open(os.path.join(d, key + ".json"), "r", encoding="utf-8") as fh:
      return json.load(fh)
  except (OSError, ValueError):
    return None

def put(key: str, value) -> None:
  d = _dir()
  if d is None:
    return
  try:
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
      json.dump(value, fh)
    os.replace(tmp, os.path.join(d, key + ".json"))
    _prune(d)
  except (OSError, TypeError, ValueError):
    return

def _prune(d: str) -> None:
  try:
    files = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".json")]
    if len(files) <= MAX_FILES:
      return
    files.sort(key=lambda p: os.path.getmtime(p))
    for p in files[: len(files) - MAX_FILES]:
      os.remove(p)
  except OSError:
    return
