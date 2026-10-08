from __future__ import annotations
from datetime import date
from decimal import Decimal as D
from types import SimpleNamespace as NS
import pytest
from app.modules.drawings_boq import boq_logic as logic
from app.modules.drawings_boq.pricing import pricing_logic as pl

pytestmark = pytest.mark.unit

def _e(unit, rate, id_="a"):
  return NS(unit=unit, rate=D(str(rate)), id=id_)

def test_unit_aliases_fold_to_table_spelling():
  assert logic.normalise_unit(" CUM ") == "m3"
  assert logic.normalise_unit("Sq.Ft") == "sft"
  assert logic.normalise_unit("unit") == "nos"
  assert logic.normalise_unit("each") == "nos"
  assert logic.normalise_unit("bag") == "bag"      

def test_convert_rate_handles_aliases_and_rejects_cross_family():
  assert logic.convert_rate(D("18500"), "cum", "m3") == D("18500.00")
  assert logic.convert_rate(D("12"), "unit", "nos") == D("12.00")
  assert logic.convert_rate(D("100"), "sft", "m2") == D("1076.39")     
  assert logic.convert_rate(D("100"), "m3", "sft") is None

def test_pl_convert_same_unit_is_identity_even_for_unknown_units():
  assert pl.convert(D("5.005"), "bag", "BAG") == D("5.01")
  assert pl.convert(D("5"), "bag", "kg") is None

def test_match_unit_prefers_exact_then_convertible():
  entries = [_e("cft", 650, "1"), _e("m3", 22000, "2")]
  m, bad = pl.match_unit(entries, "m3")
  assert (m.entry.unit, m.rate, m.converted, bad) == ("m3", D("22000.00"), False, False)
  m, bad = pl.match_unit([_e("cft", 650)], "m3")
  assert m.converted and m.rate == D("22954.53") and not bad         
  m, bad = pl.match_unit([_e("kg", 200)], "m3")
  assert m is None and bad is True
  m, bad = pl.match_unit([], "m3")
  assert m is None and bad is False

def _esc(scope, eff, factor):
  return NS(trade_scope=scope, effective_from=eff, factor=D(str(factor)), id=f"{scope}{eff}")

def test_escalation_none_applies_before_first_date():
  f, e = pl.escalation_for([_esc("ALL", date(2026, 7, 1), "1.05")], None, date(2026, 6, 30))
  assert f == D("1") and e is None

def test_escalation_latest_date_wins_within_scope():
  rows = [_esc("ALL", date(2026, 1, 1), "1.03"), _esc("ALL", date(2026, 7, 1), "1.08")]
  assert pl.escalation_for(rows, "Concrete", date(2026, 9, 1))[0] == D("1.08")
  assert pl.escalation_for(rows, "Concrete", date(2026, 3, 1))[0] == D("1.03")

def test_escalation_trade_specific_beats_all_even_when_older():
  rows = [_esc("ALL", date(2026, 7, 1), "1.08"), _esc("Steel", date(2026, 1, 1), "1.20")]
  assert pl.escalation_for(rows, "steel", date(2026, 9, 1))[0] == D("1.20")
  assert pl.escalation_for(rows, "Concrete", date(2026, 9, 1))[0] == D("1.08")

def test_escalate_rounds_half_up():
  assert pl.escalate(D("100.10"), D("1.0505")) == D("105.16")

def test_analysis_totals_cost_overhead_profit_and_basis():
  lines = [
    pl.AnalysisLine(0, "MATERIAL", "Cement", "bag", D("8"), D("1450.00")),
    pl.AnalysisLine(1, "MATERIAL", "Sand", "cft", D("22.5"), D("85.00")),
    pl.AnalysisLine(2, "LABOUR", "Mason", "day", D("1.5"), D("2200.00")),
  ]
  out = pl.analysis_totals(lines, D("1"), D("10"), D("15"))
  assert out["cost"] == "16812.50"              
  assert out["overhead"] == "1681.25"
  assert out["profit"] == "2774.06"             
  assert out["total"] == "21267.81"
  assert out["rate"] == "21267.81"
  per100 = pl.analysis_totals(lines, D("100"), D("10"), D("15"))
  assert per100["rate"] == "212.68"
  assert out["cost_by_type"] == {"LABOUR": "3300.00", "MATERIAL": "13512.50"}

def test_analysis_rejects_non_positive_basis():
  with pytest.raises(ValueError):
    pl.analysis_totals([], D("0"), D("0"), D("0"))

def _item(code, unit, rate, active=True):
  return NS(work_item_code=code, unit=unit, rate=D(str(rate)), trade=None, csr_ref=None, is_active=active)

def test_rate_book_hash_is_order_independent_and_sensitive():
  hdr = {"code": "X", "immutable_version": 1}
  a = pl.rate_book_hash(hdr, [_item("A", "m3", 1), _item("B", "m2", 2)], [])
  b = pl.rate_book_hash(hdr, [_item("B", "m2", 2), _item("A", "cum", 1)], [])
  assert a == b                                                         
  assert a != pl.rate_book_hash(hdr, [_item("A", "m3", 1.01), _item("B", "m2", 2)], [])
  assert a == pl.rate_book_hash(hdr, [_item("A", "m3", 1), _item("B", "m2", 2), _item("Z", "m", 9, active=False)], [])

def _row(key, name, qty, rate=None, unit="m3", net=None, code="C-1"):
  q = D(str(qty))
  r = D(str(rate)) if rate is not None else None
  return {"item_key": key, "work_item_code": code, "material_name": name, "unit": unit, "quantity": q,
    "net_quantity": D(str(net)) if net is not None else q, "unit_rate": r,
    "amount": logic.q2(q * r) if r is not None else None}

def test_diff_added_removed_changed_unchanged():
  a = [_row("k1", "Col", 10, 100), _row("k2", "Beam", 5, 200), _row("k3", "Slab", 8, 50)]
  b = [_row("k1", "Col", 12, 100), _row("k3", "Slab", 8, 50), _row("k4", "Stair", 2, 300)]
  d = pl.diff_lines(a, b)
  by = {l["item_key"]: l for l in d["lines"]}
  assert by["k1"]["status"] == "CHANGED" and by["k1"]["quantity_delta"] == D("2.0000")
  assert by["k1"]["quantity_delta_pct"] == D("20.00") and by["k1"]["amount_delta"] == D("200.00")
  assert by["k2"]["status"] == "REMOVED" and by["k2"]["amount_delta"] == D("-1000.00")
  assert by["k3"]["status"] == "UNCHANGED"
  assert by["k4"]["status"] == "ADDED" and by["k4"]["amount_delta"] == D("600.00")
  s = d["summary"]
  assert (s["ADDED"], s["REMOVED"], s["CHANGED"], s["UNCHANGED"]) == (1, 1, 1, 1)
  assert s["total_a"] == D("2400.00") and s["total_b"] == D("2200.00") and s["total_delta"] == D("-200.00")

def test_diff_rate_change_alone_is_a_change():
  d = pl.diff_lines([_row("k", "Col", 10, 100)], [_row("k", "Col", 10, 110)])
  line = d["lines"][0]
  assert line["status"] == "CHANGED" and line["rate_delta"] == D("10.00") and line["amount_delta"] == D("100.00")

def test_diff_unit_change_converts_quantity_when_possible():
  d = pl.diff_lines([_row("k", "Col", 353.146667, 100, unit="cft")], [_row("k", "Col", 10, 100, unit="m3")])
  line = d["lines"][0]
  assert line["unit_changed"] and line["quantity_delta"] == D("0.0000") and line["rate_delta"] is None
  d = pl.diff_lines([_row("k", "Col", 5, 100, unit="kg")], [_row("k", "Col", 10, 100, unit="m3")])
  assert d["lines"][0]["quantity_delta"] is None and d["lines"][0]["status"] == "CHANGED"

def test_diff_manual_lines_match_on_name_and_repeat_suffix():
  a = [_row(None, "Site office", 1, 5000, unit="nos", code=None), _row(None, "Site office", 1, 5000, unit="nos", code=None)]
  b = [_row(None, "Site office", 1, 5000, unit="nos", code=None)]
  d = pl.diff_lines(a, b)
  assert sorted(l["status"] for l in d["lines"]) == ["REMOVED", "UNCHANGED"]

def test_diff_priced_to_unpriced_is_a_change_and_counted():
  d = pl.diff_lines([_row("k", "Col", 10, 100)], [_row("k", "Col", 10, None)])
  assert d["lines"][0]["status"] == "CHANGED"
  assert d["summary"]["unpriced_b"] == 1 and d["summary"]["unpriced_a"] == 0

def _snap_item(**kw):
  base = dict(id="00000000-0000-0000-0000-000000000001", item_key="k", work_item_code="C", material_name="Concrete",
    item_type="MATERIAL", unit="m3", quantity=D("10"), unit_rate=D("21000.00"), rate_source="RATE_BOOK",
    base_rate=D("20000.00"), escalation_factor=D("1.0500"), rate_resolution={"source": "RATE_BOOK"})
  base.update(kw)
  return base

def test_snapshot_hash_is_stable_and_covers_rate_provenance():
  header = {"project": "P"}
  _, totals, h1 = logic.build_snapshot([_snap_item()], header)
  _, _, h2 = logic.build_snapshot([_snap_item()], header)
  assert h1 == h2 and totals["grand"] == "210000.00"
  assert logic.build_snapshot([_snap_item(base_rate=D("19000.00"))], header)[2] != h1
  assert logic.build_snapshot([_snap_item(escalation_factor=D("1.0600"))], header)[2] != h1
  assert logic.build_snapshot([_snap_item(rate_resolution={"source": "PROJECT_OVERRIDE"})], header)[2] != h1

def test_snapshot_hash_ignores_decimal_spelling():
  header = {}
  a = logic.build_snapshot([_snap_item(base_rate=D("20000.0"), escalation_factor=D("1.05"))], header)[2]
  b = logic.build_snapshot([_snap_item(base_rate=D("20000.00"), escalation_factor=D("1.0500"))], header)[2]
  assert a == b

def test_snapshot_amount_is_rounded_per_line_and_totals_add_lines():
  items = [_snap_item(id=f"00000000-0000-0000-0000-00000000000{n}", item_key=f"k{n}", quantity=D("3"), unit_rate=D("333.335"))
    for n in (1, 2)]
  rows, totals, _ = logic.build_snapshot(items, {})
  assert [r["amount"] for r in rows] == [D("1000.01"), D("1000.01")] and totals["grand"] == "2000.02"