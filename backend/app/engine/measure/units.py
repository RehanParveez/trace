from __future__ import annotations
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP

class Unit(str, Enum):
  M3 = "m3"
  M2 = "m2"
  M = "m"
  KG = "kg"
  NOS = "nos"

MM3_PER_M3 = Decimal("1000000000")
_Q6 = Decimal("0.000001")
_Q4 = Decimal("0.0001")

def to_decimal(value) -> Decimal:
  if isinstance(value, Decimal):
    return value
  if isinstance(value, float):
    return Decimal(repr(value))
  return Decimal(str(value))

def q6(value: Decimal) -> Decimal:
  return value.quantize(_Q6, rounding=ROUND_HALF_UP)

def q4(value: Decimal) -> Decimal:
  return value.quantize(_Q4, rounding=ROUND_HALF_UP)

def mm3_to_m3(value) -> Decimal:
  return q6(to_decimal(value) / MM3_PER_M3)