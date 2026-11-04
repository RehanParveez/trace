from __future__ import annotations
import re
from app.modules.drawings_boq.rebar.member_source import FLOOR_RANK

CLASSES = ("COLUMN", "BEAM", "FOOTING", "PLINTH", "SLAB", "LINTEL", "TANK")
NUMBER_FIELDS = {
  "span_ft": (1, 120), "strip_length_ft": (1, 3000), "junctions": (0, 200), "width_in": (3, 600), "depth_in": (3, 600), "length_in": (3, 6000),
  "main_bar": (3, 11), "main_s_in": (2, 24), "dist_bar": (3, 11), "dist_s_in": (2, 24), "pad_bar": (3, 11), "pad_s_in": (2, 24),
  "stirrup_bar": (3, 6), "stirrup_end_in": (2, 18), "stirrup_mid_in": (2, 18), "lx_ft": (1, 60), "ly_ft": (1, 60), "support_in": (3, 36), "top_bar": (3, 11), "top_s_in": (2, 24),
  "top_len_ft": (0.5, 30), "opening_ft": (1, 30), "tank_len_ft": (1, 60), "tank_wid_ft": (1, 60), "tank_ht_ft": (1, 30), "wall_in": (3, 36), "plan_count": (1, 2000),
  "bottom_main_bar": (3, 11), "bottom_main_s_in": (2, 24), "bottom_dist_bar": (3, 11), "bottom_dist_s_in": (2, 24), "wall_v_bar": (3, 11), "wall_v_s_in": (2, 24),
  "wall_h_bar": (3, 11), "wall_h_s_in": (2, 24), "top_main_bar": (3, 11), "top_main_s_in": (2, 24), "top_dist_bar": (3, 11), "top_dist_s_in": (2, 24),
}
LIST_FIELDS = {"runs_ft", "top_bars", "bottom_bars", "lintel_table"}
KEY_PATTERN = re.compile(r"^(" + "|".join(CLASSES) + r"):[^:|]{1,40}(:[A-Z]{3,10})?$")
MAX_KEYS = 400

def _num(v, lo, hi, what):
  if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
    raise ValueError(f"{what} must be a number between {lo} and {hi}")
  return v

def _flag(v):
  if not isinstance(v, bool):
    raise ValueError("this decision is true or false")
  return v

def check_stock(v):
  return None if v is None else _num(v, 10, 60, "the stock length in feet")

def check_zones(v):
  if v not in ("ZONES", "AVERAGE"):
    raise ValueError("tie_zones is ZONES or AVERAGE")
  return v

def check_l0(v):
  return None if v is None else _num(v, 6, 72, "the column end-zone length in inches")

def check_hooks(v):
  if not isinstance(v, dict) or set(v) - {"tie_d", "bar_d"}:
    raise ValueError("hook_lengths holds tie_d and bar_d, the hook extension as a multiple of the bar diameter")
  return {k: _num(x, 3, 16, f"hook {k}") for k, x in v.items()}

def check_link_basis(v):
  if v not in ("NET", "PERIMETER"):
    raise ValueError("link_cut_basis is NET (cover deducted, hooks added) or PERIMETER (the outside perimeter of the member)")
  return v

def check_junction(v):
  if v not in ("ONCE", "EACH_STRIP"):
    raise ValueError("strip_junction is ONCE or EACH_STRIP")
  return v

def check_heights(v):
  if not isinstance(v, dict):
    raise ValueError("floor_heights_ft is a table of floor to feet")
  bad = [k for k in v if k not in FLOOR_RANK]
  if bad:
    raise ValueError(f"unknown floor {bad[0]}; use {', '.join(FLOOR_RANK)}")
  return {k: _num(x, 6, 30, f"the height of {k}") for k, x in v.items()}

def _check_table(rows):
  out = []
  if not isinstance(rows, list) or len(rows) > 12:
    raise ValueError("lintel_table is a list of rows")
  for r in rows:
    if not isinstance(r, dict) or not isinstance(r.get("bars"), list):
      raise ValueError("a lintel_table row needs upto_ft and bars [[count, bar]]")
    out.append({"upto_ft": _num(r.get("upto_ft"), 1, 30, "upto_ft"), "bars": [[int(_num(n, 1, 20, "count")), int(_num(b, 3, 11, "bar"))] for n, b in r["bars"]],
      **{k: _num(r[k], 0, 100, k) for k in ("bearing_in", "stirrup_bar", "stirrup_s_in", "w_in", "d_in") if k in r}})
  return out

def check_member_inputs(v):
  if not isinstance(v, dict) or len(v) > MAX_KEYS:
    raise ValueError("member_inputs is a table of CLASS:MARK[:FLOOR] to inputs")
  out: dict = {}
  
  for key, fields in v.items():
    if not isinstance(key, str) or not KEY_PATTERN.match(key):
      raise ValueError(f"{key!r} is not CLASS:MARK or CLASS:MARK:FLOOR with a class of {', '.join(CLASSES)}")
    if not isinstance(fields, dict):
      raise ValueError(f"the inputs of {key} are a table")
    clean: dict = {}
    
    for f, x in fields.items():
      if f in NUMBER_FIELDS:
        clean[f] = _num(x, *NUMBER_FIELDS[f], f)
      elif f == "runs_ft":
        if not isinstance(x, list) or not x or len(x) > 60:
          raise ValueError("runs_ft is a list of run lengths in feet")
        clean[f] = [_num(r, 1, 3000, "a run") for r in x]
      elif f in ("top_bars", "bottom_bars"):
        if not isinstance(x, list) or len(x) > 8:
          raise ValueError(f"{f} is a list of [count, bar, kind]")
        clean[f] = [[int(_num(n, 1, 30, "count")), int(_num(b, 3, 11, "bar")), "Ext" if k == "Ext" else "Thr"] for n, b, k in x]
      elif f == "lintel_table":
        clean[f] = _check_table(x)
      else:
        raise ValueError(f"{f} is not an input of the expectation")
    out[key] = clean
    
  return out

EXPECT_KEYS = {
  "stock_length_ft": check_stock, "bar_count_plus_one": _flag, "tie_zones": check_zones, "column_l0": check_l0, "hook_lengths": check_hooks,
  "curtail_extras": _flag, "round_whole_bars": _flag, "strip_junction": check_junction, "floor_heights_ft": check_heights, "member_inputs": check_member_inputs,
  "link_cut_basis": check_link_basis,
}
