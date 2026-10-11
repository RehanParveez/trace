from __future__ import annotations
from decimal import Decimal as D
from uuid import uuid4
import pytest
from app.engine.measure import takeoff as t
from app.engine.measure.models import CalculationContext, LedgerEntry
from app.engine.measure.profile import OpeningRuleSpec, ResolvedRuleProfile

def _profile(opening_rules=(), tolerances=None):
  return ResolvedRuleProfile(
    rule_set_id="t", code="T", immutable_version=1, content_hash=None, convention_code=None, conserves_volume=True,
    jurisdiction=None, province=None, standard_name=None, standard_edition=None, wall_measurement_method="centre_line",
    net_vs_gross_preference="net", preferred_units={}, tolerances=tolerances or {}, opening_rules=tuple(opening_rules),
    finish_rules=())

def _ctx():
  return CalculationContext(run_id=uuid4(), engine_version="t", fingerprint="t", convention_code=None,
    rule_set_code="T", rule_set_version=1, mappings=())

def _sheet(kind="VECTOR"):
  return t.SheetInput(id=uuid4(), drawing_id=uuid4(), page_no=1, content_kind=kind)

def _two_point(sheet, mm_per_pt=10, baseline=1000, check=None):
  kwargs = {}
  if check is not None:
    kwargs = dict(check_p1=(D(0), D(50)), check_p2=(D(500), D(50)), check_known_mm=D(check))
  return t.CalibrationInput(id=uuid4(), sheet_id=sheet.id, method="TWO_POINT", p1=(D(0), D(0)), p2=(D(baseline), D(0)),
    known_mm=D(mm_per_pt * baseline), **kwargs)

def _m(sheet, cal, kind, mode, geometry, params=None, code="CONC-WALL", recon="AUTO", level=None, source="MANUAL"):
  return t.MeasurementInput(id=uuid4(), sheet_id=sheet.id, calibration_id=cal.id if cal else None, kind=kind,
    quantity_mode=mode, geometry=geometry, params=params or {}, work_item_code=code, level_id=level, recon_mode=recon,
    source=source)

RECT = {"outer": [[0, 0], [100, 0], [100, 100], [0, 100]]}
LINE = {"points": [[0, 0], [300, 0], [300, 400]]}

def _model_row(code="CONC-WALL", qty="10", unit="m3", level=None):
  return LedgerEntry(solid_id=uuid4(), element_id=uuid4(), level_id=level, work_item_code=code, quantity=D(qty), unit=unit,
    material_grade=None, confidence=D("0.9"), formula_code="X", trace={"formula_code": "X"})

def _run(measurements, sheets, cals, model=(), profile=None):
  inp = t.TakeoffInputs(sheets=tuple(sheets), calibrations=tuple(cals), measurements=tuple(measurements))
  return t.measure_takeoff(_ctx(), profile or _profile(), inp, model)

def test_two_point_calibration_is_exact():
  s = _sheet()
  ev = t.evaluate_calibration(_two_point(s))
  assert ev.usable and ev.mm_per_pt == D(10)
  assert ev.factor == D("0.92") and not ev.warnings

def test_scale_ratio_calibration_one_to_hundred():
  s = _sheet()
  cal = t.CalibrationInput(id=uuid4(), sheet_id=s.id, method="SCALE_RATIO", ratio=D(100))
  ev = t.evaluate_calibration(cal)
  assert ev.usable and abs(ev.mm_per_pt - D("35.2777778")) < D("0.0001")
  assert ev.factor == D("0.80") and "PDF_RATIO_UNVERIFIED" in ev.warnings

def test_check_dimension_error_bands():
  s = _sheet()
  ok = t.evaluate_calibration(_two_point(s, check=5000))          
  assert ok.error_pct == D("0.0000") and ok.factor == D(1)
  one = t.evaluate_calibration(_two_point(s, check=5040))         
  assert one.usable and one.factor == D("0.95")
  mid = t.evaluate_calibration(_two_point(s, check=5100))          
  assert mid.usable and mid.factor == D("0.85") and "PDF_SCALE_MISMATCH" in mid.warnings
  bad = t.evaluate_calibration(_two_point(s, check=5300))          
  assert not bad.usable and "PDF_SCALE_MISMATCH" in bad.warnings

def test_short_baseline_penalised():
  s = _sheet()
  ev = t.evaluate_calibration(_two_point(s, baseline=50))
  assert ev.usable and "PDF_CAL_SHORT_BASELINE" in ev.warnings and ev.factor == D("0.828")

def test_degenerate_calibration_rejected():
  s = _sheet()
  cal = t.CalibrationInput(id=uuid4(), sheet_id=s.id, method="TWO_POINT", p1=(D(5), D(5)), p2=(D(5), D(5)), known_mm=D(1000))
  assert not t.evaluate_calibration(cal).usable

def test_polyline_length_hand_check():
  s = _sheet(); c = _two_point(s)
  comp = t.compute_measurement(_m(s, c, "LENGTH", "DIRECT", LINE), s, t.evaluate_calibration(c))
  assert comp.quantity == D("7.000000") and comp.unit == "m"        

def test_area_with_hole():
  s = _sheet(); c = _two_point(s)
  geo = {**RECT, "holes": [[[10, 10], [30, 10], [30, 30], [10, 30]]]}
  comp = t.compute_measurement(_m(s, c, "AREA", "DIRECT", geo, code="FIN-FLOOR"), s, t.evaluate_calibration(c))
  assert comp.quantity == D("0.960000")                              

def test_self_intersecting_area_rejected():
  s = _sheet(); c = _two_point(s)
  bow = {"outer": [[0, 0], [100, 100], [100, 0], [0, 100]]}
  with pytest.raises(t.TakeoffError) as e:
    t.compute_measurement(_m(s, c, "AREA", "DIRECT", bow), s, t.evaluate_calibration(c))
  assert e.value.code == "SELF_INTERSECTING"

def test_wall_height_and_door_deduction():
  s = _sheet(); c = _two_point(s)
  prm = {"height_mm": 3000, "openings": [{"role": "DOOR", "width_mm": 900, "height_mm": 2100, "nos": 1}]}
  comp = t.compute_measurement(_m(s, c, "LENGTH", "LENGTH_X_HEIGHT", LINE, prm, code="FIN-PLASTER"), s, t.evaluate_calibration(c))
  assert comp.quantity == D("19.110000")                             

def test_wall_volume_applies_opening_before_thickness():
  s = _sheet(); c = _two_point(s)
  prm = {"height_mm": 3000, "thickness_mm": 230, "openings": [{"role": "DOOR", "width_mm": 900, "height_mm": 2100, "nos": 1}]}
  comp = t.compute_measurement(_m(s, c, "LENGTH", "LENGTH_X_HEIGHT_X_THICKNESS", LINE, prm), s, t.evaluate_calibration(c))
  assert comp.quantity == D("4.395300") and comp.unit == "m3"        

def test_small_opening_ignored_by_rule_profile():
  s = _sheet(); c = _two_point(s)
  rules = [OpeningRuleSpec("ALL", D("0"), D("2"), "IGNORE")]
  prm = {"height_mm": 3000, "openings": [{"role": "DOOR", "width_mm": 900, "height_mm": 2100, "nos": 1}]}
  comp = t.compute_measurement(_m(s, c, "LENGTH", "LENGTH_X_HEIGHT", LINE, prm), s, t.evaluate_calibration(c), _profile(rules))
  assert comp.quantity == D("21.000000")

def test_slab_volume_adjustments_and_repeat():
  s = _sheet(); c = _two_point(s)
  prm = {"thickness_mm": 150, "adjustments": [{"op": "LESS", "value": "0.05"}], "repeat": 3}
  comp = t.compute_measurement(_m(s, c, "AREA", "AREA_X_THICKNESS", RECT, prm, code="CONC-SLAB"), s, t.evaluate_calibration(c))
  assert comp.quantity == D("0.300000")                              

def test_beam_section_volume():
  s = _sheet(); c = _two_point(s)
  prm = {"width_mm": 230, "depth_mm": 450}
  comp = t.compute_measurement(_m(s, c, "LENGTH", "LENGTH_X_SECTION", LINE, prm, code="CONC-BEAM"), s, t.evaluate_calibration(c))
  assert comp.quantity == D("0.724500")                              

def test_counts_and_count_multipliers_ignore_calibration():
  s = _sheet()
  geo = {"points": [[1, 1], [2, 2], [2, 2], [3, 3]]}              # one duplicate
  n = t.compute_measurement(_m(s, None, "COUNT", "DIRECT", geo, code="DOOR-SET"), s, None)
  assert n.quantity == D(3) and n.unit == "nos" and n.confidence == D("0.9500")
  vol = t.compute_measurement(_m(s, None, "COUNT", "COUNT_X_VOLUME", geo, {"length_mm": 1000, "width_mm": 1000, "depth_mm": 1500}), s, None)
  assert vol.quantity == D("4.500000") and vol.unit == "m3"

def test_missing_dimension_and_unit_rules():
  s = _sheet(); c = _two_point(s)
  with pytest.raises(t.TakeoffError) as e:
    t.compute_measurement(_m(s, c, "LENGTH", "LENGTH_X_HEIGHT", LINE, {}), s, t.evaluate_calibration(c))
  assert e.value.code == "MISSING_DIMENSION"
  with pytest.raises(t.TakeoffError):
    t.compute_measurement(_m(s, c, "LENGTH", "AREA_X_THICKNESS", LINE, {"thickness_mm": 100}), s, t.evaluate_calibration(c))
  with pytest.raises(t.TakeoffError):                               
    t.compute_measurement(_m(s, c, "AREA", "DIRECT", RECT, {"openings": [{"width_mm": 1, "height_mm": 1}]}), s, t.evaluate_calibration(c))

def test_confidence_layers():
  s = _sheet("VECTOR"); c = _two_point(s)
  base = t.compute_measurement(_m(s, c, "AREA", "DIRECT", RECT), s, t.evaluate_calibration(c))
  assert D("0.5") < base.confidence <= D("0.95")
  raster = _sheet("RASTER"); rc = _two_point(raster)
  r = t.compute_measurement(_m(raster, rc, "AREA", "DIRECT", RECT), raster, t.evaluate_calibration(rc))
  assert r.confidence < base.confidence and "PDF_SCANNED_LOW_PRECISION" in r.warnings
  assumed = t.compute_measurement(_m(s, c, "LENGTH", "LENGTH_X_HEIGHT", LINE, {"height_mm": 3000, "dims_basis": "ASSUMED"}), s,
    t.evaluate_calibration(c))
  assert "PDF_DIMENSION_ASSUMED" in assumed.warnings
  ratio = t.CalibrationInput(id=uuid4(), sheet_id=s.id, method="SCALE_RATIO", ratio=D(100))
  low = t.compute_measurement(_m(s, ratio, "AREA", "DIRECT", RECT), s, t.evaluate_calibration(ratio))
  assert low.confidence < base.confidence and "PDF_RATIO_UNVERIFIED" in low.warnings

def test_small_shape_flags_low_precision():
  s = _sheet(); c = _two_point(s)
  tiny = {"outer": [[0, 0], [2, 0], [2, 2], [0, 2]]}
  comp = t.compute_measurement(_m(s, c, "AREA", "DIRECT", tiny), s, t.evaluate_calibration(c))
  assert "PDF_LOW_PRECISION" in comp.warnings and comp.confidence < D("0.5")

def test_geometry_hash_is_stable_and_sensitive():
  a = t.geometry_hash("LENGTH", LINE)
  assert a == t.geometry_hash("LENGTH", {"points": [[0, 0], [300, 0], [300, 400]], "closed": False})
  assert a != t.geometry_hash("LENGTH", {"points": [[0, 0], [300, 0], [300, 401]]})

def test_run_produces_ledger_with_trace_and_passes_check():
  s = _sheet(); c = _two_point(s)
  m = _m(s, c, "AREA", "AREA_X_THICKNESS", RECT, {"thickness_mm": 150}, code="CONC-SLAB")
  res = _run([m], [s], [c])
  assert len(res.ledger) == 1 and len(res.solids) == 1
  row = res.ledger[0]
  assert row.quantity == D("0.150000") and row.unit == "m3" and row.source_kind == "PDF_TAKEOFF"
  assert row.trace["formula_code"] == "PDF_TAKEOFF_AREA_X_THICKNESS" and row.trace["inputs"]["calibration"]["method"] == "TWO_POINT"
  assert row.solid_id == res.solids[0].id and res.solids[0].geometry_kind == "QTO_ONLY"
  assert t.takeoff_check(res.solids, res.ledger) == []

def test_run_is_deterministic():
  s = _sheet(); c = _two_point(s)
  ms = [_m(s, c, "AREA", "DIRECT", RECT, code="FIN-FLOOR"), _m(s, c, "LENGTH", "DIRECT", LINE, code="FIN-SKIRT")]
  ctx = _ctx()
  inp = t.TakeoffInputs((s,), (c,), tuple(ms))
  assert t.measure_takeoff(ctx, _profile(), inp) == t.measure_takeoff(ctx, _profile(), inp)

def test_reserved_and_unassigned_codes_are_skipped():
  s = _sheet(); c = _two_point(s)
  res = _run([_m(s, c, "LENGTH", "DIRECT", LINE, code="STL-REBAR"), _m(s, c, "LENGTH", "DIRECT", LINE, code=None)], [s], [c])
  assert not res.ledger and res.stats["skipped"] == {"PDF_MEASUREMENT_UNASSIGNED": 1, "WORK_ITEM_RESERVED": 1}

def test_unusable_or_missing_calibration_skips_not_counts():
  s = _sheet(); bad = _two_point(s, check=5300)
  res = _run([_m(s, bad, "LENGTH", "DIRECT", LINE, code="FIN-SKIRT"), _m(s, None, "LENGTH", "DIRECT", LINE, code="FIN-SKIRT")], [s], [bad])
  assert not res.ledger and res.stats["skipped"] == {"CALIBRATION_UNUSABLE": 1, "PDF_UNCALIBRATED": 1}

def test_auto_without_model_is_counted():
  s = _sheet(); c = _two_point(s)
  res = _run([_m(s, c, "AREA", "DIRECT", RECT, code="FIN-FLOOR")], [s], [c], model=[_model_row("CONC-WALL")])
  assert len(res.ledger) == 1 and res.results[0]["decision"] == "COUNTED"

def test_auto_with_model_is_verified_not_counted_and_variance_recorded():
  s = _sheet(); c = _two_point(s)
  m = _m(s, c, "AREA", "DIRECT", RECT, code="FIN-FLOOR")
  res = _run([m], [s], [c], model=[_model_row("FIN-FLOOR", "0.9", "m2")])
  assert not res.ledger and res.results[0]["decision"] == "VERIFIED"
  assert res.stats["not_counted"] == [{"work_item_code": "FIN-FLOOR", "level_id": None, "measurements": 1}]
  v = res.stats["variances"][0]
  assert v["pdf_quantity"] == "1.000000" and v["model_quantity"] == "0.900000" and v["variance_pct"] == "11.1111" and v["over_tolerance"]

def test_variance_tolerance_comes_from_profile():
  s = _sheet(); c = _two_point(s)
  m = _m(s, c, "AREA", "DIRECT", RECT, code="FIN-FLOOR", recon="VERIFY_ONLY")
  res = _run([m], [s], [c], model=[_model_row("FIN-FLOOR", "0.9", "m2")], profile=_profile(tolerances={"pdf_model_variance_pct": "15"}))
  assert not res.stats["variances"][0]["over_tolerance"] and not res.stats["not_counted"]

def test_add_counts_next_to_model():
  s = _sheet(); c = _two_point(s)
  m = _m(s, c, "AREA", "DIRECT", RECT, code="FIN-FLOOR", recon="ADD")
  res = _run([m], [s], [c], model=[_model_row("FIN-FLOOR", "5", "m2")])
  assert len(res.ledger) == 1 and "PDF_ADDED_TO_MODEL" in res.ledger[0].warnings and not res.dropped_keys

def test_replace_model_drops_model_rows_and_counts_auto_peers():
  s = _sheet(); c = _two_point(s)
  model = _model_row("FIN-FLOOR", "5", "m2")
  keep = _model_row("CONC-SLAB", "9", "m3")
  rep = _m(s, c, "AREA", "DIRECT", RECT, code="FIN-FLOOR", recon="REPLACE_MODEL")
  peer = _m(s, c, "AREA", "DIRECT", {"outer": [[0, 0], [50, 0], [50, 50], [0, 50]]}, code="FIN-FLOOR")   
  res = _run([rep, peer], [s], [c], model=[model, keep])
  assert len(res.ledger) == 2 and all("PDF_REPLACES_MODEL" in r.warnings or r.work_item_code == "FIN-FLOOR" for r in res.ledger)
  assert res.dropped_keys == frozenset({(model.solid_id, "FIN-FLOOR")})
  left = t.apply_replacements([model, keep], res.dropped_keys)
  assert left == [keep]
  assert res.stats["replaced"][0]["rows_dropped"] == 1

def test_level_specific_measurement_only_matches_same_level_or_none():
  s = _sheet(); c = _two_point(s)
  l1, l2 = uuid4(), uuid4()
  m = _m(s, c, "AREA", "DIRECT", RECT, code="FIN-FLOOR", level=l1)
  covered = _run([m], [s], [c], model=[_model_row("FIN-FLOOR", "5", "m2", level=l1)])
  assert not covered.ledger
  free = _run([m], [s], [c], model=[_model_row("FIN-FLOOR", "5", "m2", level=l2)])
  assert len(free.ledger) == 1

def test_pdf_rows_never_count_as_model_coverage():
  s = _sheet(); c = _two_point(s)
  prior = LedgerEntry(solid_id=uuid4(), element_id=None, level_id=None, work_item_code="FIN-FLOOR", quantity=D(3), unit="m2",
    material_grade=None, confidence=D(1), formula_code="X", trace={}, source_kind="PDF_TAKEOFF")
  res = _run([_m(s, c, "AREA", "DIRECT", RECT, code="FIN-FLOOR")], [s], [c], model=[prior])
  assert len(res.ledger) == 1

def test_takeoff_check_catches_tampering():
  s = _sheet(); c = _two_point(s)
  res = _run([_m(s, c, "LENGTH", "DIRECT", LINE, code="FIN-SKIRT")], [s], [c])
  import dataclasses
  bad = dataclasses.replace(res.ledger[0], quantity=D("99"))
  assert t.takeoff_check(res.solids, [bad])
  reserved = dataclasses.replace(res.ledger[0], work_item_code="STL-STRUCT")
  assert t.takeoff_check(res.solids, [reserved])

def test_payload_changes_when_geometry_changes():
  s = _sheet(); c = _two_point(s)
  m1 = _m(s, c, "LENGTH", "DIRECT", LINE, code="FIN-SKIRT")
  m2 = t.MeasurementInput(**{**m1.__dict__, "geometry": {"points": [[0, 0], [10, 0]]}})
  p1 = t.takeoff_payload(t.TakeoffInputs((s,), (c,), (m1,)))
  p2 = t.takeoff_payload(t.TakeoffInputs((s,), (c,), (m2,)))
  assert p1 != p2 and t.takeoff_payload(None) == {}