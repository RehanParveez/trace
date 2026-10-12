from __future__ import annotations
import pytest
try:
  from house_factory import make_house
except ModuleNotFoundError:  
  from tests.drawings_boq.takeoff.house_factory import make_house
from app.modules.drawings_boq.takeoff.extract import pipeline as P
from app.modules.drawings_boq.takeoff.prep.analyze import analyze_page
from app.modules.drawings_boq.takeoff.prep.extract import extract_page, open_document

def _index(pdf):
  return analyze_page(extract_page(open_document(pdf), 0, budget_s=20), 1.0, budget_s=20).index

def _mm_per_pt(ratio):
  return 25.4 / 72.0 * ratio

def _read(ratio=100.0, **kw):
  run = {k: kw.pop(k) for k in ("cal_factor", "scale_unverified", "content_kind", "budget_s") if k in kw}
  return P.run_extraction(_index(make_house(drawn_ratio=ratio, **kw)), _mm_per_pt(ratio), **run)

def _by(res, category):
  return [c for c in res.candidates if c.category == category]

def _one(res, category, tag=None):
  rows = [c for c in _by(res, category) if tag is None or c.tag == tag]
  assert len(rows) == 1, [c.label for c in rows]
  return rows[0]

def _codes(c):
  return [n["code"] for n in c.notes]

@pytest.mark.parametrize("ratio", [50.0, 100.0, 200.0])
def test_marks_are_counted_with_sizes_from_the_schedule_at_any_scale(ratio):
  res = _read(ratio)
  c1, c2 = _one(res, "COLUMN", "C1"), _one(res, "COLUMN", "C2")
  assert (c1.count, c2.count) == (4, 4)
  assert (c1.params["length_mm"], c1.params["width_mm"]) == (230, 230)
  assert (c2.params["length_mm"], c2.params["width_mm"]) == (230, 300)
  assert _one(res, "DOOR", "D1").count == 3 and _one(res, "DOOR", "D2").count == 1
  w1 = _one(res, "WINDOW", "W1")
  assert w1.count == 4 and w1.facts["size_schedule_mm"] == [1200, 1200]

def test_a_schedule_size_that_differs_from_the_drawn_shape_is_a_warning():
  res = _read()
  assert _one(res, "COLUMN", "C1").status == "VALID"
  c2 = _one(res, "COLUMN", "C2")
  assert c2.status == "WARNING" and "SIZE_DIFFERS_FROM_SCHEDULE" in _codes(c2)
  assert c2.confidence < _one(res, "COLUMN", "C1").confidence

def test_column_height_comes_from_the_missing_list_and_wall_height_from_the_note():
  res = _read()
  assert _one(res, "COLUMN", "C1").missing == ["height_mm"]
  for wall in _by(res, "WALL"):
    assert wall.missing == [] and wall.params["height_mm"] == 3000 and "HEIGHT_FROM_NOTE" in _codes(wall)

def test_walls_are_centre_line_runs_with_exact_lengths():
  res = _read()
  walls = _by(res, "WALL")
  assert len(walls) == 7
  by_t: dict = {}
  for w in walls:
    by_t.setdefault(w.params["thickness_mm"], []).append(round(w.facts["length_cc_m"], 2))
  assert sorted(by_t[230]) == [8.0, 8.0, 9.0, 9.0]
  assert sorted(by_t[115]) == [3.83, 3.83, 8.77]
  assert all(w.quantity_mode == "LENGTH_X_HEIGHT_X_THICKNESS" and w.kind == "LENGTH" for w in walls)

def test_door_gaps_are_listed_on_the_wall_they_cut():
  walls = _by(_read(), "WALL")
  gaps = sorted(g for w in walls for g in w.facts["gaps_mm"])
  assert gaps == [900, 900, 900, 1000]
  assert all("WALL_OPENINGS_INCLUDED" in _codes(w) for w in walls if w.facts["gaps_mm"])

def test_rooms_get_their_names_and_measured_areas():
  rooms = {c.facts["name"]: c.facts["area_m2"] for c in _by(_read(), "ROOM")}
  assert set(rooms) == {"BED ROOM 1", "BED ROOM 2", "LOUNGE", "KITCHEN"}
  assert rooms["LOUNGE"] == pytest.approx(22.31, abs=0.05)
  assert rooms["KITCHEN"] == pytest.approx(10.82, abs=0.05)
  assert all(c.quantity_mode == "DIRECT" and c.kind == "AREA" for c in _by(_read(), "ROOM"))

def test_without_a_schedule_the_drawn_shape_gives_the_size():
  res = _read(with_schedule=False)
  c1 = _one(res, "COLUMN", "C1")
  assert (c1.params["length_mm"], c1.params["width_mm"]) == (230, 230)
  assert "SIZE_FROM_SCHEDULE" not in _codes(c1)
  assert "size_schedule_mm" not in _one(res, "WINDOW", "W1").facts

def test_extra_shapes_without_a_mark_lower_the_confidence():
  res = _read(extra_untagged_column=True)
  for tag in ("C1", "C2"):
    c = _one(res, "COLUMN", tag)
    assert "UNTAGGED_SAME_SIZE" in _codes(c) and c.status == "WARNING"

def test_an_unchecked_scale_warns_on_every_item_and_lowers_confidence():
  sure = _read()
  unsure = _read(cal_factor=0.8, scale_unverified=True)
  assert all("SCALE_UNVERIFIED" in _codes(c) and c.status != "VALID" for c in unsure.candidates)
  a, b = _one(sure, "DOOR", "D1"), _one(unsure, "DOOR", "D1")
  assert b.confidence == pytest.approx(a.confidence * 0.8, abs=0.001)

def test_a_raster_sheet_lowers_confidence():
  vec = _one(_read(), "DOOR", "D1").confidence
  ras = _one(_read(content_kind="RASTER"), "DOOR", "D1").confidence
  assert ras == pytest.approx(vec * 0.85, abs=0.001)

def test_running_out_of_time_keeps_what_was_found_and_says_so():
  res = _read(budget_s=0.0)
  assert any(n["code"] == "TIME_LIMIT" for n in res.notes)
  assert _by(res, "COLUMN") and not _by(res, "WALL")

def test_keys_are_stable_between_two_reads():
  a = sorted(c.key for c in _read().candidates)
  b = sorted(c.key for c in _read().candidates)
  assert a == b and len(set(a)) == len(a)

def test_keys_do_not_depend_on_the_scale():
  a = sorted(c.key for c in _by(P.run_extraction(_index(make_house(drawn_ratio=100.0)), _mm_per_pt(100.0)), "WALL"))
  b = sorted(c.key for c in _by(P.run_extraction(_index(make_house(drawn_ratio=100.0)), _mm_per_pt(100.0) * 1.07), "WALL"))
  assert a == b

def test_reserved_work_items_are_never_suggested():
  for c in _read().candidates:
    assert c.work_item not in ("STL-REBAR", "STL-STRUCT", "STL-PILE")

def test_every_candidate_is_ready_for_a_measurement():
  from app.engine.measure import takeoff as tk
  for c in _read().candidates:
    if c.category == "BEAM":
      continue
    assert (c.kind, c.quantity_mode) in tk.MODES
    tk.normalized_geometry(c.kind, c.geometry)
    needed = set(tk.required_params(c.kind, c.quantity_mode))
    have = {k for k, v in c.params.items() if v not in (None, "")}
    gap = needed - have
    assert gap <= {"depth_mm", "height_mm"} and ({"height_mm"} & gap or {"depth_mm"} & gap or not gap) , (c.label, gap)