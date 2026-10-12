from __future__ import annotations
from dataclasses import replace
from decimal import Decimal as D
from uuid import uuid4
import pytest
from app.engine.measure import engine as k
from app.engine.measure import spec as sp
from app.engine.measure.models import CalculationContext, MappingInput, ModelElement

MAPPINGS = (
  MappingInput("IfcColumn", "CON-RCC", D("0.95")),
  MappingInput("IfcWall", "MAS-BRICK", D("0.9")),
  MappingInput("IfcWallStandardCase", "MAS-BRICK", D("0.9")),
)

def _ctx(spec_mode=True, run_id=None):
  return CalculationContext(run_id=run_id or uuid4(), engine_version=k.ENGINE_VERSION, fingerprint="x", convention_code=None,
    rule_set_code="T", rule_set_version=1, mappings=MAPPINGS, spec_mode=spec_mode)

def _column(text="Reinforced Concrete 1:2:4"):
  return ModelElement(id=uuid4(), ifc_type="IfcColumn", role="COLUMN", level_id=None, geometry_kind="EXTRUDED_PROFILE",
    profile={"kind": "RECT", "x_dim": 300.0, "y_dim": 300.0}, placement={"depth_mm": 3000.0}, volume_mm3=None,
    bbox_min_mm=None, bbox_max_mm=None, classification_confidence=D("0.95"), normalization_status="VALID",
    material_text=text)

def _wall(thickness=228.6, text="Burnt Clay Brick Masonry", material_class="MASONRY", role="WALL"):
  return ModelElement(id=uuid4(), ifc_type="IfcWall", role=role, level_id=None, geometry_kind="EXTRUDED_PROFILE",
    profile={"kind": "RECT", "x_dim": 4000.0, "y_dim": 228.6}, placement={"depth_mm": 3000.0}, volume_mm3=None,
    bbox_min_mm=None, bbox_max_mm=None, classification_confidence=D("0.95"), normalization_status="VALID",
    material_class=material_class, material_text=text, thickness_mm=D(str(thickness)) if thickness is not None else None)

@pytest.mark.parametrize("text,expected", [
  ("Reinforced Concrete 1:2:4", "1:2:4"), ("Reinforced Concrete 1:1.5:3", "1:1.5:3"), ("Concrete M20", "M20"),
  ("Concrete - M 25", "M25"), ("Concrete C25/30", "C25/30"), ("RCC 3000 psi", "3000psi"),
  ("Concrete M20 (1:1.5:3)", "M20"), ("Concrete", None), (None, None), ("Brick 1:6", None)])
def test_concrete_grade(text, expected):
  assert sp.concrete_grade(text) == expected

@pytest.mark.parametrize("text,expected", [
  ("Cement mortar 1:6", "1:6"), ("CM 1:4.0", "1:4"), ("Brick masonry (1:5)", "1:5"),
  ("Reinforced Concrete 1:2:4", None), ("Burnt Clay Brick Masonry", None), (None, None)])
def test_mortar_ratio(text, expected):
  assert sp.mortar_ratio(text) == expected

@pytest.mark.parametrize("mm,expected", [(228.6, 230), (114.3, 115), (230, 230), (112.5, 115), (0, None), (None, None), (-5, None)])
def test_round_thickness(mm, expected):
  assert sp.round_thickness(mm) == expected

def test_thickness_falls_back_to_profile_and_is_marked():
  w = replace(_wall(thickness=None), thickness_mm=None)
  s = sp.derive_spec(w)
  assert s["thickness_mm"] == 230 and s["basis"]["thickness_mm"] == "profile"

def test_unknown_wall_material_is_assumed_masonry():
  s = sp.derive_spec(_wall(material_class=None, text=None))
  assert s["kind"] == "MASONRY" and s["basis"]["material"] == "assumed_masonry"

def test_spec_key_and_label():
  s = sp.derive_spec(_wall(text="Brick masonry mortar 1:6"))
  assert sp.spec_key(s) == "t230" and sp.spec_grade(s) == "1:6"
  assert sp.describe_spec(s) == "230 mm thick, mortar 1:6"
  assert sp.spec_key(sp.derive_spec(_column())) is None

def test_flag_off_changes_nothing():
  els = [_column(), _wall()]
  rid = uuid4()
  off = k.run(_ctx(False, rid), els)
  assert all(r.material_grade is None and r.spec is None and r.spec_key is None for r in off.ledger)
  assert off.stats["spec"] == {"enabled": False}
  assert not any(w.startswith("SPEC_") for r in off.ledger for w in r.warnings)

def test_flag_on_tags_concrete_and_masonry():
  res = k.run(_ctx(), [_column(), _wall(text="Burnt Clay Brick Masonry")])
  rows = {r.work_item_code: r for r in res.ledger}
  col, wall = rows["CON-RCC"], rows["MAS-BRICK"]
  assert col.material_grade == "1:2:4" and col.spec_key is None and "SPEC_MIX_MISSING" not in col.warnings
  assert wall.spec_key == "t230" and wall.material_grade is None
  assert "SPEC_MORTAR_MISSING" in wall.warnings and "SPEC_THICKNESS_MISSING" not in wall.warnings
  assert wall.trace["inputs"]["spec"]["thickness_mm"] == 230
  assert res.stats["spec"]["masonry_rows"] == 1 and res.stats["spec"]["mortar_missing"] == 1

def test_quantities_are_identical_with_and_without_spec():
  els, rid = [_column(), _wall()], uuid4()
  on, off = k.run(_ctx(True, rid), els), k.run(_ctx(False, rid), els)
  assert [(r.work_item_code, r.quantity, r.unit) for r in on.ledger] == [(r.work_item_code, r.quantity, r.unit) for r in off.ledger]

def test_missing_mix_and_thickness_are_flagged():
  res = k.run(_ctx(), [_column(text="Concrete"), replace(_wall(thickness=None, text=None, material_class=None), profile=None, geometry_kind="QTO_ONLY", volume_mm3=D("5000000000"))])
  rows = {r.work_item_code: r for r in res.ledger}
  assert "SPEC_MIX_MISSING" in rows["CON-RCC"].warnings
  assert rows["MAS-BRICK"].spec_key is None and "SPEC_THICKNESS_MISSING" in rows["MAS-BRICK"].warnings

def test_two_thicknesses_get_two_spec_keys():
  res = k.run(_ctx(), [_wall(thickness=228.6), _wall(thickness=114.3)])
  assert sorted(r.spec_key for r in res.ledger) == ["t115", "t230"]

def test_concrete_wall_is_billed_as_concrete_with_a_mix():
  mappings = (*MAPPINGS, MappingInput("IfcSlab", "CON-RCC", D("0.95")))
  ctx = replace(_ctx(), mappings=mappings)
  res = k.run(ctx, [_wall(text="Reinforced Concrete M25", material_class="CONCRETE", role="WALL_SHEAR")])
  row = res.ledger[0]
  assert row.work_item_code == "CON-RCC" and row.material_grade == "M25" and row.spec_key is None

def test_self_check_catches_a_spec_key_that_drifted():
  res = k.run(_ctx(), [_wall()])
  broken = [replace(r, spec_key="t999") for r in res.ledger]
  with pytest.raises(k.InvariantViolation):
    k.self_check(res.solids, broken)

def test_determinism_with_spec():
  els, rid = [_column(), _wall()], uuid4()
  assert k.run(_ctx(True, rid), els) == k.run(_ctx(True, rid), els)