from __future__ import annotations
from app.engine.measure.rebar import BarSizeSpec, RebarError, RebarInputs, RebarRowInput, ShapeSpec, compute_mark, cut_from_shape, measure_rebar, role_family, self_check_rebar, split_laps, unit_weight
from app.engine.measure.profile import ReinforcementRuleSpec, ResolvedRuleProfile
from app.engine.measure.models import CalculationContext, LedgerEntry, Solid
from decimal import Decimal as D
from uuid import uuid4
import pytest

SIZES = (
  BarSizeSpec("METRIC", "8", "ALL", D("8"), D("0.395")), BarSizeSpec("METRIC", "12", "ALL", D("12"), D("0.888")),
  BarSizeSpec("METRIC", "16", "ALL", D("16"), D("1.579")), BarSizeSpec("METRIC", "20", "ALL", D("20"), D("2.466")),
  BarSizeSpec("ASTM A615", "#4", "ALL", D("12.7"), D("0.994")),
)

SHAPES = (
  ShapeSpec("STRAIGHT", ("A",)), ShapeSpec("HOOKED", ("A",), (), 2),
  ShapeSpec("L_BAR", ("A", "B"), (90,)), ShapeSpec("STIRRUP_RECT", ("A", "B", "A", "B"), (90, 90, 90, 135, 135), 2, True),
)

MAIN = ReinforcementRuleSpec("ALL", "MAIN", "diameter_multiple", D("40"), {"standard_hook_d_multiple": 12},
  {"deduction_d_multiple": {"45": 1, "90": 2, "135": 3}}, None, {"stock_length_m": 12}, {})

LINK = ReinforcementRuleSpec("ALL", "STIRRUP", None, None, {"stirrup_hook_d_multiple": 10}, {"deduction_d_multiple": {"45": 1, "90": 2, "135": 3}}, None, {}, {})

EST_COL = ReinforcementRuleSpec("COLUMN", "ESTIMATE", None, None, {}, {}, None, {}, {"kg_per_m3": 200, "assumed_dia_mm": 12})
EST_SLAB = ReinforcementRuleSpec("SLAB", "ESTIMATE", None, None, {}, {}, None, {}, {"kg_per_m3": 90})

def _profile(*rules):
  return ResolvedRuleProfile(rule_set_id="t", code="T", immutable_version=1, content_hash=None, convention_code=None,
    conserves_volume=True, jurisdiction=None, province=None, standard_name=None, standard_edition=None,
    wall_measurement_method="centre_line", net_vs_gross_preference="net", preferred_units={}, tolerances={},
    reinforcement_rules=tuple(rules))

def _ctx():
  return CalculationContext(run_id=uuid4(), engine_version="t", fingerprint="t", convention_code=None,
    rule_set_code="T", rule_set_version=1, mappings=())

def _row(**kw):
  base = dict(id=uuid4(), import_id=uuid4(), row_no=1, member_mark="C1", mark="M1", role="COLUMN", shape_code="STRAIGHT",
    shape_params={}, designation="16", dia_mm=D("16"), grade=None, count=10, spacing_mm=None, cut_len_mm=D("3000"),
    declared_total_kg=None, level_id=None, matched_element_id=None, confidence=D("0.9"))
  base.update(kw)
  return RebarRowInput(**base)

def _solid(role="COLUMN", element=None):
  return Solid(id=uuid4(), element_id=element or uuid4(), ifc_type="IfcColumn", role=role, level_id=None, geometry_kind="EXTRUDED_PROFILE",
    classification_confidence=D("1"), confidence_factor=D("1"), gross_volume_m3=D("10"))

def _vol_row(solid, qty="10"):
  return LedgerEntry(solid_id=solid.id, element_id=solid.element_id, level_id=None, work_item_code="CON-RCC", quantity=D(qty),
    unit="m3", material_grade=None, confidence=D("1"), formula_code="SOLID_NET_VOLUME", trace={"formula_code": "SOLID_NET_VOLUME"})

def test_stirrup_cut_length_hand_check():
  cut, _ = cut_from_shape(SHAPES[3], {"A": 300, "B": 500}, D("8"), LINK)
  assert cut == D("1664")
  r = _row(shape_code="STIRRUP_RECT", shape_params={"A": 300, "B": 500}, cut_len_mm=None, dia_mm=D("8"), designation="8", count=100)
  c = compute_mark(r, SHAPES[3], SIZES, (MAIN, LINK), "COLUMN")
  assert c["total_len_m"] == D("166.400000") and c["total_kg"] == D("65.728000")

def test_hooked_main_bar_uses_main_hook_rule():
  cut, _ = cut_from_shape(SHAPES[1], {"A": 5000}, D("16"), MAIN)
  assert cut == D("5384")                                          

def test_missing_rule_or_param_raises():
  with pytest.raises(RebarError):
    cut_from_shape(SHAPES[2], {"A": 1000}, D("12"), MAIN)           
  with pytest.raises(RebarError):
    cut_from_shape(SHAPES[2], {"A": 1000, "B": 500}, D("12"), None)  

def test_lap_split_over_stock_length():
  stock, pieces, laps, lap, per_bar, w = split_laps(D("20000"), D("20"), MAIN)
  assert (stock, pieces, laps, lap, per_bar, w) == (D("12000"), 2, 1, D("800"), D("20800"), [])
  assert split_laps(D("11000"), D("20"), MAIN)[1:4] == (1, 0, None)   

def test_coupler_rule_adds_no_lap_length():
  rule = ReinforcementRuleSpec("ALL", "MAIN", "diameter_multiple", D("40"), {}, {}, None, {}, {}, stock_length_mm=D("12000"), use_couplers=True)
  _, pieces, laps, lap, per_bar, _ = split_laps(D("20000"), D("20"), rule)
  assert (pieces, laps, lap, per_bar) == (2, 1, D("0"), D("20000"))

def test_unit_weight_table_then_formula_fallback():
  assert unit_weight(SIZES, "#4", D("12.7"), None) == (D("0.994"), [])
  w, warn = unit_weight(SIZES, None, D("14"), None)                  
  assert w == D("1.2084") and warn == ["UNIT_WEIGHT_COMPUTED"]

def test_declared_weight_mismatch_flags_review():
  r = _row(count=10, cut_len_mm=D("3000"), declared_total_kg=D("100"))   
  c = compute_mark(r, SHAPES[0], SIZES, (MAIN,), "COLUMN")
  assert "DECLARED_WEIGHT_MISMATCH" in c["warnings"]

def test_schedule_rows_matched_and_unmatched():
  col = _solid("COLUMN")
  matched = _row(mark="M1", matched_element_id=col.element_id)
  loose = _row(mark="M1", member_mark="B2", role="BEAM", count=4, cut_len_mm=D("6000"))
  res = measure_rebar(_ctx(), _profile(MAIN, LINK), [col], [_vol_row(col)], RebarInputs((matched, loose), SHAPES, SIZES))
  assert res.stats["matched"] == 1 and res.stats["unmatched"] == 1 and len(res.solids) == 1
  assert res.solids[0].role == "REBAR_SCHEDULE"
  assert len(res.ledger) == 2 and all(e.unit == "kg" and e.source_kind == "SCHEDULE_IMPORT" for e in res.ledger)
  kg = {e.solid_id: e.quantity for e in res.ledger}
  assert kg[col.id] == D("47.370000")                                
  assert self_check_rebar(res.marks, res.ledger) == []

def test_estimate_for_uncovered_column_is_flagged():
  col = _solid("COLUMN")
  res = measure_rebar(_ctx(), _profile(EST_COL), [col], [_vol_row(col, "10")], RebarInputs((), SHAPES, SIZES))
  e = res.ledger[0]
  assert e.quantity == D("2000.000000") and e.source_kind == "ESTIMATE" and "STEEL_ESTIMATED" in e.warnings
  m = res.marks[0]
  assert m.provenance == "RULE_ESTIMATE" and m.review_status == "REVIEW_REQUIRED" and m.total_len_m == D("2252.252252")
  assert res.stats["tier3_kg"] == "2000.000000" and res.stats["tier2_kg"] == "0.000000"

def test_estimate_suppressed_by_family_and_by_element_coverage():
  c1, c2, slab = _solid("COLUMN"), _solid("COLUMN"), _solid("SLAB")
  rows = (_row(role="COLUMN", matched_element_id=None),)
  res = measure_rebar(_ctx(), _profile(MAIN, EST_COL, EST_SLAB), [c1, c2, slab],
    [_vol_row(c1), _vol_row(c2), _vol_row(slab, "20")], RebarInputs(rows, SHAPES, SIZES))
  assert res.stats["estimate_suppressed"] == 2                       
  est = [m for m in res.marks if m.provenance == "RULE_ESTIMATE"]
  assert len(est) == 1 and est[0].role == "SLAB" and est[0].total_kg == D("1800.000000")
  one = measure_rebar(_ctx(), _profile(MAIN, EST_COL), [c1, c2], [_vol_row(c1), _vol_row(c2)],
    RebarInputs((_row(role=None, matched_element_id=c1.element_id),), SHAPES, SIZES))
  assert [m.element_id for m in one.marks if m.provenance == "RULE_ESTIMATE"] == [c2.element_id]

def test_no_estimate_for_walls_or_without_rule():
  wall = _solid("WALL_EXTERNAL")
  res = measure_rebar(_ctx(), _profile(EST_COL), [wall], [_vol_row(wall)], RebarInputs((), SHAPES, SIZES))
  assert res.ledger == [] and res.marks == []

def test_row_with_unknown_shape_and_no_length_is_skipped_not_guessed():
  r = _row(shape_code="ZZZ", cut_len_mm=None)
  res = measure_rebar(_ctx(), _profile(MAIN), [], [], RebarInputs((r,), SHAPES, SIZES))
  assert res.ledger == [] and list(res.skipped.values()) == [1]

def test_duplicate_marks_on_one_element_get_unique_names():
  col = _solid("COLUMN")
  rows = (_row(row_no=1, mark="M1", matched_element_id=col.element_id), _row(row_no=2, mark="M1", matched_element_id=col.element_id))
  res = measure_rebar(_ctx(), _profile(MAIN), [col], [], RebarInputs(rows, SHAPES, SIZES))
  assert sorted(m.mark for m in res.marks) == ["M1", "M1-2"] and len(res.ledger) == 1

def test_role_family():
  assert [role_family(r) for r in ("COLUMN_STRUCTURAL", "LINTEL", "SLAB_ROOF", "FOOTING_ISOLATED", "WALL", "DOOR")] == \
    ["COLUMN", "BEAM", "SLAB", "FOOTING", "WALL", None]
