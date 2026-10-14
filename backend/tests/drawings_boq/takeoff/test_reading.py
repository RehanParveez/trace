from __future__ import annotations
import pytest
from tests.drawings_boq.takeoff.pdf_factory import Canvas, PdfBuilder
from app.modules.drawings_boq.takeoff.extract import rooms as R
from app.modules.drawings_boq.takeoff.extract import walls as W
from app.modules.drawings_boq.takeoff.extract.sheetkind import sheet_kind
from app.modules.drawings_boq.takeoff.prep import facts as F
from app.modules.drawings_boq.takeoff.prep.analyze import analyze_page
from app.modules.drawings_boq.takeoff.prep.extract import Word, extract_page, open_document
from app.modules.drawings_boq.takeoff.prep.texts import TextLine, build_lines, normalize_dimension_text, parse_dimension

def _word(text, cx, cy, size=6.0):
  length = size * 0.55 * len(text)
  return Word(text=text, x0=cx - length / 2, y0=cy - size / 2, x1=cx + length / 2, y1=cy + size / 2, angle=0.0, size=size, cx=cx, cy=cy, length=length, height=size)

def _lines(*texts):
  return [TextLine(text=t, spans=[], angle=0.0) for t in texts]

def _mm(text):
  return [round(r.value_mm, 1) for r in parse_dimension(text)]

def test_feet_without_a_foot_mark_are_read_as_feet_and_inches():
  assert normalize_dimension_text('12-0"') == "12'-0\""
  assert _mm('12-6"') == _mm("12'-6\"")

def test_inches_that_cannot_be_inches_are_left_alone():
  assert normalize_dimension_text('18"') == '18"'
  assert normalize_dimension_text('7-15"') == '7-15"'

def test_vulgar_fractions_become_ordinary_fractions():
  assert _mm('1½"') == _mm('1 1/2"')
  assert _mm('3¾"') == _mm('3 3/4"')

def test_a_size_split_over_two_lines_is_put_back_together():
  words = [_word("BED", 100, 100), _word("12'-0\"", 100, 92), _word("x15'-6\"", 100, 84)]
  lines = R.merge_split_sizes(build_lines(words))
  assert any("12'-0\"" in l.text and "15'-6\"" in l.text for l in lines)

def test_each_size_goes_to_the_nearest_name_only_once():
  mm_per_pt = 30.0
  names = [("BED", 100.0, 100.0), ("KITCHEN", 300.0, 100.0)]
  sizes = [("a", (3658.0, 4724.0), 102.0, 94.0), ("b", (3000.0, 3500.0), 298.0, 94.0)]
  pairs = R.pair_labels(names, sizes, mm_per_pt)
  assert len(pairs) == 2
  by_name = {p["name"]: p for p in pairs}
  assert abs(by_name["BED"]["a_mm"] - 3658.0) < 1 or abs(by_name["BED"]["b_mm"] - 3658.0) < 1

def test_a_size_far_from_every_name_makes_no_room():
  assert R.pair_labels([("BED", 0.0, 0.0)], [("a", (3000.0, 3000.0), 900.0, 900.0)], 30.0) == []

def test_a_door_size_next_to_a_room_name_is_not_a_room():
  assert not R.plausible_room({"name": "BED", "a_mm": 914.0, "b_mm": 2134.0})
  assert not R.plausible_room({"name": "BED", "a_mm": 60000.0, "b_mm": 60000.0})
  assert R.plausible_room({"name": "BED", "a_mm": 3658.0, "b_mm": 4724.0})

def test_a_small_room_may_be_small_but_not_thin():
  assert R.plausible_room({"name": "BATH", "a_mm": 1524.0, "b_mm": 1829.0})
  assert not R.plausible_room({"name": "BATH", "a_mm": 700.0, "b_mm": 4000.0})

def test_the_label_box_has_the_printed_area_and_is_centred_on_the_label():
  poly = R.label_polygon({"a_mm": 4000.0, "b_mm": 3000.0, "x": 500.0, "y": 400.0}, 10.0)
  assert abs(poly.area * 100.0 - 12_000_000.0) < 1
  assert abs(poly.centroid.x - 500.0) < 1e-6 and abs(poly.centroid.y - 400.0) < 1e-6

def test_labels_reads_names_and_sizes_from_text_lines():
  words = [_word("BED", 100, 100), _word("12'-0\"x15'-0\"", 100, 92)]
  names, sizes = R.labels(build_lines(words), None)
  assert [n[0] for n in names] and len(sizes) == 1
  assert sizes[0][1][0] >= 3000

def test_a_framing_plan_that_names_a_floor_is_still_structural():
  assert sheet_kind([_word("GROUND", 100, 50, 12), _word("FLOOR", 130, 50, 12), _word("FRAMING", 160, 50, 12), _word("PLAN", 190, 50, 12)])["kind"] == "STRUCTURAL"

def test_a_roof_plan_is_a_plan_not_a_structural_sheet():
  assert sheet_kind([_word("ROOF", 100, 50, 12), _word("PLAN", 130, 50, 12)])["kind"] == "PLAN"
  assert sheet_kind([_word("MUMTY", 100, 50, 12), _word("PLAN", 130, 50, 12)])["kind"] == "PLAN"
  assert sheet_kind([_word("MUMTY", 100, 50, 12), _word("FRAMING", 130, 50, 12), _word("PLAN", 160, 50, 12)])["kind"] == "STRUCTURAL"

RATIO = 100.0
MM_PT = 25.4 / 72.0 * RATIO
T_PT = 230.0 / MM_PT

def _pair(c, x1, y1, x2, y2, pen):
  if y1 == y2:
    c.line(x1, y1, x2, y2, pen)
    c.line(x1, y1 + T_PT, x2, y2 + T_PT, pen)
  else:
    c.line(x1, y1, x2, y2, pen)
    c.line(x1 + T_PT, y1, x2 + T_PT, y2, pen)

def _index(c):
  pdf = PdfBuilder().add_page(842, 595, c).build()
  return analyze_page(extract_page(open_document(pdf), 0, budget_s=20), 1.0, budget_s=20).index

def _house(c, pen, x0=100, y0=100, w=300, h=220):
  _pair(c, x0, y0, x0 + w, y0, pen)
  _pair(c, x0, y0 + h, x0 + w, y0 + h, pen)
  _pair(c, x0, y0, x0, y0 + h, pen)
  _pair(c, x0 + w, y0, x0 + w, y0 + h, pen)
  _pair(c, x0 + w / 2, y0, x0 + w / 2, y0 + h, pen)

def _clutter(c, pen):
  for i in range(14):
    _pair(c, 500, 100 + i * 25, 580, 100 + i * 25, pen)

def test_the_heavy_pen_is_the_wall_pen_when_light_lines_also_pair_up():
  c = Canvas()
  _house(c, 0.84)
  _clutter(c, 0.3)
  frames, runs, stats = W.detect_walls(_index(c), MM_PT)
  assert stats["wall_pen_pt"] == pytest.approx(0.84, abs=0.02)
  assert stats["runs_all_pens"] > len(runs)
  assert max(r.s1 for r in runs) < 600

def test_one_pen_everywhere_is_left_alone():
  c = Canvas()
  _house(c, 0.6)
  frames, runs, stats = W.detect_walls(_index(c), MM_PT)
  assert stats["wall_pen_pt"] is None
  assert len(runs) >= 4

def test_a_heavy_pen_with_too_few_walls_is_not_trusted():
  c = Canvas()
  _house(c, 0.3)
  _pair(c, 450, 300, 520, 300, 0.84)
  frames, runs, stats = W.detect_walls(_index(c), MM_PT)
  assert stats["wall_pen_pt"] is None

def _kinds(text):
  return [(i["kind"], i.get("value_mm"), i.get("scope")) for i in F.read_line(text)]

def test_slab_thickness_from_the_plan_and_from_the_structural_note():
  assert _kinds('6" Thick R.c.c Slab') == [("SLAB_THICKNESS", 152.4, "slab")]
  assert _kinds('* ALL SLABS ARE 5" THICK UNLESS OTHERWISE NOTED ON PLAN') == [("SLAB_THICKNESS", 127.0, "all slabs")]
  assert _kinds('* LOW ROOF SLAB IS 5" THICK') == [("SLAB_THICKNESS", 127.0, "low roof slab")]

def test_wall_thickness_plaster_fill_and_brick_column():
  assert _kinds('9" Thick R.c.c Wall')[0][:2] == ("RCC_WALL_THICKNESS", 228.6)
  assert _kinds('1/2" TH.C.M PLASTER')[0][:2] == ("PLASTER_THICKNESS", 12.7)
  assert _kinds('Filling shall be done in 6" thick compacted layers.')[0][:2] == ("FILL_LAYER", 152.4)
  col = F.read_line('BRICK COLUMNS 9"X9"')[0]
  assert col["kind"] == "BRICK_COLUMN" and col["value_mm"] == col["value2_mm"] == 228.6

def test_steel_grade_and_what_it_is_for():
  it = F.read_line("2. USE G-60 DEFORMED STEEL FOR FOOTING ,COLUMNS, BEAMS")[0]
  assert it["kind"] == "STEEL_GRADE" and it["grade"] == 60 and it["scope"] == "footing, columns, beams"

def test_concrete_class_with_a_fractional_mix():
  it = F.read_line('4. USE CLASS "B" (1:1½:3) CONCRETE IN UNDERGROUND & OVERHEAD')[0]
  assert (it["concrete_class"], it["mix"]) == ("B", "1:1.5:3")
  assert F.read_line('3. USE CLASS "C" (1:2:4) CONCRETE IN UNDERGROUND & OVERHEAD')[0]["mix"] == "1:2:4"

def test_clear_covers_with_fractions():
  vals = {i["scope"]: i["value_mm"] for t in ('(a) SLAB 3/4" BOTTOM.', '(b) BEAM 1½" ALL SIDES.', '(c) COLUMNS 1½" ALL SIDES.', '(d) FOOTING 2" ALL SIDES.') for i in F.read_line(t)}
  assert vals == {"slab": 19.05, "beam": 38.1, "column": 38.1, "footing": 50.8}

def test_bearing_capacity_and_stair_width():
  it = F.read_line("MUMTY WITH ASSUMED BEARING CAPACITY OF SOIL AS 1.0 TSF.")[0]
  assert (it["kind"], it["value"], it["unit"]) == ("BEARING_CAPACITY", 1.0, "TSF")
  assert F.read_line("Stair Width = 3'-6\"")[0]["value_mm"] == pytest.approx(1066.8)

def test_ordinary_text_states_no_fact():
  for t in ("BASEMENT FLOOR PLAN", "SECTOR------- I-11/2,", "TOTAL AREA OF PLOT = 30'-0\"x60'-0\"", "DETAIL OF STAIR SECTION", "1/2\"TH: JET BLACK MARBLE"):
    assert F.read_line(t) == [], t

def test_level_marks_are_bare_marks_only():
  assert F.level_mark_mm("+3'-6\"") == pytest.approx(1066.8)
  assert F.level_mark_mm("±0'-0\"") == 0.0
  assert F.level_mark_mm("-4'-0\"") == pytest.approx(-1219.2)
  assert F.level_mark_mm("+12\"") is None
  assert F.level_mark_mm("ROAD LEVEL ±0'-0\"") is None
  assert F.level_mark_mm("F.F.LEV.+3'-6\"") is None

def test_a_note_printed_on_every_view_is_one_fact_seen_many_times():
  facts = F.read_facts(_lines(*(['6" Thick R.c.c Slab'] * 5)))
  assert len(facts["items"]) == 1 and facts["items"][0]["count"] == 5

def test_level_ladder_gives_the_typical_floor_to_floor_height():
  marks = [{"mm": 0.0, "count": 5}, {"mm": 1066.8, "count": 5}, {"mm": 4267.2, "count": 5}, {"mm": 7467.6, "count": 5}, {"mm": 10363.2, "count": 5}, {"mm": 99999.0, "count": 1}]
  lad = F.level_ladder(marks)
  assert lad["levels_mm"] == [0.0, 1066.8, 4267.2, 7467.6, 10363.2]
  assert lad["typical_floor_to_floor_mm"] == pytest.approx(3200.4)

def test_two_levels_give_no_typical_height():
  assert F.level_ladder([{"mm": 0.0, "count": 3}, {"mm": 3000.0, "count": 3}])["typical_floor_to_floor_mm"] is None

def test_the_same_thing_stated_two_ways_is_a_conflict_to_settle():
  a = F.read_facts(_lines('6" Thick R.c.c Slab'))
  b = F.read_facts(_lines('* ALL SLABS ARE 5" THICK UNLESS OTHERWISE NOTED ON PLAN', "USE G-40 DEFORMED STEEL FOR SLABS"))
  g = F.gather([{"page_no": 5, "label": "x", "facts": a}, {"page_no": 6, "label": "y", "facts": b}])
  assert [c["kind"] for c in g["conflicts"]] == ["SLAB_THICKNESS"]
  assert sorted(v["value_mm"] for v in g["conflicts"][0]["values"]) == [127.0, 152.4]
  assert {v["value_mm"]: v["pages"] for v in g["conflicts"][0]["values"]} == {127.0: [6], 152.4: [5]}

def test_the_same_value_on_many_sheets_is_no_conflict():
  a = F.read_facts(_lines('9" Thick R.c.c Wall'))
  g = F.gather([{"page_no": 4, "label": "", "facts": a}, {"page_no": 5, "label": "", "facts": a}])
  assert g["conflicts"] == [] and g["items"][0]["pages"] == [4, 5] and g["items"][0]["count"] == 2
