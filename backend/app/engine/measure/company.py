from __future__ import annotations
import contextvars
from contextlib import contextmanager
from app.engine.measure import rulebook as RB

COMPANY, QS_WORKBOOK, PROJECT, CODE_DEFAULT_ASSUMED = RB.COMPANY, RB.QS_WORKBOOK, RB.PROJECT, RB.CODE_DEFAULT_ASSUMED
ORIGINS = (COMPANY, QS_WORKBOOK, PROJECT, CODE_DEFAULT_ASSUMED)
STORED_ORIGINS = (COMPANY, QS_WORKBOOK)

ORIGIN_TEXT = {
  COMPANY: "set by your company",
  QS_WORKBOOK: "taken from the QS's answers and workbook",
  PROJECT: "set for one project",
  CODE_DEFAULT_ASSUMED: "assumed: the company has set none, so the software's own figure is used",
}

_LAYER = contextvars.ContextVar("company_conventions", default=None)

def _clean(layer) -> dict:
  out: dict = {}
  for key, row in (layer or {}).items():
    if isinstance(row, dict) and row.get("value") is not None:
      origin = row.get("origin")
      out[str(key)] = {"value": row["value"], "origin": origin if origin in STORED_ORIGINS else COMPANY}
  return out

def hold(layer) -> None:
  _LAYER.set(_clean(layer))
  RB.hold_layer(_LAYER.get())

@contextmanager
def using(layer):
  token = _LAYER.set(_clean(layer))
  with RB.using_layer(_LAYER.get()):
    try:
      yield
    finally:
      _LAYER.reset(token)

def _legacy(name: str):
  row = (_LAYER.get() or {}).get(name)
  return None if row is None else row["value"]

RB.LEGACY = _legacy

def value(name: str):
  if not RB.enabled():
    return _legacy(name)
  rv = RB.lookup(name)
  return None if rv is None else rv.value

def pick(name: str, code_default):
  return RB.pick(name, code_default)

def origin_of(*names: str) -> str:
  if not RB.enabled():
    rows = _LAYER.get() or {}
    found = [rows.get(n) for n in names]
    if not names or any(r is None for r in found):
      return CODE_DEFAULT_ASSUMED
    return COMPANY if any(r["origin"] != QS_WORKBOOK for r in found) else QS_WORKBOOK
  
  found = [RB.lookup(n) for n in names]
  if not names or any(r is None for r in found):
    return CODE_DEFAULT_ASSUMED
  if any(r.origin == PROJECT for r in found):
    return PROJECT
  return COMPANY if any(r.origin != QS_WORKBOOK for r in found) else QS_WORKBOOK

def stamp() -> dict:
  return {k: r["value"] for k, r in (_LAYER.get() or {}).items()}