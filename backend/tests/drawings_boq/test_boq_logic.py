from app.modules.drawings_boq import boq_logic as L
from uuid import uuid4
from decimal import Decimal

def _line(code="CONC-COL", qty="0.27", unit="m3", conf="0.95", warnings=()):
  return L.LedgerLine(id=uuid4(), solid_id=uuid4(), element_id=uuid4(), level_id=None, work_item_code=code,
    quantity=Decimal(qty), unit=unit, material_grade=None, confidence=Decimal(conf), warnings=warnings)

WI = {"CONC-COL": L.WorkItemInfo("CONC-COL", "Concrete column", "cft")}

def test_catalog_cft_is_not_a_mismatch_and_sets_display_unit():
  drafts, unknown, mismatch = L.aggregate([_line(), _line(qty="0.30")], scope="building", preferred_units={},
    work_items=WI, waste_for=lambda mc: Decimal("1.03"))
  assert not unknown and not mismatch
  d = drafts[0]
  assert d.unit == "cft" and d.net_quantity == L.q4(Decimal("0.57") * Decimal("35.3146667"))

def test_adjustments_replace_then_delta():
  qty = L.compute_quantity(Decimal("10"), [L.AdjustmentLine("REPLACE", Decimal("12")), L.AdjustmentLine("DELTA", Decimal("-1.5"))])
  assert qty == Decimal("10.5000")

def test_snapshot_hash_is_stable_and_ignores_ids():
  def items():
    return [{"id": uuid4(), "item_key": "A|m3|-|-", "work_item_code": "A", "material_name": "A", "item_type": "MATERIAL",
      "unit": "m3", "quantity": Decimal("2"), "unit_rate": Decimal("100"), "ledger_row_count": 1}]
  _, t1, h1 = L.build_snapshot(items(), {"v": 1})
  _, t2, h2 = L.build_snapshot(items(), {"v": 1})
  assert h1 == h2 and t1["grand"] == "200.00"

def test_low_confidence_flags_review():
  drafts, _, _ = L.aggregate([_line(conf="0.4")], scope="building", preferred_units={}, work_items=WI,
    waste_for=lambda mc: Decimal("1"))
  assert drafts[0].review_status == "REVIEW_REQUIRED"