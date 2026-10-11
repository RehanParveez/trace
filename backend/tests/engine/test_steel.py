from __future__ import annotations
from app.engine.measure.models import MappingInput, CalculationContext, ModelElement
from decimal import Decimal as D
from app.engine.measure import engine as k
from app.engine.measure.steel import STEEL_PILE_CODE, STEEL_SECTION_CODE, steel_check
import pytest
from uuid import uuid4
from dataclasses import replace

MAPPINGS = (
  MappingInput("IfcSlab", "CON-RCC", D("0.95")),
  MappingInput("IfcColumn", "CON-RCC", D("0.95")),
  MappingInput("IfcBeam", "CON-RCC", D("0.95")),
)

def _ctx(convention=None):
  return CalculationContext(run_id=uuid4(), engine_version=k.ENGINE_VERSION, fingerprint="x", convention_code=convention,
    rule_set_code="PUNJAB_CSR", rule_set_version=1, mappings=MAPPINGS)

def _el(ifc_type="IfcBeam", role="BEAM", kind="BOX_ONLY", volume_m3=None, status="INVALID", material="STEEL", bbox=None,
    profile=None, placement=None, confidence="0.95", basis=None):
  return ModelElement(
    id=uuid4(), ifc_type=ifc_type, role=role, level_id=None, geometry_kind=kind, profile=profile, placement=placement,
    volume_mm3=D(str(volume_m3)) * D("1e9") if volume_m3 is not None else None,
    bbox_min_mm=bbox[0] if bbox else None, bbox_max_mm=bbox[1] if bbox else None,
    classification_confidence=D(confidence), normalization_status=status, material_class=material, material_basis=basis)

UB = dict(volume_m3="0.06548853642", bbox=((0, 0, 3396.6), (12155.6, 2158.3, 3700.0)))
PIPE_PILE = dict(ifc_type="IfcSlab", role="PILE", volume_m3="0.75396", bbox=((0, 0, -7200), (400, 400, -1200)))

def test_flagged_steel_beam_is_weighed_not_rejected():
  res = k.run(_ctx(), [_el(**UB)])
  assert res.rejected == []
  (row,) = res.ledger
  assert row.work_item_code == STEEL_SECTION_CODE and row.unit == "kg"
  assert row.quantity == D("514.088650") and row.confidence == D("0.7650")

def test_pile_is_billed_by_length_never_by_volume():
  res = k.run(_ctx(), [_el(**PIPE_PILE) for _ in range(3)])
  assert all(r.work_item_code == STEEL_PILE_CODE and r.unit == "m" and r.quantity == D("6.000000") for r in res.ledger)
  assert res.stats["steel"]["pile_length_m"] == "18.000000" and res.stats["steel"]["sections_kg"] == "0.000000"

@pytest.mark.parametrize("volume", [None, D("NaN"), D("0")])
def test_steel_without_a_usable_volume_is_not_weighed(volume):
  e = replace(_el(**UB), volume_mm3=volume)
  res = k.run(_ctx(), [e])
  assert res.ledger == [] and res.stats["steel"]["not_measured"] == 1

def test_non_steel_invalid_elements_and_pile_caps_stay_concrete():
  wall = _el(ifc_type="IfcWall", role="WALL", kind="QTO_ONLY", volume_m3="5")
  res = k.run(_ctx(), [_el(material=None, **UB), wall])
  assert {r.code for r in res.rejected} == {"INVALID_ELEMENT"} and res.ledger == []
  cap = _el(ifc_type="IfcFooting", role="PILE_CAP", kind="QTO_ONLY", volume_m3="3", status="VALID", material=None)
  assert k.run(_ctx(), [cap]).stats["steel"]["elements"] == 0

def test_steel_never_takes_part_in_concrete_allocation():
  prof = {"kind": "RECT", "x_dim": 400, "y_dim": 400}
  plc = {"depth_mm": 3000.0, "plan_mm": [[0, 0], [400, 0], [400, 400], [0, 400]], "z_min_mm": 0, "z_max_mm": 3000, "vertical": True,
    "origin_mm": [0, 0, 0], "extrusion_dir": [0, 0, 1]}
  common = dict(ifc_type="IfcColumn", role="COLUMN", kind="EXTRUDED_PROFILE", volume_m3="0.48", profile=prof, placement=plc, status="VALID")
  res = k.run(_ctx("FRAME_MONOLITHIC_A"), [_el(material=None, **common), _el(material="STEEL", **common)])
  by_code = {r.work_item_code: r for r in res.ledger}
  assert by_code["CON-RCC"].quantity == D("0.480000") and by_code[STEEL_SECTION_CODE].quantity == D("3768.000000")

def test_self_check_catches_a_wrong_steel_quantity():
  res = k.run(_ctx(), [_el(**UB), _el(**PIPE_PILE)])
  assert steel_check(res.solids, res.ledger) == []
  broken = [replace(r, quantity=r.quantity + D("1")) for r in res.ledger]
  with pytest.raises(k.InvariantViolation):
    k.self_check(res.solids, broken)

def test_duplicate_steel_is_flagged_but_still_counted():
  res = k.run(_ctx(), [_el(**UB), _el(**UB)])
  assert len(res.ledger) == 2 and res.stats["steel"]["duplicates_suspected"] == 1