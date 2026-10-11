from __future__ import annotations
from decimal import Decimal as D
from uuid import uuid4
import pytest
from app.engine.measure import engine as k
from app.engine.measure import takeoff as t
from app.engine.measure.models import CalculationContext, MappingInput, ModelElement

def _column() -> ModelElement:
  return ModelElement(
    id=uuid4(), ifc_type="IfcColumn", role="COLUMN", level_id=None, geometry_kind="EXTRUDED_PROFILE",
    profile={"kind": "RECT", "x_dim": 300.0, "y_dim": 300.0}, placement={"depth_mm": 3000.0}, volume_mm3=None,
    bbox_min_mm=None, bbox_max_mm=None, classification_confidence=D("0.95"), normalization_status="VALID")

def _inputs(code, recon="AUTO", unit_mode=("AREA", "AREA_X_THICKNESS"), params=None):
  sheet = t.SheetInput(id=uuid4(), drawing_id=uuid4(), page_no=1, content_kind="VECTOR")
  cal = t.CalibrationInput(id=uuid4(), sheet_id=sheet.id, method="TWO_POINT", p1=(D(0), D(0)), p2=(D(1000), D(0)), known_mm=D(10000))
  kind, mode = unit_mode
  m = t.MeasurementInput(id=uuid4(), sheet_id=sheet.id, calibration_id=cal.id, kind=kind, quantity_mode=mode,
    geometry={"outer": [[0, 0], [100, 0], [100, 100], [0, 100]]}, params=params or {"thickness_mm": 150},
    work_item_code=code, recon_mode=recon)
  return t.TakeoffInputs((sheet,), (cal,), (m,))

def _ctx(takeoff, run_id=None):
  return CalculationContext(run_id=run_id or uuid4(), engine_version=k.ENGINE_VERSION, fingerprint="x", convention_code=None,
    rule_set_code="T", rule_set_version=1, mappings=(MappingInput("IfcColumn", "CONC-COL", D("0.95")),), takeoff=takeoff)

def test_engine_version_moved_and_formulas_registered():
  assert k.ENGINE_VERSION == "2026.10.5"
  for formula, unit in t.TAKEOFF_FORMULA_UNITS.items():
    assert k.FORMULA_UNITS[formula] == unit

def test_uncovered_measurement_is_counted_and_self_check_passes():
  res = k.run(_ctx(_inputs("CONC-SLAB")), [_column()])
  codes = {r.work_item_code: r for r in res.ledger}
  assert codes["CONC-COL"].quantity == D("0.270000")
  assert codes["CONC-SLAB"].quantity == D("0.150000") and codes["CONC-SLAB"].source_kind == "PDF_TAKEOFF"
  assert res.stats["pdf_takeoff"]["counted"] == 1

def test_auto_covered_measurement_is_not_counted():
  res = k.run(_ctx(_inputs("CONC-COL")), [_column()])
  rows = [r for r in res.ledger if r.work_item_code == "CONC-COL"]
  assert len(rows) == 1 and rows[0].source_kind == "MODEL"
  stats = res.stats["pdf_takeoff"]
  assert stats["verified"] == 1 and stats["not_counted"][0]["work_item_code"] == "CONC-COL"
  assert stats["variances"][0]["unit"] == "m3"

def test_replace_model_swaps_the_model_row_for_the_pdf_row():
  res = k.run(_ctx(_inputs("CONC-COL", recon="REPLACE_MODEL")), [_column()])
  rows = [r for r in res.ledger if r.work_item_code == "CONC-COL"]
  assert len(rows) == 1 and rows[0].source_kind == "PDF_TAKEOFF" and rows[0].quantity == D("0.150000")
  assert res.stats["pdf_takeoff"]["replaced"][0]["rows_dropped"] == 1

def test_add_keeps_both():
  res = k.run(_ctx(_inputs("CONC-COL", recon="ADD")), [_column()])
  kinds = sorted(r.source_kind for r in res.ledger if r.work_item_code == "CONC-COL")
  assert kinds == ["MODEL", "PDF_TAKEOFF"]

def test_steel_codes_cannot_be_measured_from_pdf():
  res = k.run(_ctx(_inputs("STL-STRUCT")), [_column()])
  assert not [r for r in res.ledger if r.source_kind == "PDF_TAKEOFF"]
  assert res.stats["pdf_takeoff"]["skipped"] == {"WORK_ITEM_RESERVED": 1}

def test_run_with_takeoff_is_deterministic():
  rid, els, inp = uuid4(), [_column()], _inputs("CONC-SLAB")
  assert k.run(_ctx(inp, rid), els) == k.run(_ctx(inp, rid), els)

def test_run_without_takeoff_is_unchanged():
  res = k.run(_ctx(None), [_column()])
  assert res.stats["pdf_takeoff"] == {} and len(res.ledger) == 1

def test_self_check_rejects_a_takeoff_row_without_its_reference():
  res = k.run(_ctx(_inputs("CONC-SLAB")), [_column()])
  row = next(r for r in res.ledger if r.source_kind == "PDF_TAKEOFF")
  import dataclasses
  broken = dataclasses.replace(row, trace={"formula_code": row.formula_code, "inputs": {}})
  with pytest.raises(k.InvariantViolation):
    k.self_check(res.solids, [broken])