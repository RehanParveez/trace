from __future__ import annotations

SHIFT = 0x1D
SYMBOLS = frozenset(chr(c - SHIFT) for c in range(ord("A"), ord("Z") + 1))

TITLE_WORDS = frozenset("""
GROUND FLOOR FIRST SECOND THIRD FOURTH ROOF BASEMENT FOUNDATION FOUNDATIONS MEZZANINE TYPICAL MUMTY
PLAN PLANS LAYOUT FRAMING BEAM BEAMS SLAB SLABS COLUMN COLUMNS FOOTING FOOTINGS LINTEL LINTELS STAIR STAIRCASE TANK
STRUCTURE STRUCTURAL ARCHITECTURAL ELECTRICAL PLUMBING SANITARY REINFORCEMENT
SECTION SECTIONS ELEVATION ELEVATIONS DETAIL DETAILS SCHEDULE SCHEDULES SITE LEGEND SYMBOLS NOTES GENERAL SPECIFICATIONS
""".split())

def repair_word(text: str) -> str:
  if not any(c in SYMBOLS for c in text):
    return text
  fixed = "".join(chr(ord(c) + SHIFT) if c in SYMBOLS else c for c in text)
  return fixed if fixed in TITLE_WORDS else text

def repair(words: list) -> int:
  n = 0
  for w in words:
    fixed = repair_word(w.text)
    if fixed != w.text:
      w.text = fixed
      n += 1
  return n
