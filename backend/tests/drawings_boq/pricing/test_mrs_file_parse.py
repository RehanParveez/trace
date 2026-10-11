from __future__ import annotations
from app.modules.drawings_boq.pricing import mrs_parse as mp
from decimal import Decimal as D
import pytest

def page(text: str) -> list[str]:
  return [l for l in text.strip("\n").split("\n")]

STYLE_A = page("""
CHAPTER 2 CONCRETE WORK
2.1 Plain cement concrete 1:4:8 in foundation Cft 111.00
2.2 Reinforced cement concrete 1:2:4 in slabs per 100 Cft 22,200
(a) with crushed stone Cft 333
2.3 Brick work in cement mortar
    1:6 in foundation and plinth
    Per 1000 Nos 4,444.50
2.4 Deformed steel bars as reinforcement Kg 777
""")

def test_unit_basis_forms_mean_the_same_thing():
  for raw in ("% cft", "per 100 cft", "100 Cft", "Rs. per 100 Cft", "100cft"):
    ub = mp.parse_unit_basis(raw)
    assert (ub.basis_qty, ub.unit, ub.known) == (D(100), "cft", True), raw
  assert mp.parse_unit_basis("1000 Nos") == mp.UnitBasis(D(1000), "nos", True, None)
  assert mp.parse_unit_basis("Sft").basis_qty == 1 and mp.parse_unit_basis("Rft").unit == "rft"
  assert mp.parse_unit_basis("Cum").unit == "m3" and mp.parse_unit_basis("kgs").unit == "kg"
  assert mp.parse_unit_basis("metric tonne").unit == "tonne"

def test_ambiguous_and_unconvertible_units_are_recognised_but_flagged():
  ton = mp.parse_unit_basis("ton")
  assert ton.unit == "ton" and not ton.known and "ambiguous" in ton.note
  bag = mp.parse_unit_basis("bag")
  assert bag.unit == "bag" and not bag.known
  junk = mp.parse_unit_basis("whatever")
  assert junk.unit is None and not junk.known

def test_unit_rate_divides_a_block_price_down():
  assert mp.unit_rate_from(D("4500"), D(100)) == D("45")
  assert mp.unit_rate_from(D("1234.5"), D(1)) == D("1234.5")

def test_parse_rate_accepts_printed_forms_and_rejects_the_rest():
  assert mp.parse_rate("1,234.50") == D("1234.50")
  assert mp.parse_rate("Rs. 1234/-") == D("1234")
  assert mp.parse_rate(" 98 ") == D("98")
  for bad in ("", None, "12 34", "-5", "abc", "1,23", "NaN"):
    assert mp.parse_rate(bad) is None, bad

def test_style_a_rows_chapter_basis_sub_items_and_wrapped_description():
  rows, unparsed = mp.parse_pages([STYLE_A], mp.GENERIC)
  assert unparsed == []
  assert [r.item_no for r in rows] == ["2.1", "2.2", "2.2(a)", "2.3", "2.4"]
  by = {r.item_no: r for r in rows}
  assert all(r.chapter == "CHAPTER 2 CONCRETE WORK" for r in rows)
  assert by["2.1"].unit == "cft" and by["2.1"].rate == D("111.00") and by["2.1"].unit_rate == D("111.00")
  assert by["2.2"].basis_qty == D(100) and by["2.2"].unit_rate == D("222") and "BASIS_APPLIED" in by["2.2"].flags
  assert by["2.2(a)"].rate == D("333") and by["2.2(a)"].unit == "cft"
  assert by["2.3"].unit == "nos" and by["2.3"].basis_qty == D(1000) and by["2.3"].unit_rate == D("4.4445")
  assert "WRAPPED_DESCRIPTION" in by["2.3"].flags and "1:6 in foundation and plinth" in by["2.3"].description
  assert by["2.4"].unit == "kg" and by["2.4"].page == 1
  assert all(not (set(r.flags) & mp.REVIEW_FLAGS) for r in rows)

def test_unknown_unit_and_missing_item_number_are_flagged_not_dropped():
  rows, _ = mp.parse_pages([page("""
3.1 Cement bags supplied Bag 650
Extra labour for height Cft 12
""")])
  assert [r.item_no for r in rows] == ["3.1", None]
  assert "UNIT_UNKNOWN" in rows[0].flags and "NO_ITEM_NO" in rows[1].flags

def test_integer_item_numbers_need_a_dot_or_column_gap():
  rows, _ = mp.parse_pages([page("""
12. Door frame chowkat Nos 50
13   Window frame Nos 60
thick 25 mm Cft 70
""")])
  assert [r.item_no for r in rows] == ["12", "13", None]

def test_two_rate_columns_are_read_and_cross_checked():
  profile = mp.LayoutProfile("T", rate_columns=2, alt_unit="m3")
  text = page("""
4.1 Concrete A Cft 10.00 353.15
4.2 Concrete B Cft 20.00 999.00
""")
  rows, _ = mp.parse_pages([text], profile)
  assert rows[0].rate == D("10.00") and rows[0].rate_alt == D("353.15")
  report = mp.apply_checks(rows, [], page_count=1, second_pass_tokens=None, content_hash="h", profile=profile)
  assert "ALT_RATE_MISMATCH" not in rows[0].flags and "ALT_RATE_MISMATCH" in rows[1].flags
  assert next(c for c in report["checks"] if c["code"] == "ALT_RATES")["count"] == 1

def test_single_rate_profile_keeps_a_stray_number_in_the_description():
  rows, _ = mp.parse_pages([page("5.1 Pipe of diameter Nos 6 450")])
  assert rows[0].rate == D("450") and rows[0].description.endswith("6")

def test_running_headers_and_footers_are_dropped_and_page_numbers_ignored():
  pages = [page(f"GOVERNMENT OF NOWHERE RATE SCHEDULE\n{i}.1 Item {i} Cft {100 + i}\nPage {i} of 8") for i in range(1, 9)]
  rows, unparsed = mp.parse_pages(pages)
  assert len(rows) == 8 and unparsed == [] and all(r.chapter is None for r in rows)

def test_lines_that_look_like_rows_but_are_not_read_are_reported():
  rows, unparsed = mp.parse_pages([page("""
6.1 Good row Cft 10
Sundry items total 1,234.00
6.2 Row with no end
""")])
  assert len(rows) == 1
  texts = [u["text"] for u in unparsed]
  assert any("Sundry" in t for t in texts) and any("6.2" in t for t in texts)

def test_checks_pass_on_clean_input_and_report_page_coverage():
  rows, unparsed = mp.parse_pages([STYLE_A, page("2.5 Another Cft 5\n2.6 Another Sft 6")])
  tokens = {1: mp.number_tokens(STYLE_A), 2: mp.number_tokens(["2.5 Another Cft 5", "2.6 Another Sft 6"])}
  report = mp.apply_checks(rows, unparsed, page_count=2, second_pass_tokens=tokens, content_hash="abc")
  assert report["status"] == "PASS", report["checks"]
  assert mp.can_publish(report) and report["counts"]["rows"] == 7 and report["page_coverage"] == 1.0

def test_checks_fail_when_nothing_is_read_or_pages_are_missed():
  empty = mp.apply_checks([], [], page_count=3, second_pass_tokens=None, content_hash="h")
  assert empty["status"] == "FAIL" and not mp.can_publish(empty)
  rows, _ = mp.parse_pages([page("1.1 Row Cft 5")])
  partial = mp.apply_checks(rows, [], page_count=10, second_pass_tokens=None, content_hash="h")
  assert next(c for c in partial["checks"] if c["code"] == "PAGE_COVERAGE")["status"] == "fail"
  assert partial["status"] == "FAIL"

def test_second_read_flags_a_rate_the_other_reader_never_saw():
  rows, _ = mp.parse_pages([page("1.1 Row one Cft 111\n1.2 Row two Cft 222")])
  tokens = {1: {"111", "1", "2"}}
  report = mp.apply_checks(rows, [], page_count=1, second_pass_tokens=tokens, content_hash="h")
  assert "SECOND_PASS_MISSING" not in rows[0].flags and "SECOND_PASS_MISSING" in rows[1].flags
  assert next(c for c in report["checks"] if c["code"] == "SECOND_READ")["count"] == 1

def test_duplicate_item_numbers_with_different_rates_and_numbering_gaps():
  rows, _ = mp.parse_pages([page("""
CHAPTER ONE
7.1 A Cft 10
7.2 B Cft 20
7.2 B again Cft 21
7.5 E Cft 50
""")])
  report = mp.apply_checks(rows, [], page_count=1, second_pass_tokens=None, content_hash="h")
  assert [r.item_no for r in rows if "DUPLICATE_ITEM_NO" in r.flags] == ["7.2", "7.2"]
  gap = next(c for c in report["checks"] if c["code"] == "NUMBERING_GAPS")
  assert gap["status"] == "warn" and "7.2" in gap["detail"]

def test_a_rate_far_from_its_neighbours_is_flagged():
  lines = [f"8.{i} Item {i} Cft {100 + i}" for i in range(1, 10)] + ["8.10 Item ten Cft 90000"]
  rows, _ = mp.parse_pages([page("\n".join(lines))])
  mp.apply_checks(rows, [], page_count=1, second_pass_tokens=None, content_hash="h")
  assert [r.item_no for r in rows if "RATE_OUTLIER" in r.flags] == ["8.10"]

def test_spot_sample_is_stable_spread_and_bounded():
  a = mp.spot_sample_indices(1000, "abc")
  assert a == mp.spot_sample_indices(1000, "abc") and a != mp.spot_sample_indices(1000, "abd")
  assert 15 <= len(a) <= 40 and a == sorted(a) and a[-1] - a[0] > 800
  assert mp.spot_sample_indices(5, "abc") == [0, 1, 2, 3, 4] or len(mp.spot_sample_indices(5, "abc")) <= 5
  assert mp.spot_sample_indices(0, "abc") == []

def test_suggestions_need_a_matching_description_and_a_compatible_unit():
  assert mp.suggest_work_item("Plain cement concrete 1:4:8", "cft")[0] == "CON-PCC"
  assert mp.suggest_work_item("Reinforced cement concrete in slabs", "m3")[0] == "CON-RCC"
  assert mp.suggest_work_item("Reinforced cement concrete in slabs", "sft") is None
  assert mp.suggest_work_item("Deformed bars steel reinforcement", "kg")[0] == "STL-REBAR"
  assert mp.suggest_work_item("Deformed bars steel reinforcement", "tonne")[0] == "STL-REBAR"
  assert mp.suggest_work_item("Supply of widgets", "nos") is None
  assert mp.suggest_work_item("Plaster 1:4", None) is None

def test_publish_plan_resolves_one_rate_per_work_item_and_unit():
  plan = mp.plan_publish([
    {"id": 1, "work_item_code": "CON-RCC", "unit": "cft", "unit_rate": D("100"), "item_no": "2.1"},
    {"id": 2, "work_item_code": "CON-RCC", "unit": "cft", "unit_rate": D("120"), "item_no": "2.2"},
    {"id": 3, "work_item_code": "MAS-BRICK", "unit": "cft", "unit_rate": D("90"), "item_no": "3.1"},
    {"id": 4, "work_item_code": "FIN-PAINT", "unit": "bag", "unit_rate": D("5"), "item_no": "4.1"},
    {"id": 5, "work_item_code": "FIN-PLASTER", "unit": "sft", "unit_rate": D("0.001"), "item_no": "5.1"},
    {"id": 6, "work_item_code": "FIN-FLOOR", "unit": "sft", "unit_rate": None, "item_no": "6.1"},
  ])
  assert [i["id"] for i in plan.items] == [3]
  assert plan.conflicts == [{"work_item_code": "CON-RCC", "unit": "cft", "rows": [1, 2], "item_nos": ["2.1", "2.2"]}]
  assert {p["row_id"] for p in plan.problems} == {4, 5, 6}

def test_book_codes_are_one_per_district():
  assert mp.book_code("Punjab", "Lahore") == "MRS-PB-LAHORE"
  assert mp.book_code("Punjab", "Dera Ghazi Khan") == "MRS-PB-DERA-GHAZI-KHAN"
  assert mp.book_code("Sindh", None) == "MRS-SD-NA"

def test_csv_path_uses_the_same_rules():
  data = b"item_no,description,unit,rate,chapter\n1.1,Plain concrete,% Cft,\"22,200\",C1\n1.2,Bags,Bag,650,C1\n1.3,Bad,Cft,,C1\n"
  rows = mp.parse_csv(data)
  assert rows[0].unit_rate == D("222") and "BASIS_APPLIED" in rows[0].flags
  assert "UNIT_UNKNOWN" in rows[1].flags and "RATE_MISSING" in rows[2].flags
  with pytest.raises(ValueError):
    mp.parse_csv(b"a,b\n1,2\n")