from __future__ import annotations
from decimal import Decimal, InvalidOperation
import re

UNIT_TO_MM = {
  "mm": Decimal("1"), "cm": Decimal("10"), "m": Decimal("1000"),
  "in": Decimal("25.4"), "ft": Decimal("304.8"),
}
MIN_RATIO = Decimal("0.01")
MAX_RATIO = Decimal("100000")

_NOT_TO_SCALE = re.compile(r"\b(n\.?\s?t\.?\s?s\.?|not\s+to\s+scale|no\s+scale)\b", re.I)
_RATIO = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*(?::|/)\s*(\d+(?:\.\d+)?)(?![\d.]*\s*[\"'″′])")
_IMPERIAL = re.compile(
  r"(?P<p>(?:\d+\s+)?\d+\s*/\s*\d+|\d+(?:\.\d+)?)\s*(?:\"|in\b|inch(?:es)?\b)\s*=\s*"
  r"(?P<f>\d+(?:\.\d+)?)\s*(?:'|ft\b|feet\b|foot\b)?"
  r"(?:\s*-?\s*(?P<i>\d+(?:\.\d+)?)\s*(?:\"|in\b)?)?", re.I)

def to_mm(value: Decimal, unit: str) -> Decimal:
  factor = UNIT_TO_MM.get((unit or "").strip().lower())
  if factor is None:
    raise ValueError(f"Unknown length unit '{unit}'.")
  return Decimal(value) * factor

MIN_IMPERIAL_RATIO = Decimal("1")
_PAPER_INCHES = {"1/32": Decimal(1) / 32, "1/16": Decimal(1) / 16, "3/32": Decimal(3) / 32, "1/8": Decimal(1) / 8, "3/16": Decimal(3) / 16, "1/4": Decimal(1) / 4, "3/8": Decimal(3) / 8,
  "1/2": Decimal(1) / 2, "5/8": Decimal(5) / 8, "3/4": Decimal(3) / 4}

def _repair_paper_inches(raw: str) -> Decimal | None:
  s = re.sub(r"\s+", "", raw or "")
  if "/" in s or not s.isdigit() or len(s) < 3 or s[1] != "1":
    return None
  return _PAPER_INCHES.get(f"{s[0]}/{s[2:]}")

def _clean(text: str) -> str:
  return (text or "").replace("″", '"').replace("”", '"').replace("“", '"').replace("′", "'").replace("’", "'").strip()

def _fraction(raw: str) -> Decimal:
  mixed = re.match(r"^\s*(\d+)\s+(\d+)\s*/\s*(\d+)\s*$", raw)
  if mixed:
    return Decimal(mixed.group(1)) + Decimal(mixed.group(2)) / Decimal(mixed.group(3))
  raw = raw.replace(" ", "")
  if "/" in raw:
    num, den = raw.split("/", 1)
    return Decimal(num) / Decimal(den)
  return Decimal(raw)

def parse_scale_text(text: str | None) -> Decimal | None:
  s = _clean(text or "")
  if not s or _NOT_TO_SCALE.search(s):
    return None

  try:
    m = _IMPERIAL.search(s)
    if m:
      paper = _fraction(m.group("p"))
      feet = Decimal(m.group("f"))
      inches = Decimal(m.group("i")) if m.group("i") else Decimal(0)
      ratio = (feet * 12 + inches) / paper if paper > 0 else None
      if ratio is not None and ratio < MIN_IMPERIAL_RATIO:
        fixed = _repair_paper_inches(m.group("p"))
        ratio = (feet * 12 + inches) / fixed if fixed else None
    else:
      m = _RATIO.search(s)
      if not m:
        return None
      a, b = Decimal(m.group(1)), Decimal(m.group(2))
      ratio = b / a if a > 0 else None
  except (InvalidOperation, ZeroDivisionError, ValueError):
    return None
  if ratio is None or ratio < MIN_RATIO or ratio > MAX_RATIO:
    return None
  return ratio.quantize(Decimal("0.0001"))