from __future__ import annotations
from app.engine.measure.profile import ResolvedRuleProfile, FinishRuleSpec, OpeningRuleSpec
from app.engine.measure.models import CalculationContext, SpaceInput, OpeningInput, SpaceFinishInput
from app.engine.measure.finishes import measure_finishes, resolve_finishes
from decimal import Decimal as D
from uuid import uuid4
from app.modules.drawings_boq.schedule_parsing import ScheduleParseError, canonicalize, parse_size, rows_from_table
import pytest

def _profile(rules, opening_rules=()):
  return ResolvedRuleProfile(
    rule_set_id="t", code="T", immutable_version=1, content_hash=None, convention_code=None, conserves_volume=True,
    jurisdiction=None, province=None, standard_name=None, standard_edition=None, wall_measurement_method="centre_line",
    net_vs_gross_preference="net", preferred_units={}, tolerances={}, opening_rules=tuple(opening_rules),
    finish_rules=tuple(rules))

def _ctx():
  return CalculationContext(run_id=uuid4(), engine_version="t", fingerprint="t", convention_code=None,
    rule_set_code="T", rule_set_version=1, mappings=())

RULES = [
  FinishRuleSpec("ALL", "FLOOR", "FIN-FLOOR", None),
  FinishRuleSpec("ALL", "SKIRTING", "FIN-SKIRT", None),
  FinishRuleSpec("ALL", "WALL", "FIN-PLASTER", None),
  FinishRuleSpec("ALL", "CEILING", "FIN-CEIL-PLASTER", None, deduct_openings=False),
  FinishRuleSpec("BATHROOM", "SKIRTING", "FIN-SKIRT", None, exclude=True),
  FinishRuleSpec("BATHROOM", "DADO", "FIN-DADO", D("2134")),
]

def _room(category="BEDROOM", boundary=(), finishes=(), area=True):
  return SpaceInput(
    id=uuid4(), level_id=None, number="R1", name=category.title(), category=category, is_external=False,
    net_floor_area_mm2=D("12000000") if area else None, gross_floor_area_mm2=D("12000000") if area else None,
    perimeter_mm=D("14000"), height_mm=D("2700"), geometry_kind="EXTRUDED_PROFILE",
    footprint=((0.0, 0.0), (4000.0, 0.0), (4000.0, 3000.0), (0.0, 3000.0)),
    boundary_element_ids=tuple(boundary), finishes=tuple(finishes))

def _door(centre=(1450.0, -115.0)):
  return OpeningInput(element_id=uuid4(), role="DOOR", host_element_id=None, host_thickness_mm=D("230"),
    width_mm=D("900"), height_mm=D("2100"), level_id=None, centre_mm=centre)

def _window():
  return OpeningInput(element_id=uuid4(), role="WINDOW", host_element_id=None, host_thickness_mm=D("230"),
    width_mm=D("1200"), height_mm=D("1200"), level_id=None, centre_mm=(2000.0, 3115.0))

def _by_item(result):
  return {e.work_item_code: e for e in result.ledger}

def test_bedroom_hand_check():
  door, win = _door(), _window()
  room = _room(boundary=(door.element_id, win.element_id))
  res = measure_finishes(_ctx(), _profile(RULES), [room], [door, win])
  q = _by_item(res)
  assert q["FIN-FLOOR"].quantity == D("12.000000")
  assert q["FIN-CEIL-PLASTER"].quantity == D("12.000000")           
  assert q["FIN-SKIRT"].quantity == D("13.100000")                  
  assert q["FIN-PLASTER"].quantity == D("34.470000")              
  assert q["FIN-FLOOR"].unit == "m2" and q["FIN-SKIRT"].unit == "m"
  assert "FIN-DADO" not in q
  assert not q["FIN-PLASTER"].warnings                            

def test_bathroom_excludes_skirting_and_adds_dado():
  door, win = _door(), _window()
  room = _room("BATHROOM", boundary=(door.element_id, win.element_id))
  q = _by_item(measure_finishes(_ctx(), _profile(RULES), [room], [door, win]))
  assert "FIN-SKIRT" not in q
  assert q["FIN-DADO"].quantity == D("27.986000")                   

def test_proximity_fallback_is_flagged_approximate():
  door = _door()
  room = _room(boundary=())                                         
  q = _by_item(measure_finishes(_ctx(), _profile(RULES), [room], [door]))
  assert q["FIN-SKIRT"].quantity == D("13.100000")
  assert "OPENING_ASSIGNMENT_APPROXIMATE" in q["FIN-SKIRT"].warnings

def test_no_position_means_no_opening_deduction():
  door = _door(centre=None)                                        
  q = _by_item(measure_finishes(_ctx(), _profile(RULES), [_room(boundary=())], [door]))
  assert q["FIN-SKIRT"].quantity == D("14.000000")                  

def test_explicit_finish_replaces_rule_defaults_for_that_surface():
  paint = SpaceFinishInput("WALL", "FIN-PAINT", None, "MANUAL", D("1"), "OK")
  room = _room(finishes=(paint,))
  resolved = {(f.surface, f.work_item_code) for f in resolve_finishes(room, RULES)}
  assert ("WALL", "FIN-PAINT") in resolved and ("WALL", "FIN-PLASTER") not in resolved

def test_room_without_area_is_skipped_not_zero():
  res = measure_finishes(_ctx(), _profile(RULES), [_room(area=False)], [])
  assert "FIN-FLOOR" not in _by_item(res) and res.skipped.get("space has no floor area") == 2

def test_small_opening_ignored_by_rule():
  rules = [OpeningRuleSpec("ALL", D("0"), D("0.5"), "IGNORE"), OpeningRuleSpec("ALL", D("0.5"), None, "DEDUCT")]
  small = OpeningInput(uuid4(), "WINDOW", None, D("230"), D("600"), D("600"), None, (2000.0, 3115.0))  
  room = _room(boundary=(small.element_id,))
  q = _by_item(measure_finishes(_ctx(), _profile(RULES, rules), [room], [small]))
  assert q["FIN-PLASTER"].quantity == D("37.800000")

def test_size_parsing():
  assert parse_size("900 x 2100") == (D("900"), D("2100"), None)
  w, h, _ = parse_size("3'-0\" x 7'-0\"")
  assert w == D("914.4") and h == D("2133.6")
  assert parse_size("0.9 x 2.1")[:2] == (D("900"), D("2100"))
  assert parse_size("nonsense") == (None, None, None)

def test_unit_canonicalization():
  cu, cq, _ = canonicalize("sft", D("100"))
  assert cu == "m2" and cq.quantize(D("0.0001")) == D("9.2903")
  assert canonicalize("ton", D("2"))[:2] == ("kg", D("2000.000000"))
  assert canonicalize("furlong", D("2")) == (None, None, None)

def test_long_and_wide_finish_schedules_agree():
  long_t = [["Room", "Surface", "Finish"], ["Bath 1", "Floor", "Tile"], ["Bath 1", "Wall", "Plaster"], ["Bath 1", "Wall", "Paint"]]
  wide_t = [["Room", "Floor", "Walls"], ["Bath 1", "Tile", "Plaster + Paint"]]
  a = [(r["location_text"], r["surface"], r["finish_name"]) for r in rows_from_table(long_t, "FINISH")]
  b = [(r["location_text"], r["surface"], r["finish_name"]) for r in rows_from_table(wide_t, "FINISH")]
  assert a == b

def test_wide_schedule_dado_height_and_empty_cells():
  t = [["Room", "Floor", "Ceiling", "Dado", "Dado Height"], ["Bath 1", "Tile", "-", "Tile", "2134"], ["Bed 1", "Tile", "N/A", "", ""]]
  rows = rows_from_table(t, "FINISH")
  assert [(r["location_text"], r["surface"]) for r in rows] == [("Bath 1", "FLOOR"), ("Bath 1", "DADO"), ("Bed 1", "FLOOR")]
  assert rows[1]["height_mm"] == D("2134")

def test_door_schedule_sizes_and_missing_header():
  t = [["Mark", "Description", "Unit", "Qty", "Size"], ["D1", "Main door", "nos", "4", "900 x 2100"]]
  r = rows_from_table(t, "DOOR")[0]
  assert (r["mark"], r["quantity"], r["width_mm"], r["height_mm"]) == ("D1", D("4"), D("900"), D("2100"))
  with pytest.raises(ScheduleParseError):
    rows_from_table([["foo", "bar"], ["1", "2"]], "DOOR")
