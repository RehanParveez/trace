from app.engine.measure.models import CalculationContext, MappingInput, ModelElement, ScheduleLineInput
from decimal import Decimal
from uuid import uuid4
from app.engine.measure import engine as k
from app.engine.measure.finishes import schedule_lines_ledger
from app.engine.measure.profile import FinishRuleSpec, ResolvedRuleProfile

def _ctx(convention="FRAME_MONOLITHIC_A"):
  return CalculationContext(
    run_id=uuid4(), engine_version=k.ENGINE_VERSION, fingerprint="x", convention_code=convention,
    rule_set_code="PUNJAB_CSR", rule_set_version=1,
    mappings=(
      MappingInput("IfcColumn", "CONC-COL", Decimal("0.95")),
      MappingInput("IfcBeam", "CONC-BEAM", Decimal("0.95")),
      MappingInput("IfcSlab", "CONC-SLAB", Decimal("0.95")),
      MappingInput("IfcStair", "CONC-STAIR", Decimal("0.95")),
    ),
  )

def _rect(x0, y0, x1, y1):
  return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

def _el(ifc_type, role, xd, yd, depth, plan, z0, z1):
  return ModelElement(
    id=uuid4(), ifc_type=ifc_type, role=role, level_id=None, geometry_kind="EXTRUDED_PROFILE",
    profile={"kind": "RECT", "x_dim": xd, "y_dim": yd},
    placement={"depth_mm": depth, "plan_mm": plan, "z_min_mm": z0, "z_max_mm": z1},
    volume_mm3=None, bbox_min_mm=None, bbox_max_mm=None,
    classification_confidence=Decimal("0.95"), normalization_status="VALID",
  )

def _rows(res, el):
  return [r for r in res.ledger if r.element_id == el.id]

def test_appendix_a_unchanged():
  c1 = _el("IfcColumn", "COLUMN", 300.0, 300.0, 3000.0, _rect(-150, -150, 150, 150), 0.0, 3000.0)
  c2 = _el("IfcColumn", "COLUMN", 300.0, 300.0, 3000.0, _rect(3850, -150, 4150, 150), 0.0, 3000.0)
  beam = _el("IfcBeam", "BEAM", 230.0, 450.0, 4000.0, _rect(0, -115, 4000, 115), 2550.0, 3000.0)
  slab = _el("IfcSlab", "SLAB", 4300.0, 1000.0, 125.0, _rect(-150, -500, 4150, 500), 2875.0, 3000.0)
  res = k.run(_ctx(), [c1, c2, beam, slab])
  net = {r.element_id: r.quantity for r in res.ledger}
  assert net[c1.id] == Decimal("0.270000") and net[beam.id] == Decimal("0.276575") and net[slab.id] == Decimal("0.515000")
  assert all("NOT_ALLOCATED" not in r.warnings for r in res.ledger)

def test_sloped_prism_is_not_allocated_instead_of_wrong():
  slab = _el("IfcSlab", "SLAB_ROOF", 5000.0, 4000.0, 150.0, _rect(0, 0, 5000, 4000), 3000.0, 4495.0)
  beam = _el("IfcBeam", "BEAM", 230.0, 450.0, 4000.0, _rect(4885, 0, 5115, 4000), 4045.0, 4495.0)
  res = k.run(_ctx(), [slab, beam])
  (b,) = _rows(res, beam)
  assert b.quantity == Decimal("0.414000")       
  assert "NOT_ALLOCATED" in _rows(res, slab)[0].warnings

def test_unranked_role_is_flagged():
  slab = _el("IfcSlab", "SLAB", 3000.0, 3000.0, 150.0, _rect(0, 0, 3000, 3000), 2850.0, 3000.0)
  stair = _el("IfcStair", "STAIR", 1000.0, 3000.0, 1000.0, _rect(0, 0, 1000, 3000), 2000.0, 3000.0)
  res = k.run(_ctx(), [slab, stair])
  assert "NOT_ALLOCATED" in _rows(res, stair)[0].warnings

def test_duplicate_column_is_kept_and_flagged():
  a = _el("IfcColumn", "COLUMN", 300.0, 300.0, 3000.0, _rect(0, 0, 300, 300), 0.0, 3000.0)
  b = _el("IfcColumn", "COLUMN", 300.0, 300.0, 3000.0, _rect(0, 0, 300, 300), 0.0, 3000.0)
  res = k.run(_ctx(), [a, b])
  rows = sorted((r for r in res.ledger), key=lambda r: r.quantity)
  assert [r.quantity for r in rows] == [Decimal("0"), Decimal("0.270000")]
  assert "DUPLICATE_SOLID" in rows[0].warnings

def test_no_convention_marks_not_allocated():
  col = _el("IfcColumn", "COLUMN", 300.0, 300.0, 3000.0, _rect(0, 0, 300, 300), 0.0, 3000.0)
  res = k.run(_ctx(convention=None), [col])
  assert "NOT_ALLOCATED" in res.ledger[0].warnings

def test_profile_fingerprint_with_finish_rules():
  def prof(rule_id):
    return ResolvedRuleProfile(
      rule_set_id="r", code="T", immutable_version=1, content_hash=None, convention_code="FRAME_MONOLITHIC_A",
      conserves_volume=True, jurisdiction=None, province=None, standard_name=None, standard_edition=None,
      wall_measurement_method="centre_line", net_vs_gross_preference="net", preferred_units={}, tolerances={},
      finish_rules=(FinishRuleSpec("ALL", "FLOOR", "FIN-FLOOR", None, id=rule_id),))
  a, b = prof("11111111-1111-1111-1111-111111111111"), prof("22222222-2222-2222-2222-222222222222")
  assert a.fingerprint() == a.fingerprint()                     
  assert a.content_fingerprint() == b.content_fingerprint()      

def test_schedule_lines_warnings():
  ln = ScheduleLineInput(id=uuid4(), import_id=uuid4(), row_no=1, schedule_kind="FINISH", description="Tiles",
    mark=None, work_item_code="FIN-FLOOR", unit="m2", quantity=Decimal("180"), confidence=Decimal("0.4"),
    level_id=None, space_id=None, raw_text="Tiles all rooms 180 m2")
  res = schedule_lines_ledger(_ctx(), [ln], frozenset({"FIN-FLOOR"}))
  assert set(res.ledger[0].warnings) == {"SCHEDULE_OVERLAPS_MODEL", "SCHEDULE_LOW_CONFIDENCE"}