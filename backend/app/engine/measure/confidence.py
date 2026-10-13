from __future__ import annotations
from decimal import Decimal

VERIFIED = "VERIFIED"
MESH = "MESH"
MISMATCH = "MISMATCH"

_CHECK_BY_CODE = {
  "QTO_MESH_MISMATCH": MISMATCH,
  "QTO_MESH_VERIFIED": VERIFIED,
  "QUANTITY_FROM_MESH": MESH,
}
_PRECEDENCE = (MISMATCH, VERIFIED, MESH)

BOX_FACTOR_UNCHECKED = Decimal("0.6")
BOX_FACTOR = {VERIFIED: Decimal("0.9"), MESH: Decimal("0.85"), MISMATCH: Decimal("0.5")}
BOX_FACTOR_BBOX_VOLUME = Decimal("0.4")

HIGH_AT = Decimal("0.9")
MEDIUM_AT = Decimal("0.7")
HIGH, MEDIUM, LOW = "HIGH", "MEDIUM", "LOW"


def volume_check(issues) -> str | None:
  found = {_CHECK_BY_CODE[i.get("code")] for i in (issues or ()) if isinstance(i, dict) and i.get("code") in _CHECK_BY_CODE}
  for check in _PRECEDENCE:
    if check in found:
      return check
  return None

def box_factor(check: str | None, from_bbox: bool = False) -> Decimal:
  if from_bbox:
    return BOX_FACTOR_BBOX_VOLUME
  return BOX_FACTOR.get(check, BOX_FACTOR_UNCHECKED)

def stands_on_its_own(check: str | None, from_bbox: bool = False) -> bool:
  return not from_bbox and check in (VERIFIED, MESH)

def band(confidence) -> str:
  value = Decimal(str(confidence))
  if value >= HIGH_AT:
    return HIGH
  if value >= MEDIUM_AT:
    return MEDIUM
  return LOW