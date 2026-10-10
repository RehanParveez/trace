import pytest
from pydantic import ValidationError
from app.modules.running_bills.schemas import RunningBillRecordCollectionRequest
from decimal import Decimal
from datetime import date
from app.modules.running_bills.service import RunningBillService

def test_collection_needs_some_amount():
  with pytest.raises(ValidationError):
    RunningBillRecordCollectionRequest(amount=Decimal("0"), client_wht_amount=Decimal("0"), collection_date=date(2026, 10, 1))

def test_collection_accepts_wht_only():
  req = RunningBillRecordCollectionRequest(amount=Decimal("0"), client_wht_amount=Decimal("500"), collection_date=date(2026, 10, 1))
  assert req.client_wht_amount == Decimal("500")

def test_collection_rejects_negative():
  with pytest.raises(ValidationError):
    RunningBillRecordCollectionRequest(amount=Decimal("-1"), client_wht_amount=Decimal("10"), collection_date=date(2026, 10, 1))

def test_notes_gain_revision_warning_only_when_revised():
  assert RunningBillService._notes_with_revisions("hello", []) == "hello"
  assert RunningBillService._notes_with_revisions(None, []) is None
  merged = RunningBillService._notes_with_revisions("hello", ["Brick work"])
  assert merged.startswith("hello\n") and "Brick work" in merged
  assert "Brick work" in RunningBillService._notes_with_revisions(None, ["Brick work"])

def test_retention_cap_uses_whole_contract_value():
  this_period, cumulative = RunningBillService._calculate_retention(
    gross_this_period=Decimal("1000000"), retention_percentage=Decimal("10"), retention_cap_percentage=Decimal("5"),
    previous_retention_cumulative=Decimal("0"), contract_total_value=Decimal("10000000"),
  )
  assert this_period == Decimal("100000.00") and cumulative == Decimal("100000.00") 