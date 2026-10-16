from __future__ import annotations
import functools
import shutil
import subprocess

@functools.lru_cache(maxsize=1)
def status() -> dict:
  """{"installed": bool, "version": str | None, "packages": bool, "usable": bool}."""
  path = shutil.which("tesseract")
  version = None
  if path:
    try:
      out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10)
      first = ((out.stdout or "") + (out.stderr or "")).strip().splitlines()
      version = first[0].replace("tesseract", "").strip() if first else None
    except Exception:
      version = None
  try:
    import numpy 
    import PIL  
    packages = True
  except ImportError:
    packages = False
  return {"installed": path is not None, "version": version, "packages": packages, "usable": path is not None and packages}