from __future__ import annotations
import json
from decimal import Decimal as D
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4
import pytest
from pydantic import ValidationError
from pypdf import PdfWriter
from app.core.exceptions import TraceException
from app.engine.measure import takeoff as t
from app.modules.drawings_boq import boq_logic as logic
from app.modules.drawings_boq.takeoff import repository as repo
from app.modules.drawings_boq.takeoff import service as svc
from app.modules.drawings_boq.takeoff.scale import parse_scale_text, to_mm
from app.modules.drawings_boq.takeoff.schemas import CalibrationCreateRequest, KnownDistance, MeasurementCreateRequest

def test_scale_text_metric_and_imperial():
  assert parse_scale_text("1:100") == D("100")
  assert parse_scale_text("SCALE 1 : 50") == D("50")
  assert parse_scale_text('1/8" = 1\'-0"') == D("96")
  assert parse_scale_text('3/32" = 1\'') == D("128")
  assert parse_scale_text('1" = 10\'') == D("120")
  assert parse_scale_text("2:1") == D("0.5")

def test_scale_text_rejects_non_scales():
  for text in ("NTS", "N.T.S.", "not to scale", "1:0", "hello", "", None, "1:100000000"):
    assert parse_scale_text(text) is None

def test_unit_conversion():
  assert to_mm(D("2.5"), "m") == D("2500")
  assert to_mm(D("10"), "ft") == D("3048")
  assert to_mm(D("1"), "in") == D("25.4")
  with pytest.raises(ValueError):
    to_mm(D("1"), "yard")

def _ref(value="10", unit="m"):
  return KnownDistance(p1=[0, 0], p2=[1000, 0], value=D(value), unit=unit)

def test_build_two_point_calibration():
  cols = svc.build_calibration("TWO_POINT", _ref(), None, None, None)
  assert cols["usable"] and cols["mm_per_pt"] == D("10") and cols["baseline_pt"] == D("1000")
  assert cols["ref"]["known_mm"] == "10000.000000" or D(cols["ref"]["known_mm"]) == D("10000")
  assert cols["quality_factor"] == D("0.92")

def test_build_two_point_in_feet_matches_metric():
  a = svc.build_calibration("TWO_POINT", _ref("10", "ft"), None, None, None)
  assert a["mm_per_pt"] == D("3.048")

def test_build_ratio_from_text_and_check_dimension():
  chk = KnownDistance(p1=[0, 50], p2=[500, 50], value=D("17.64"), unit="m")      
  cols = svc.build_calibration("SCALE_RATIO", None, None, "1:100", chk)
  assert cols["usable"] and cols["ratio"] == D("100") and cols["check_error_pct"] < D("0.5")
  assert "PDF_RATIO_UNVERIFIED" not in cols["warnings"]

def test_bad_check_makes_calibration_unusable_but_keeps_reason():
  chk = KnownDistance(p1=[0, 50], p2=[500, 50], value=D("30"), unit="m")
  cols = svc.build_calibration("SCALE_RATIO", None, None, "1:100", chk)
  assert not cols["usable"] and cols["quality_factor"] == D("0") and "differs" in cols["reason"]

def test_unreadable_scale_text_is_a_clear_error():
  with pytest.raises(TraceException) as e:
    svc.build_calibration("SCALE_RATIO", None, None, "as shown", None)
  assert e.value.code == "SCALE_TEXT_UNREADABLE"
  with pytest.raises(TraceException) as e:
    svc.build_calibration("TWO_POINT", None, None, None, None)
  assert e.value.code == "CALIBRATION_INCOMPLETE"

def test_user_unit_scales_ratio_calibration():
  plain = svc.build_calibration("SCALE_RATIO", None, None, "1:100", None, D(1))
  big = svc.build_calibration("SCALE_RATIO", None, None, "1:100", None, D(2))
  assert big["mm_per_pt"] == plain["mm_per_pt"] * 2

def test_page_geometry_reads_boxes_and_rotation():
  w = PdfWriter()
  w.add_blank_page(width=2384, height=1684)
  p = w.add_blank_page(width=595, height=842)
  p.rotate(90)
  buf = BytesIO(); w.write(buf)
  pages = svc.page_geometry(buf.getvalue())
  assert [(g["page_no"], g["width_pt"], g["height_pt"], g["rotation"]) for g in pages] == [(1, 2384.0, 1684.0, 0), (2, 595.0, 842.0, 90)]

def test_page_geometry_rejects_garbage():
  with pytest.raises(TraceException) as e:
    svc.page_geometry(b"not a pdf")
  assert e.value.code == "PDF_UNREADABLE"

def test_computed_json_is_plain_json():
  s = t.SheetInput(id=uuid4(), drawing_id=uuid4(), page_no=1, content_kind="VECTOR")
  c = t.CalibrationInput(id=uuid4(), sheet_id=s.id, method="TWO_POINT", p1=(D(0), D(0)), p2=(D(1000), D(0)), known_mm=D(10000))
  m = t.MeasurementInput(id=uuid4(), sheet_id=s.id, calibration_id=c.id, kind="LENGTH", quantity_mode="LENGTH_X_HEIGHT",
    geometry={"points": [[0, 0], [300, 0]]}, params={"height_mm": 3000, "openings": [{"role": "DOOR", "width_mm": 900, "height_mm": 2100}]},
    work_item_code="FIN-PLASTER")
  comp = t.compute_measurement(m, s, t.evaluate_calibration(c))
  out = json.loads(json.dumps(svc.computed_json(comp)))
  assert out["quantity"] == "7.110000" and out["unit"] == "m2" and out["formula"] == "PDF_TAKEOFF_LENGTH_X_HEIGHT"

def test_repository_maps_rows_to_kernel_inputs():
  cal_row = SimpleNamespace(id=uuid4(), sheet_id=uuid4(), method="TWO_POINT", ratio=None, label=None,
    ref={"p1": [0, 0], "p2": [1000, 0], "known_mm": "10000"}, check_ref={"p1": [0, 50], "p2": [500, 50], "known_mm": "5000"})
  ci = repo.calibration_input(cal_row, D(1))
  ev = t.evaluate_calibration(ci)
  assert ev.usable and ev.mm_per_pt == D(10) and ev.error_pct == D("0.0000")
  assert repo.sheet_user_unit(SimpleNamespace(prep_meta={"user_unit": 2.0})) == D(2)
  assert repo.sheet_user_unit(SimpleNamespace(prep_meta={})) == D(1)

def test_geometry_normalisation_is_what_gets_stored():
  g = t.normalized_geometry("AREA", {"outer": [[0, 0], [100.123456, 0], [100, 100], [0, 100], [0, 0]]})
  assert g["outer"][1] == [100.1235, 0.0] and len(g["outer"]) == 4 and g["holes"] == []
  assert t.geometry_hash("AREA", g) == t.geometry_hash("AREA", {"outer": g["outer"]})

def test_schema_guards():
  with pytest.raises(ValidationError):
    CalibrationCreateRequest(method="TWO_POINT")
  with pytest.raises(ValidationError):
    CalibrationCreateRequest(method="SCALE_RATIO")
  with pytest.raises(ValidationError):
    KnownDistance(p1=[0, float("nan")], p2=[1, 1], value=D(1))
  with pytest.raises(ValidationError):
    MeasurementCreateRequest(kind="LENGTH", geometry={}, params={"repeat": 0})
  ok = MeasurementCreateRequest(kind="LENGTH", geometry={}, params={"height_mm": "3000"})
  assert ok.params.model_dump(mode="json", exclude_none=True)["height_mm"] == "3000"

def test_modes_listing_drives_the_ui():
  modes = svc.TakeoffService.modes()
  assert len(modes) == 10
  wall = next(m for m in modes if m["quantity_mode"] == "LENGTH_X_HEIGHT_X_THICKNESS")
  assert wall["output_unit"] == "m3" and wall["required_params"] == ["height_mm", "thickness_mm"]

def test_issue_specs_from_run_stats():
  stats = {
    "not_counted": [{"work_item_code": "FIN-FLOOR", "level_id": None, "measurements": 2}],
    "skipped": {"PDF_UNCALIBRATED": 1, "WORK_ITEM_RESERVED": 1, "PDF_MEASUREMENT_UNASSIGNED": 3},
    "variances": [
      {"work_item_code": "FIN-FLOOR", "level_id": None, "unit": "m2", "pdf_quantity": "10", "model_quantity": "9", "variance_pct": "11.1111",
        "over_tolerance": True, "tolerance_pct": "5"},
      {"work_item_code": "CONC-COL", "level_id": None, "unit": "m3", "pdf_quantity": "1", "model_quantity": "1", "variance_pct": "0",
        "over_tolerance": False, "tolerance_pct": "5"}],
  }
  specs = {s.code: s for s in logic.takeoff_issue_specs(stats)}
  assert specs["PDF_MEASUREMENT_NOT_COUNTED"].blocks == "APPROVAL"
  assert specs["PDF_UNCALIBRATED"].severity == "error" and specs["PDF_UNCALIBRATED"].blocks == "APPROVAL"
  assert specs["PDF_MEASUREMENT_UNASSIGNED"].blocks == "NONE"
  assert specs["PDF_MEASUREMENT_SKIPPED"].details["reason"] == "WORK_ITEM_RESERVED"
  assert specs["PDF_MODEL_VARIANCE"].severity == "info" and "11.1111" in specs["PDF_MODEL_VARIANCE"].message
  assert len([s for s in logic.takeoff_issue_specs(stats) if s.code == "PDF_MODEL_VARIANCE"]) == 1
  keys = [s.dedupe_key for s in logic.takeoff_issue_specs(stats)]
  assert len(keys) == len(set(keys))

def test_every_warning_the_kernel_can_emit_has_a_catalog_entry():
  for code in t.WARNING_CODES:
    assert code in logic.LEDGER_WARNING_CATALOG
  for code in t.WARNING_CODES:
    if code not in ("PDF_ADDED_TO_MODEL", "PDF_REPLACES_MODEL"):
      assert code in logic.REVIEW_WARNING_CODES