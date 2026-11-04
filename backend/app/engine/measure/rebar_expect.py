from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal as D, ROUND_CEILING, ROUND_HALF_UP

PRINTED, DERIVED, DEFAULTED, MISSING = "PRINTED", "DERIVED", "DEFAULTED", "MISSING"
STATES = (PRINTED, DERIVED, DEFAULTED, MISSING)
WEIGHT_DIVISOR = D(162)
STOCK_DEFAULT_FT = D(40)
M_PER_FT = D("0.3048")
IN_PER_BAR_NO = D("0.125")
MM_PER_IN = D("25.4")
TWO_PLACES = D("0.01")
FRACTIONS = {"L/3": D(1) / D(3), "L/8": D(1) / D(8), "L/4": D(1) / D(4), "L/6": D(1) / D(6)}

def kg_per_ft(bar_no) -> D:
  """d squared over 162 (d in mm) per metre, converted to feet. The engine's own divisor is 162.2 (rebar.KG_M_DIVISOR)."""
  d_mm = D(int(bar_no)) * IN_PER_BAR_NO * MM_PER_IN
  return d_mm * d_mm / WEIGHT_DIVISOR * M_PER_FT

def q2(x: D | None) -> D | None:
  return None if x is None else x.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

def ceil_d(x: D) -> D:
  return x.to_integral_value(rounding=ROUND_CEILING)

@dataclass(frozen=True)
class Input:
  name: str
  value: object
  state: str
  source: str
  flag: str | None = None

  def as_dict(self) -> dict:
    v = self.value
    if isinstance(v, D):
      v = str(v)
    elif isinstance(v, (list, tuple)):
      v = [str(x) if isinstance(x, D) else x for x in v]
    return {"name": self.name, "value": v, "state": self.state, "source": self.source, "flag": self.flag}

def printed(name, value, source) -> Input:
  return Input(name, value, PRINTED, source)

def derived(name, value, source) -> Input:
  return Input(name, value, DERIVED, source)

def defaulted(name, value, source, flag="VALUE_DEFAULTED") -> Input:
  return Input(name, value, DEFAULTED, source, flag)

def missing(name, why="not read from the drawings") -> Input:
  return Input(name, None, MISSING, why)

class Ledger:
  def __init__(self, items: list):
    self._d = {i.name: i for i in items}
    self.used: dict = {}
    self.blocked: list = []

  def get(self, name: str, why: str | None = None) -> Input:
    i = self._d.get(name) or missing(name, why or "not read from the drawings")
    self.used[name] = i
    return i

  def val(self, name: str):
    return self.get(name).value

  def opt(self, name: str):
    i = self._d.get(name)
    if i is not None:
      self.used[name] = i
    return None if i is None else i.value

  def put(self, i: Input) -> Input:
    self._d[i.name] = i
    self.used[i.name] = i
    return i

  def need(self, *names: str) -> bool:
    gone = [n for n in names if self.val(n) is None]
    for n in gone:
      if n not in self.blocked:
        self.blocked.append(n)
    return not gone

@dataclass
class ExpectedLine:
  role: str
  dia: int | None
  count: D | None = None
  cut_ft: D | None = None
  spacing_in: D | None = None
  laps: int = 0
  lap_ft: D = D(0)
  note: str | None = None
  total_ft: D | None = field(default=None, init=False)
  kg: D | None = field(default=None, init=False)

  def __post_init__(self):
    if self.count is not None and self.cut_ft is not None:
      self.cut_ft = q2(self.cut_ft)
      self.total_ft = q2(self.count * (self.cut_ft + self.laps * self.lap_ft))
      if self.dia:
        self.kg = q2(self.total_ft * kg_per_ft(self.dia))

  def as_dict(self) -> dict:
    s = lambda v: None if v is None else str(v)
    return {"role": self.role, "dia": self.dia, "count": s(self.count), "cut_ft": s(self.cut_ft), "spacing_in": s(self.spacing_in), "laps": self.laps, "lap_ft": s(self.lap_ft),
      "total_ft": s(self.total_ft), "kg": s(self.kg), "note": self.note}

@dataclass
class Expected:
  cls: str
  mark: str
  floor: str | None
  lines: list
  inputs: list
  blocked: list
  notes: list = field(default_factory=list)

  @property
  def complete(self) -> bool:
    return bool(self.lines) and not self.blocked and all(l.kg is not None for l in self.lines)

  @property
  def count(self) -> D | None:
    return sum((l.count for l in self.lines), D(0)) if self.lines and all(l.count is not None for l in self.lines) else None

  @property
  def total_ft(self) -> D | None:
    return sum((l.total_ft for l in self.lines), D(0)) if self.lines and all(l.total_ft is not None for l in self.lines) else None

  @property
  def kg(self) -> D | None:
    known = [l.kg for l in self.lines if l.kg is not None]
    return sum(known, D(0)) if known else None

  def as_dict(self) -> dict:
    s = lambda v: None if v is None else str(v)
    return {"class": self.cls, "mark": self.mark, "floor": self.floor, "count": s(self.count), "total_ft": s(self.total_ft), "kg": s(self.kg), "complete": self.complete,
      "lines": [l.as_dict() for l in self.lines], "inputs": [i.as_dict() for i in self.inputs], "blocked": list(self.blocked), "notes": list(self.notes)}

def _finish(L: Ledger, cls: str, mark: str, floor: str | None, lines: list, notes: list | None = None) -> Expected:
  return Expected(cls, mark, floor, lines, list(L.used.values()), list(L.blocked), notes or [])

def input_shares(expectations: list) -> dict:
  n = {s: 0 for s in STATES}
  for e in expectations:
    for i in e.inputs:
      n[i.state] += 1
  total = sum(n.values())
  return {"counts": n, "total": total, "shares": {s: (round(n[s] / total, 4) if total else 0.0) for s in STATES}}

def laps(run_ft: D, stock_ft: D, lap_in: D) -> int:
  if run_ft <= stock_ft:
    return 0
  usable = stock_ft - lap_in / 12
  if usable <= 0:
    raise ValueError("the lap is longer than the stock bar")
  return int(ceil_d((run_ft - stock_ft) / usable))

def _stock(L: Ledger) -> Input:
  return L.get("stock_length_ft")

def _bar_laps(L: Ledger, run_ft: D, bar_no: int) -> tuple:
  lap_in = L.val(f"LAP_{bar_no}")
  stock = _stock(L).value
  if lap_in is None or stock is None:
    return None, None
  return laps(run_ft, D(str(stock)), D(str(lap_in))), D(str(lap_in)) / 12

def _count(L: Ledger, span_in: D, spacing_in: D) -> D:
  n = D(span_in) / D(spacing_in)
  if L.val("round_whole_bars"):
    n = ceil_d(n)
  else:
    n = n.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
  return n + (1 if L.val("bar_count_plus_one") else 0)

def _tie_cut_ft(L: Ledger, w_in: D, d_in: D, cover_in: D, bar_no: int) -> D:
  if L.opt("link_cut_basis") == "PERIMETER":
    return (2 * (w_in + d_in)) / 12
  hook = max(D(str(L.val("hook_tie_d"))) * D(bar_no) * IN_PER_BAR_NO, D(3))
  return (2 * ((w_in - 2 * cover_in) + (d_in - 2 * cover_in)) + 2 * hook) / 12

def _zone_count(L: Ledger, length_in: D, end_in: D, mid_in: D, end_zone_in: D) -> D:
  if L.val("tie_zones") == "AVERAGE":
    return ceil_d(length_in / ((end_in + mid_in) / 2))
  return 2 * ceil_d(end_zone_in / end_in) + ceil_d(max(length_in - 2 * end_zone_in, D(0)) / mid_in)

def column(L: Ledger, mark: str, floor: str | None) -> Expected:
  lines: list = []
  notes: list = []
  n, bar = L.val("steel_n"), L.val("steel_bar")
  H = L.val("height_ft")
  if L.need("steel_n", "steel_bar") and L.need("height_ft") and L.need(f"LAP_{bar}"):
    lap_in = D(str(L.val(f"LAP_{bar}")))
    lines.append(ExpectedLine("Vertical Bars", int(bar), D(int(n)), D(str(H)) + lap_in / 12, note="floor to floor plus one lap"))
  elif bar is not None:
    L.need("height_ft", f"LAP_{bar}")
    lines.append(ExpectedLine("Vertical Bars", int(bar), D(int(n)) if n is not None else None))
    
  tb, end, mid = L.val("tie_bar"), L.val("tie_end_in"), L.val("tie_mid_in")
  w, d = L.val("size_w_in"), L.val("size_d_in")
  cover = L.val("COVER_COLUMN_BEAM")
  if L.need("tie_bar", "tie_end_in", "tie_mid_in", "size_w_in", "size_d_in", "COVER_COLUMN_BEAM") and L.need("height_ft"):
    H_in = D(str(H)) * 12
    l0_dec = L.opt("column_l0_in")
    if l0_dec is not None:
      l0 = D(str(l0_dec))
      L.put(derived("l0_in", l0, "decision column_l0"))
    else:
      l0 = max(D(str(max(w, d))), H_in / 6, D(18))
      L.put(defaulted("l0_in", l0, "largest of the larger column side, H/6 and 18 in (assumed; no end-zone length is printed)", "UNSURE,VALUE_DEFAULTED"))
    count = _zone_count(L, H_in, D(str(end)), D(str(mid)), l0)
    cut = _tie_cut_ft(L, D(str(w)), D(str(d)), D(str(cover)), int(tb))
    lines.append(ExpectedLine("Rings", int(tb), count, cut, D(str(mid)), note="zones" if L.val("tie_zones") == "ZONES" else "one average spacing"))
  elif tb is not None:
    lines.append(ExpectedLine("Rings", int(tb), None, None, D(str(mid)) if mid is not None else None))
  return _finish(L, "COLUMN", mark, floor, lines, notes)

def _bars_of(L: Ledger, prefix: str) -> list:
  return L.val(f"{prefix}_bars") or []

def beam(L: Ledger, mark: str, floor: str | None) -> Expected:
  lines: list = []
  notes: list = []
  span = L.val("span_ft")
  for prefix, role in (("bottom", "Bottom Bars"), ("top", "Top Bars")):
    for n, bar, kind in _bars_of(L, prefix):
      if kind == "Ext":
        frac_name = "CURTAILMENT_TOP" if prefix == "top" else "CURTAILMENT_BOTTOM"
        frac = FRACTIONS.get(str(L.val(frac_name))) if L.val(frac_name) else None
        if L.val("curtail_extras") and frac is not None and span is not None:
          length = D(str(span)) * frac if prefix == "top" else D(str(span)) * (1 - 2 * frac)
          lines.append(ExpectedLine(f"{role} (extra)", bar, D(n), length, note=f"curtailed to {L.val(frac_name) if prefix == 'top' else 'L - 2 x ' + str(L.val(frac_name))}"))
          continue
        if L.val("curtail_extras") and frac is None:
          L.need(frac_name)
      if L.need("span_ft", f"EMBEDMENT_{bar}"):
        run = D(str(span)) + 2 * D(str(L.val(f"EMBEDMENT_{bar}"))) / 12
        k, lap_ft = _bar_laps(L, run, bar)
        if k is None:
          L.need(f"LAP_{bar}", "stock_length_ft")
          lines.append(ExpectedLine(role + (" (extra, full length)" if kind == "Ext" else ""), bar, D(n)))
        else:
          lines.append(ExpectedLine(role + (" (extra, full length)" if kind == "Ext" else ""), bar, D(n), run, laps=k, lap_ft=lap_ft))
      else:
        lines.append(ExpectedLine(role + (" (extra)" if kind == "Ext" else ""), bar, D(n)))
        
  sb, end, mid = L.val("stirrup_bar"), L.val("stirrup_end_in"), L.val("stirrup_mid_in")
  w, d, cover = L.val("width_in"), L.val("depth_in"), L.val("COVER_COLUMN_BEAM")
  if L.need("stirrup_bar", "stirrup_end_in", "stirrup_mid_in", "width_in", "depth_in", "COVER_COLUMN_BEAM", "span_ft"):
    L_in = D(str(span)) * 12
    count = _zone_count(L, L_in, D(str(end)), D(str(mid)), L_in / 4)
    lines.append(ExpectedLine("Rings", int(sb), count, _tie_cut_ft(L, D(str(w)), D(str(d)), D(str(cover)), int(sb)), D(str(mid)), note="0.25L / 0.5L / 0.25L" if L.val("tie_zones") == "ZONES" else "one average spacing"))
  elif sb is not None:
    lines.append(ExpectedLine("Rings", int(sb), None, None, D(str(mid)) if mid is not None else None))
  if not any(k == "Ext" for p in ("top", "bottom") for _, _, k in _bars_of(L, p)):
    notes.append("no extras callout: through bars only")
  return _finish(L, "BEAM", mark, floor, lines, notes)

def strip_footing(L: Ledger, mark: str, floor: str | None) -> Expected:
  lines: list = []
  
  c = L.val("COVER_FOOTING")
  length = L.val("strip_length_ft")
  W, depth = L.val("width_in"), L.val("depth_in")
  if length is not None and L.val("strip_junction") == "EACH_STRIP" and L.opt("junctions") is not None and W is not None:
    length = D(str(length)) + D(int(L.val("junctions"))) * D(str(W)) / 12
    L.put(derived("strip_length_adjusted_ft", length, "strip length plus one width per junction (strip_junction = EACH_STRIP)"))
  mb, ms = L.val("main_bar"), L.val("main_s_in")
  if L.need("main_bar", "main_s_in", "strip_length_ft", "width_in", "depth_in", "COVER_FOOTING"):
    leg = D(str(depth)) - 2 * D(str(c))
    L.put(derived("leg_in", leg, "depth less 2 covers"))
    cut = (D(str(W)) - 2 * D(str(c)) + 2 * leg) / 12
    lines.append(ExpectedLine("Main Bars", int(mb), _count(L, D(str(length)) * 12, D(str(ms))), cut, D(str(ms)), note="count = strip length / spacing"))
  elif mb is not None:
    lines.append(ExpectedLine("Main Bars", int(mb), None, None, D(str(ms)) if ms is not None else None))
    
  db, ds = L.val("dist_bar"), L.val("dist_s_in")
  if L.need("dist_bar", "dist_s_in", "strip_length_ft", "width_in", "COVER_FOOTING"):
    cut = D(str(length)) - 2 * D(str(c)) / 12
    lines.append(ExpectedLine("Distt. Bars", int(db), _count(L, D(str(W)) - 2 * D(str(c)), D(str(ds))), cut, D(str(ds)), note="count = (width - 2 covers) / spacing"))
  elif db is not None:
    lines.append(ExpectedLine("Distt. Bars", int(db), None, None, D(str(ds)) if ds is not None else None))
  return _finish(L, "FOOTING", mark, floor, lines)

def pad_footing(L: Ledger, mark: str, floor: str | None) -> Expected:
  lines: list = []
  c = L.val("COVER_FOOTING")
  for way, a, b in (("Bars along L", "length_in", "width_in"), ("Bars along B", "width_in", "length_in")):
    bar, s = L.val("pad_bar"), L.val("pad_s_in")
    if L.need("pad_bar", "pad_s_in", "length_in", "width_in", "depth_in", "COVER_FOOTING"):
      depth = D(str(L.val("depth_in")))
      leg = depth - 2 * D(str(c))
      cut = (D(str(L.val(a))) - 2 * D(str(c)) + 2 * leg) / 12
      lines.append(ExpectedLine(way, int(bar), _count(L, D(str(L.val(b))) - 2 * D(str(c)), D(str(s))), cut, D(str(s))))
    elif bar is not None:
      lines.append(ExpectedLine(way, int(bar)))
  return _finish(L, "FOOTING", mark, floor, lines)

def plinth_beam(L: Ledger, mark: str, floor: str | None) -> Expected:
  lines: list = []
  runs = L.val("runs_ft")
  for prefix, role in (("bottom", "Bottom Bars"), ("top", "Top Bars")):
    for n, bar, kind in _bars_of(L, prefix):
      if L.need("runs_ft", f"EMBEDMENT_{bar}") and runs:
        total_k, total_cut = 0, D(0)
        lap_ft = D(0)
        ok = True
        for r in runs:
          run = D(str(r))
          k, lap_ft = _bar_laps(L, run, bar)
          if k is None:
            ok = False
            L.need(f"LAP_{bar}", "stock_length_ft")
            break
          total_k += k
          total_cut += run
        if ok:
          lines.append(ExpectedLine(role, bar, D(n), total_cut, laps=total_k, lap_ft=lap_ft, note="count is bars in the whole run; cut is the sum of the runs"))
          continue
      lines.append(ExpectedLine(role, bar, D(n)))
      
  sb, mid = L.val("stirrup_bar"), L.val("stirrup_mid_in")
  if L.need("stirrup_bar", "stirrup_mid_in", "width_in", "depth_in", "COVER_COLUMN_BEAM", "runs_ft") and runs:
    count = sum((ceil_d(D(str(r)) * 12 / D(str(mid))) for r in runs), D(0))
    lines.append(ExpectedLine("Rings", int(sb), count, _tie_cut_ft(L, D(str(L.val("width_in"))), D(str(L.val("depth_in"))), D(str(L.val("COVER_COLUMN_BEAM"))), int(sb)), D(str(mid)), note="per segment"))
  return _finish(L, "PLINTH", mark, floor, lines)

def slab_panel(L: Ledger, mark: str, floor: str | None) -> Expected:
  lines: list = []
  c = L.val("COVER_SLAB_WALL")
  ly = L.val("ly_ft")
  sup = L.val("support_in")
  for role, bar_n, s_n, along, across in (("Main Bars", "main_bar", "main_s_in", "lx_ft", "ly_ft"), ("Distribution Bars", "dist_bar", "dist_s_in", "ly_ft", "lx_ft")):
    bar, s = L.val(bar_n), L.val(s_n)
    if L.need(bar_n, s_n, "lx_ft", "ly_ft", "COVER_SLAB_WALL", "support_in"):
      cut = D(str(L.val(along))) + (2 * (D(str(sup)) - D(str(c)))) / 12
      lines.append(ExpectedLine(role, int(bar), _count(L, D(str(L.val(across))) * 12, D(str(s))), cut, D(str(s)), note="clear span plus bearing less cover each end"))
    elif bar is not None:
      lines.append(ExpectedLine(role, int(bar), None, None, D(str(s)) if s is not None else None))
      
  tb = L.opt("top_bar")
  ts, tl = L.val("top_s_in") if tb is not None else None, L.val("top_len_ft") if tb is not None else None
  if tb is not None:
    if L.need("top_s_in", "top_len_ft", "ly_ft"):
      lines.append(ExpectedLine("Top Extra Bars", int(tb), _count(L, D(str(ly)) * 12, D(str(ts))), D(str(tl)), D(str(ts)), note="by printed length"))
    else:
      lines.append(ExpectedLine("Top Extra Bars", int(tb)))
  return _finish(L, "SLAB", mark, floor, lines)

def lintel(L: Ledger, mark: str, floor: str | None) -> Expected:
  lines: list = []
  width = L.val("opening_ft")
  rows = L.val("lintel_table")
  
  row = None
  if L.need("lintel_table", "opening_ft") and rows:
    row = next((r for r in sorted(rows, key=lambda r: r["upto_ft"]) if D(str(width)) <= D(str(r["upto_ft"]))), None)
    if row is None:
      L.blocked.append("lintel_table (no row covers this opening)")
  if row:
    L.put(derived("lintel_type", f"up to {row['upto_ft']} ft", "lintel table row chosen by opening width"))
    bearing = D(str(row.get("bearing_in", 0)))
    for n, bar in row["bars"]:
      lines.append(ExpectedLine("Main Bars", int(bar), D(n), D(str(width)) + 2 * bearing / 12))
    if row.get("stirrup_bar") and row.get("stirrup_s_in") and L.need("COVER_COLUMN_BEAM") and row.get("w_in") and row.get("d_in"):
      cut = _tie_cut_ft(L, D(str(row["w_in"])), D(str(row["d_in"])), D(str(L.val("COVER_COLUMN_BEAM"))), int(row["stirrup_bar"]))
      lines.append(ExpectedLine("Rings", int(row["stirrup_bar"]), ceil_d(D(str(width)) * 12 / D(str(row["stirrup_s_in"]))), cut, D(str(row["stirrup_s_in"]))))
  return _finish(L, "LINTEL", mark, floor, lines)

def tank(L: Ledger, mark: str, floor: str | None) -> Expected:
  lines: list = []
  c = L.val("COVER_SLAB_WALL")
  
  Lc, Bc, Hc, t = L.val("tank_len_ft"), L.val("tank_wid_ft"), L.val("tank_ht_ft"), L.val("wall_in")
  base = ("tank_len_ft", "tank_wid_ft", "tank_ht_ft", "wall_in", "COVER_SLAB_WALL")
  for face, bar_n, s_n, spec in (("Bottom Slab Main", "bottom_main_bar", "bottom_main_s_in", "slab_a"), ("Bottom Slab Distribution", "bottom_dist_bar", "bottom_dist_s_in", "slab_b"),
      ("Walls Vertical", "wall_v_bar", "wall_v_s_in", "wall_v"), ("Walls Horizontal", "wall_h_bar", "wall_h_s_in", "wall_h"),
      ("Top Slab Main", "top_main_bar", "top_main_s_in", "slab_a"), ("Top Slab Distribution", "top_dist_bar", "top_dist_s_in", "slab_b")):
    bar, s = L.val(bar_n), L.val(s_n)
    if not L.need(*base) or bar is None or s is None:
      L.need(bar_n, s_n)
      lines.append(ExpectedLine(face, int(bar) if bar is not None else None))
      continue
    Lo, Bo = D(str(Lc)) * 12 + 2 * D(str(t)), D(str(Bc)) * 12 + 2 * D(str(t))
    cv = D(str(c))
    H = D(str(Hc)) * 12
    if spec == "slab_a":
      count, cut = _count(L, Bo - 2 * cv, D(str(s))), (Lo - 2 * cv) / 12
    elif spec == "slab_b":
      count, cut = _count(L, Lo - 2 * cv, D(str(s))), (Bo - 2 * cv) / 12
    elif spec == "wall_v":
      count, cut = _count(L, 2 * (Lo + Bo) - 8 * cv, D(str(s))), (H + D(str(t)) - 2 * cv) / 12
    else:
      count, cut = _count(L, H - 2 * cv, D(str(s))) * 2, (Lo + Bo - 4 * cv) / 12
    lines.append(ExpectedLine(face, int(bar), count, cut, D(str(s))))
  return _finish(L, "TANK", mark, floor, lines, ["sizes from the schedule's sheet title unless the architecture set is given"])

FUNCTIONS = {"COLUMN": column, "BEAM": beam, "STRIP_FOOTING": strip_footing, "PAD_FOOTING": pad_footing, "PLINTH": plinth_beam, "SLAB": slab_panel, "LINTEL": lintel, "TANK": tank}
