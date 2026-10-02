from decimal import Decimal
from backend.app.engine.measure.models import CalculationContext, MappingInput, ModelElement
from uuid import uuid4
from app.engine.measure import engine as k

def _ctx(run_id=None):
  return CalculationContext(
    run_id=run_id or uuid4(), engine_version=k.ENGINE_VERSION, fingerprint="x",
    convention_code=None, rule_set_code="PUNJAB_CSR", rule_set_version=1,
    mappings=(MappingInput("IfcColumn", "CONC-COL", Decimal("0.95")),),
  )

def _column():
  return ModelElement(
    id=uuid4(), ifc_type="IfcColumn", role="COLUMN", level_id=None,
    geometry_kind="EXTRUDED_PROFILE",
    profile={"kind": "RECT", "x_dim": 300.0, "y_dim": 300.0},
    placement={"depth_mm": 3000.0}, volume_mm3=None, bbox_min_mm=None, bbox_max_mm=None,
    classification_confidence=Decimal("0.95"), normalization_status="VALID",
  )

def test_column_gross_volume():
  res = k.run(_ctx(), [_column()])
  assert res.ledger[0].quantity == Decimal("0.270000")
  assert res.ledger[0].unit == "m3"

def test_determinism():
  els, rid = [_column(), _column()], uuid4()
  assert k.run(_ctx(rid), els) == k.run(_ctx(rid), els)