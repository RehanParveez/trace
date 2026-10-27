from __future__ import annotations
import re

_FOOT_MARKS = str.maketrans({"’": "'", "‘": "'", "′": "'", "´": "'", "`": "'"})
_INCH_MARKS = str.maketrans({"”": '"', "“": '"', "″": '"'})
_DASHES = str.maketrans({"—": "-", "–": "-", "‒": "-", "−": "-"})
_VULGAR = {"½": " 1/2", "¼": " 1/4", "¾": " 3/4", "⅛": " 1/8", "⅜": " 3/8", "⅝": " 5/8", "⅞": " 7/8"}

_DOUBLE_APOSTROPHE = re.compile(r"(?<=\d)\s*(?:''|’’|‘‘)")
_LENGTH_SHAPE = re.compile(r"^[\dOolI'\"\-\s/]+(?: \d/\d)?$")
_SLASH_FOR_FOOT = re.compile(r"^(\d{1,2})\s*/\s*-\s*(\d{1,2})(\s*\")?$")
_INCH_AS_FOOT = re.compile(r"^(\d{1,3}\s*'\s*-\s*\d{1,2}(?: \d/\d)?)\s*'$")
_LOOKALIKE = str.maketrans({"O": "0", "o": "0", "l": "1", "I": "1"})

def tidy(text: str) -> str:
  s = text or ""
  s = _DOUBLE_APOSTROPHE.sub('"', s)
  s = s.translate(_FOOT_MARKS).translate(_INCH_MARKS).translate(_DASHES)
  for k, v in _VULGAR.items():
    s = s.replace(k, v)
  return s

def clean(text: str) -> str:
  s = tidy(text).strip()
  core = s.strip("()[] ")

  if not core or ("'" not in core and '"' not in core and "/" not in core):
    return s
  if not _LENGTH_SHAPE.match(core) or not re.search(r"\d", core):
    return s
  fixed = core.translate(_LOOKALIKE)
  fixed = re.sub(r"\s+", " ", fixed).strip()
  m = _SLASH_FOR_FOOT.match(fixed)
  if m:
    fixed = f"{m.group(1)}'-{m.group(2)}\""
  m = _INCH_AS_FOOT.match(fixed)
  if m:
    fixed = m.group(1) + '"'
  return fixed
