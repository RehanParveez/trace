from __future__ import annotations
import os
from collections import OrderedDict
import threading
import tempfile
from app.shared.storage import download_to_path

MAX_FILES = 3
MAX_BYTES = 96 * 1024 * 1024
_FILES: "OrderedDict[str, bytes]" = OrderedDict()
_LOCK = threading.Lock()

def drawing_bytes(storage_key: str) -> bytes:
  with _LOCK:
    if storage_key in _FILES:
      _FILES.move_to_end(storage_key)
      return _FILES[storage_key]

  with tempfile.TemporaryDirectory() as tmp:
    path = os.path.join(tmp, "drawing.pdf")
    download_to_path(storage_key, path)
    with open(path, "rb") as handle:
      contents = handle.read()

  with _LOCK:
    _FILES[storage_key] = contents
    _FILES.move_to_end(storage_key)
    while len(_FILES) > MAX_FILES or (len(_FILES) > 1 and sum(len(v) for v in _FILES.values()) > MAX_BYTES):
      _FILES.popitem(last=False)
  return contents
