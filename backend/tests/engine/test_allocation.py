from decimal import Decimal
from app.engine.measure.models import CalculationContext, MappingInput, ModelElement
from uuid import uuid4
from app.engine.measure import engine as k

def _ctx(convention="FRAME_MONOLITHIC_A"):
  return CalculationContext(
    run_id=uuid4(), engine_version=k.ENGINE_VERSION, fingerprint="x", convention_code=convention,
    rule_set_code="PUNJAB_CSR", rule_set_version=1,
    mappings=(
      MappingInput("IfcColumn", "CONC-COL", Decimal("0.95")),
      MappingInput("IfcBeam", "CONC-BEAM", Decimal("0.95")),
      MappingInput("IfcSlab", "CONC-SLAB", Decimal("0.95")),
    ),
    convention_params={},
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

def _frame():
  c1 = _el("IfcColumn", "COLUMN", 300.0, 300.0, 3000.0, _rect(-150, -150, 150, 150), 0.0, 3000.0)
  c2 = _el("IfcColumn", "COLUMN", 300.0, 300.0, 3000.0, _rect(3850, -150, 4150, 150), 0.0, 3000.0)
  beam = _el("IfcBeam", "BEAM", 230.0, 450.0, 4000.0, _rect(0, -115, 4000, 115), 2550.0, 3000.0)
  slab = _el("IfcSlab", "SLAB", 4300.0, 1000.0, 125.0, _rect(-150, -500, 4150, 500), 2875.0, 3000.0)
  return c1, c2, beam, slab

def test_appendix_a_frame():
  c1, c2, beam, slab = _frame()
  res = k.run(_ctx(), [c1, c2, beam, slab])
  net = {r.element_id: r.quantity for r in res.ledger}
  assert net[c1.id] == Decimal("0.270000")
  assert net[beam.id] == Decimal("0.276575")
  assert net[slab.id] == Decimal("0.515000")
  solid_of = {s.element_id: s.id for s in res.solids}
  beam_deds = [d for d in res.deductions if d.from_solid_id == solid_of[beam.id]]
  assert sum(d.quantity for d in beam_deds if d.deduction_type == "EXTENT_TRIMMING") == Decimal("0.031050")
  assert sum(d.quantity for d in beam_deds if d.deduction_type == "OVERLAP_ALLOCATION") == Decimal("0.106375")

def test_without_convention_net_equals_gross():
  c1, c2, beam, slab = _frame()
  res = k.run(_ctx(convention=None), [c1, c2, beam, slab])
  assert res.deductions == []
  assert {r.element_id: r.quantity for r in res.ledger}[beam.id] == Decimal("0.414000")

def test_determinism():
  els, ctx = list(_frame()), _ctx()
  assert k.run(ctx, els) == k.run(ctx, els)