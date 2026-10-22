from __future__ import annotations
from dataclasses import dataclass
import re
from decimal import Decimal

@dataclass(frozen=True)
class Measure:
  basis: Decimal            
  dim: str                  
  per_si: Decimal           
  word: str

_FACTORS = {
  "cft": ("volume", "0.0283168466"), "cuft": ("volume", "0.0283168466"), "cuftt": ("volume", "0.0283168466"),
  "cum": ("volume", "1"), "cu.m": ("volume", "1"), "cm": ("volume", "1"), "m3": ("volume", "1"),
  "sft": ("area", "0.09290304"), "sqft": ("area", "0.09290304"),
  "sqm": ("area", "1"), "sq.m": ("area", "1"), "m2": ("area", "1"),
  "rft": ("length", "0.3048"), "ft": ("length", "0.3048"),
  "metre": ("length", "1"), "meter": ("length", "1"), "m": ("length", "1"), "rm": ("length", "1"), "mtr": ("length", "1"),
  "km": ("length", "1000"),
  "cwt": ("mass", "50.80234544"), "foot": ("length", "0.3048"), "feet": ("length", "0.3048"), "gallon": ("volume", "0.00454609"),
  "ltr": ("volume", "0.001"), "liter": ("volume", "0.001"), "litre": ("volume", "0.001"),
  "ton": ("mass", "1016.0469088"), "tonne": ("mass", "1000"), "mt": ("mass", "1000"),
  "kg": ("mass", "1"), "quintal": ("mass", "100"), "maund": ("mass", "37.3242"), "mds": ("mass", "37.3242"), "md": ("mass", "37.3242"),
  "nos": ("count", "1"), "no": ("count", "1"), "each": ("count", "1"), "pcs": ("count", "1"), "piece": ("count", "1"), "bag": ("count", "1"),
  "bags": ("count", "1"),
}

def unit_core(text: str | None) -> str | None:
  if not text:
    return text
  return re.sub(r"\s+of\b.*$", "", text.strip(), flags=re.I) or text

def measure_of(text: str | None) -> Measure | None:
  if not text:
    return None
  t = re.sub(r"\s+", " ", unit_core(text).strip().lower())
  t = re.sub(r"\bper\b", "", t).strip()
  t = t.replace("p.cft", "cft").replace("p.cum", "cum").replace("p.rft", "rft").replace("p.sft", "sft").replace("p.cu.m", "cum")
  t = t.replace("p.metre", "metre").replace("p.meter", "meter")
  m = re.match(r"^(\d[\d,]*)\s*(.*)$", t)
  
  basis = Decimal(1)
  if m:
    basis, t = Decimal(m.group(1).replace(",", "")), m.group(2)
  t = t.replace(".", "").replace(" ", "")
  if t not in _FACTORS and re.sub(r"s$", "", t) in _FACTORS:
    t = re.sub(r"s$", "", t)
  hit = _FACTORS.get(t)
  if hit is None:
    return None
  return Measure(basis, hit[0], Decimal(hit[1]), t)

def _plain(text: str | None) -> str:
  return re.sub(r"[^a-z0-9]+", "", (text or "").lower())

def price_per_si(rate: Decimal, unit_text: str | None) -> tuple[Decimal, str] | None:
  ms = measure_of(unit_text)
  if ms is None or rate is None:
    return None
  size = ms.basis * ms.per_si
  return (rate / size, ms.dim) if size else None

def agree(rate_b: Decimal | None, unit_b: str | None, rate_m: Decimal | None, unit_m: str | None, tolerance: float = 0.012) -> bool | None:
 
  if rate_b is None or rate_m is None or rate_b == 0 or rate_m == 0:
    return None
  a, b = price_per_si(rate_b, unit_b), price_per_si(rate_m, unit_m)
  if a is None and b is None and _plain(unit_b) and _plain(unit_b) == _plain(unit_m):
    a, b = (rate_b, "same"), (rate_m, "same")        
  if a is None or b is None or a[1] != b[1]:
    return None
  hi, lo = max(a[0], b[0]), min(a[0], b[0])
  return float((hi - lo) / hi) <= tolerance
