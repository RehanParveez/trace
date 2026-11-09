from __future__ import annotations
import functools
import os
import re
import yaml

NATIVE, OUTLINED_OCR, IMAGE_OCR = "NATIVE", "OUTLINED_OCR", "IMAGE_OCR"
SOURCES = (NATIVE, OUTLINED_OCR, IMAGE_OCR)
CODES = {NATIVE: 0, OUTLINED_OCR: 1, IMAGE_OCR: 2}
BY_CODE = {v: k for k, v in CODES.items()}
OCR_BUDGET, REGION_LIMIT = "OCR_BUDGET", "REGION_LIMIT"
TURNED = "TURNED_"
STROKED = "LETTERING_STROKES"
PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "words_settings.yaml")
DIMENSION = re.compile(r"""^\d{1,3}(['\u2019]-?\d{0,2}["\u201d]?|["\u201d])?(\s?[xX]\s?\d{1,3}(['\u2019]-?\d{0,2}["\u201d]?|["\u201d])?)?$""")
MARK = re.compile(r"^[A-Z]{1,3}-?\d{1,2}[A-Z]?$")

class SettingsError(ValueError):
  pass

@functools.lru_cache(maxsize=1)
def settings() -> dict:
  with open(PATH, encoding="utf-8") as fh:
    doc = yaml.safe_load(fh) or {}
  bad = [k for k, v in doc.items() if isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0]
  if bad:
    raise SettingsError("words_settings.yaml: " + ", ".join(sorted(bad)) + " must be numbers above zero")
  return doc

def setting(name: str) -> float:
  return float(settings()[name])

def parses(text: str, vocabulary: set | None = None) -> str | None:
  t = (text or "").strip()
  if len(t) < setting("cluster_min_chars"):
    return None
  u = t.upper()
  if MARK.match(u):
    return "MARK"
  if len(t) >= 3 and t.isalpha() and (vocabulary is None or u in vocabulary or t.lower() in vocabulary):
    return "WORD"
  if DIMENSION.match(t):
    return "DIMENSION"
  return None

def confidence_of(word) -> float:
  if getattr(word, "source", NATIVE) == NATIVE:
    return setting("native_repaired_confidence") if getattr(word, "repair", "") else 1.0
  return float(getattr(word, "confidence", 1.0))

def settle(words: list) -> None:
  for w in words:
    if getattr(w, "source", NATIVE) == NATIVE and getattr(w, "repair", ""):
      w.confidence = setting("native_repaired_confidence")

def stamp(words: list, source: str, confidences: list | None = None) -> list:
  for i, w in enumerate(words):
    w.source = source
    if confidences is not None and i < len(confidences):
      w.confidence = round(max(0.0, min(1.0, float(confidences[i]) / 100.0)), 3)
  return words

def keep_picture_word(text: str, conf: float) -> bool:
  return conf >= setting("image_keep_confidence") and len(text.strip()) >= setting("image_min_chars") and any(ch.isalnum() for ch in text)

def record(words: list, notes: dict | None = None) -> dict:
  out: dict = {"by_source": {s: 0 for s in SOURCES}, "low": 0}
  low = setting("low_confidence")
  conf = {s: [] for s in SOURCES}
  turned = 0
  stroked = 0
  for w in words:
    s = getattr(w, "source", NATIVE)
    if s not in out["by_source"]:
      s = NATIVE
    out["by_source"][s] += 1
    c = confidence_of(w)
    conf[s].append(c)
    
    if c < low:
      out["low"] += 1
    if str(getattr(w, "repair", "")).startswith(TURNED):
      turned += 1
    if str(getattr(w, "repair", "")) == STROKED:
      stroked += 1
  out["mean_confidence"] = {s: round(sum(v) / len(v), 3) for s, v in conf.items() if v}
  if turned:
    out["turned"] = turned
  if stroked:
    out["stroked"] = stroked
  if notes:
    out.update(notes)
  return out

def text_type(counts: dict) -> str:
  n = {s: int(counts.get(s, 0)) for s in SOURCES}
  total = sum(n.values())
  if not total:
    return "NONE"
  if n[NATIVE] == total:
    return "TEXT"
  if n[OUTLINED_OCR] == total:
    return "OUTLINED"
  if n[IMAGE_OCR] == total:
    return "RASTER"
  return "MIXED"

def turned_readings(img, axis: int, read, accept) -> tuple | None:
  text, conf = read(img)
  if accept(text) and conf >= setting("cluster_general_confidence"):
    return text, conf, 0
  for turn in ((180,) if axis == 0 else (90, 270)):
    text, conf = read(img.rotate(turn, expand=True))
    if accept(text) and conf >= setting("turned_keep_confidence"):
      return text, conf, turn
  return None
