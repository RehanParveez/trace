from __future__ import annotations
import pytest
from decimal import Decimal
import dataclasses
import re
from types import SimpleNamespace
from app.modules.drawings_boq import ifc_types
from app.modules.drawings_boq.audit import summarize_audit
from app.modules.drawings_boq.ifc_reader import read_ifc
from tests.drawings_boq.ifc_fixtures import build_ifc2x3_minimal, build_villa_ifc

@pytest.fixture(scope="module")
def villa(tmp_path_factory):
  path = tmp_path_factory.mktemp("ifc") / "05_Stadium.ifc"
  build_villa_ifc(str(path))
  return read_ifc(str(path)), str(path)

def _by_name(result, name):
  matches = [e for e in result.elements if e.name == name]
  assert len(matches) == 1, f"{name}: {len(matches)} matches"
  return matches[0]

def _codes(element):
  return {i["code"] for i in element.issues}

def test_unit_scale_and_levels(villa):
  result, _ = villa
  assert result.schema == "IFC4"
  assert result.length_unit_scale == pytest.approx(0.001)
  assert [(l.name, l.elevation_mm) for l in result.levels] == [
    ("Ground", Decimal("0.0")),
    ("First", Decimal("3000.0")),
  ]
  assert result.model_issues == []

def test_no_duplicates_and_voids_excluded(villa):
  result, _ = villa
  step_ids = [e.step_id for e in result.elements]
  assert len(step_ids) == len(set(step_ids))
  assert "Opening 1" not in {e.name for e in result.elements}
  assert result.stats["excluded"] == {"IfcOpeningElement": 1}

def test_wall_from_qto_is_scaled_and_measured(villa):
  result, _ = villa
  wall = _by_name(result, "Wall A")
  assert wall.structural_role == "WALL_EXTERNAL"
  assert (wall.unit, wall.quantity, wall.quantity_source) == ("m3", Decimal("3.45"), "QTO")
  assert wall.raw_material_text == "Brick 230"
  assert (wall.length_mm, wall.height_mm, wall.thickness_mm) == (Decimal("5000.0"), Decimal("3000.0"), Decimal("230.0"))
  assert wall.geometry_kind == "EXTRUDED_PROFILE"
  assert wall.elevation_base_mm == Decimal("0.0") and wall.elevation_top_mm == Decimal("3000.0")

def test_geometry_derived_quantity_is_flagged(villa):
  result, _ = villa
  wall = _by_name(result, "Wall B")
  assert wall.quantity_source == "GEOMETRY"
  assert float(wall.quantity) == pytest.approx(4 * 0.2 * 3)
  assert "QUANTITY_FROM_GEOMETRY" in _codes(wall)
  assert wall.is_generic_fallback and "MISSING_MATERIAL" in _codes(wall)
  assert wall.status == "WARNING"

def test_slab_dimensions_and_level(villa):
  result, _ = villa
  slab = _by_name(result, "Slab 1")
  levels = {l.global_id: l.name for l in result.levels}
  assert levels[slab.level_global_id] == "First"
  assert slab.thickness_mm == Decimal("125.0")
  assert (slab.length_mm, slab.width_mm) == (Decimal("5000.0"), Decimal("4000.0"))
  assert float(slab.quantity) == pytest.approx(4 * 5 * 0.125)

def test_column_extruded_profile(villa):
  result, _ = villa
  column = _by_name(result, "Column C1")
  assert column.structural_role == "COLUMN"
  assert column.height_mm == Decimal("3000.0")
  assert column.width_mm == Decimal("300.0")
  assert float(column.quantity) == pytest.approx(0.3 * 0.3 * 3)

def test_doors_and_windows_are_counts(villa):
  result, _ = villa
  door = _by_name(result, "Door D1")
  assert (door.unit, door.quantity, door.quantity_source) == ("nos", Decimal("1"), "COUNT")
  assert (door.width_mm, door.height_mm) == (Decimal("900.0"), Decimal("2100.0"))
  assert door.status == "VALID"
  assert _by_name(result, "Window W1").unit == "nos"

def test_predefined_type_roles(villa):
  result, _ = villa
  assert _by_name(result, "Shear 1").structural_role == "WALL_SHEAR"
  assert _by_name(result, "Tiles").structural_role == "FLOOR_FINISH"

def test_proxy_name_heuristic_is_whole_word(villa):
  result, _ = villa
  beam = _by_name(result, "Beam B1")
  assert (beam.structural_role, beam.classification_source) == ("BEAM", "NAME_HEURISTIC")
  assert beam.classification_confidence < Decimal("0.6")
  assert "LOW_CONFIDENCE_CLASSIFICATION" in _codes(beam)
  assert beam.status == "INVALID" 
  deck = _by_name(result, "Composite deck")
  assert deck.structural_role == "UNKNOWN" 
  assert "UNCLASSIFIED_ELEMENT" in _codes(deck)

def test_mep_elements(villa):
  result, _ = villa
  pipe = _by_name(result, "Pipe 1")
  assert (pipe.structural_role, pipe.discipline, pipe.unit) == ("PIPE", "MEP_PLUMBING", "m")
  assert pipe.quantity == Decimal("3.0")
  wc = _by_name(result, "WC 1")
  assert (wc.structural_role, wc.unit, wc.quantity) == ("SANITARY_FIXTURE", "nos", Decimal("1"))
  assert _by_name(result, "Light 1").discipline == "MEP_ELECTRICAL"

def test_rebar_is_stored_not_invalid(villa):
  result, _ = villa
  bar = _by_name(result, "Bar 1")
  assert bar.structural_role == "REBAR"
  assert "STORED_ONLY" in _codes(bar)
  assert bar.status != "INVALID"

def test_reader_is_deterministic(villa):
  result, path = villa
  again = read_ifc(path)
  assert dataclasses.asdict(result) == dataclasses.asdict(again)

def test_ifc2x3_basequantities(tmp_path):
  path = tmp_path / "old.ifc"
  build_ifc2x3_minimal(str(path))
  result = read_ifc(str(path))
  assert result.length_unit_scale == pytest.approx(1.0)
  wall = result.elements[0]
  assert wall.ifc_type == "IfcWallStandardCase" and wall.structural_role == "WALL"
  assert (wall.unit, wall.quantity, wall.quantity_source) == ("m3", Decimal("2.0"), "QTO")
  assert wall.length_mm == Decimal("4000.0") and wall.thickness_mm == Decimal("200.0")

def test_audit_score_is_percentage_of_valid():
  def row(status, issues=()):
    return SimpleNamespace(
      id=f"id-{status}", normalization_status=status, normalization_issues=list(issues),
      structural_role="WALL", geometry_kind="EXTRUDED_PROFILE",
    )

  rows = [row("VALID"), row("VALID"), row("WARNING", [{"code": "MISSING_MATERIAL", "severity": "warning", "message": "x"}]),
    row("INVALID", [{"code": "NO_QUANTITY", "severity": "error", "message": "y"}])]
  summary = summarize_audit(rows, [{"code": "NO_STOREYS", "severity": "warning", "message": "z"}])
  assert summary["overall_score"] == Decimal("50.00")
  assert summary["missing_material_count"] == 1 and summary["zero_quantity_count"] == 1
  assert summary["issues"][0]["code"] == "NO_QUANTITY" 
  assert summary["extra_stats"]["blocking_error_count"] == 1
  assert summarize_audit([])["overall_score"] == Decimal("0.00")

def test_audit_scales_to_large_models():
  rows = [
    SimpleNamespace(id=i, normalization_status="WARNING", normalization_issues=[{"code": "MISSING_MATERIAL", "severity": "warning", "message": ""}],
      structural_role="WALL", geometry_kind=None)
    for i in range(5000)
  ]
  summary = summarize_audit(rows)
  assert summary["overall_score"] == Decimal("0.00")
  assert len(summary["issues"][0]["element_ids"]) == 50 

def _all_roles():
  return set(ifc_types.ROLE_BY_IFC_TYPE.values()) | set(ifc_types.PREDEFINED_TYPE_ROLE_OVERRIDES.values())

def test_every_role_has_a_discipline():
  missing = {r for r in _all_roles() - {"UNKNOWN"} if r not in ifc_types.DISCIPLINE_BY_ROLE}
  assert not missing, f"roles without a discipline: {sorted(missing)}"

def test_role_families_do_not_overlap():
  assert not (ifc_types.COUNT_ROLES & ifc_types.LENGTH_ROLES), sorted(ifc_types.COUNT_ROLES & ifc_types.LENGTH_ROLES)
  assert not (ifc_types.COUNT_ROLES & ifc_types.AREA_ROLES)

def test_every_mep_role_is_counted_or_linear():
  mep = {r for r, d in ifc_types.DISCIPLINE_BY_ROLE.items() if d.startswith("MEP_")}
  loose = mep - ifc_types.COUNT_ROLES - ifc_types.LENGTH_ROLES
  assert not loose, f"MEP roles with no quantity family: {sorted(loose)}"

def test_keyword_order_has_no_shadowed_entries():
  patterns = [(kw, re.compile(rf"(?<![a-z]){re.escape(kw)}(?:s|es)?(?![a-z])")) for kw, _ in ifc_types.NAME_KEYWORD_ROLES]
  for i, (kw_i, _) in enumerate(patterns):
    for kw_j, pat_j in patterns[:i]:
      assert not pat_j.search(f" {kw_i} "), f"'{kw_i}' is unreachable: '{kw_j}' matches it first"

def test_keyword_roles_exist():
  known = _all_roles() | set(ifc_types.DISCIPLINE_BY_ROLE)
  unknown = {role for _, role in ifc_types.NAME_KEYWORD_ROLES if role not in known}
  assert not unknown, sorted(unknown)

def test_beams_prefer_volume():
  for role in ("BEAM", "LINTEL"):
    order = ifc_types.QUANTITY_KIND_ORDER_BY_ROLE.get(role, ifc_types.DEFAULT_QUANTITY_KIND_ORDER)
    assert order[0] == "volume", f"{role} measures {order[0]} first; concrete beams are priced per volume"