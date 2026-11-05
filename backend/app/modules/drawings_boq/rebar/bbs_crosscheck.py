from __future__ import annotations
import hashlib
import re
from pathlib import Path
from dataclasses import dataclass, field
from decimal import Decimal as D
from app.engine.measure import rebar_expect as RX
from app.modules.drawings_boq.rebar.bbs_audit import Finding
from app.modules.drawings_boq.rebar import expect_source as ES
import yaml
from app.modules.drawings_boq.rebar.member_source import norm_mark
from app.modules.drawings_boq.takeoff.model.storeys import heights_ft as storey_heights_ft

CROSSCHECK_VERSION = "L4.1"
RULES_PATH = Path(__file__).with_name("rebar_audit_rules.yaml")
ZERO = D(0)
FLOORED = ("COLUMN", "BEAM", "SLAB")
LINK_ROLES = ("rings",)
LAP_NAME = re.compile(r"^LAP_\d+$")
DEFAULT_BANDS = {"count": {"bars": 1, "share": 0.02}, "cut_in": 2, "weight_share": 0.03, "fit_aggregate_in": 0.75, "fit_min_gap_in": 1, "extras_full_share": 0.9, "spacing_tol_in": 0.01}

@dataclass
class XFinding(Finding):
  drawing_ref: dict | None = None
  effect_basis: str | None = None
  convention: dict | None = None

@dataclass
class CrossBands:
  count_bars: D
  count_share: D
  cut_in: D
  weight_share: D
  fit_aggregate_in: D
  fit_min_gap_in: D
  extras_full_share: D
  spacing_tol_in: D
  digest: str

def load_cross_bands(text: str | None = None) -> CrossBands:
  raw = text if text is not None else RULES_PATH.read_text(encoding="utf-8")
  data = {**DEFAULT_BANDS, **(yaml.safe_load(raw) or {})}
  count = {**DEFAULT_BANDS["count"], **(data.get("count") or {})}
  return CrossBands(count_bars=D(str(count["bars"])), count_share=D(str(count["share"])), cut_in=D(str(data["cut_in"])), weight_share=D(str(data["weight_share"])),
    fit_aggregate_in=D(str(data["fit_aggregate_in"])), fit_min_gap_in=D(str(data["fit_min_gap_in"])), extras_full_share=D(str(data["extras_full_share"])),
    spacing_tol_in=D(str(data["spacing_tol_in"])), digest=hashlib.sha256(raw.encode("utf-8")).hexdigest())

def role_key(text: str | None) -> str:
  t = re.sub(r"\([^)]*\)", "", (text or "").lower())
  t = t.replace("distt.", "dist").replace("distribution", "dist")
  return re.sub(r"[^a-z]", "", t)

def unit_kg(dia) -> D:
  return RX.kg_per_ft(int(dia))

def kg_of(members, each, cut, dia) -> D:
  if None in (each, cut, dia):
    return ZERO
  return (members if members is not None else D(1)) * each * cut * unit_kg(dia)

def r2(x: D | None) -> D | None:
  return None if x is None else x.quantize(D("0.01"))

def _ref(row, sheet_names: dict) -> dict:
  return {"page": row.page, "sheet": row.sheet, "sheet_name": sheet_names.get(row.sheet), "member": row.member, "sr": row.sr, "y": row.y, "description": row.description}

def _row_note(row, index: int) -> dict:
  return {"index": index, "page": row.page, "y": row.y, "sr": row.sr, "description": row.description, "kg": str(row.total_kg) if row.total_kg is not None else None}

def _inp(job: dict, name: str):
  for i in job["inputs"]:
    if i.name == name:
      return i.value
  return None

def _flagged(job: dict, name: str) -> bool:
  for i in job["inputs"]:
    if i.name == name:
      return bool(i.flag and "UNSURE" in i.flag)
  return False

def _fmt(x, places: int = 2) -> str:
  return f"{D(str(x)):.{places}f}"

def _num(x) -> D | None:
  return None if x is None else D(str(x))

def _tol_count(bands: CrossBands, expected: D) -> D:
  return min(bands.count_bars, bands.count_share * expected)

@dataclass
class RowState:
  index: int
  row: object
  dia: int | None
  each: D | None
  cut: D | None
  start_kg: D
  items: list = field(default_factory=list)

  def kg(self) -> D:
    return kg_of(self.row.members, self.each, self.cut, self.dia)

def drawing_refs(sheets: list) -> dict:
  out: dict = {}
  
  for sh in sheets:
    meta = sh.get("meta") or {}
    no = (meta.get("identity") or {}).get("sheet_no")
    base = {"pdf_key": sh["pdf_key"], "page": sh["page_no"], "sheet_no": no}
    tables = meta.get("structure_tables") or {}
    for c in (tables.get("column_schedule") or {}).get("cells") or []:
      if c.get("mark"):
        out.setdefault(("COLUMN", norm_mark(c["mark"]), c.get("floor")), {**base, "what": f"column schedule {c['mark']} {c.get('floor') or ''}".strip(), "uv": c.get("cell_uv"), "anchor_native": c.get("anchor_native")})
    for s in (tables.get("beam_sections") or {}).get("sections") or []:
      if s.get("mark"):
        out.setdefault(("BEAM", norm_mark(s["mark"]), None), {**base, "what": f"beam section {s['mark']}", "uv": None, "anchor_native": s.get("anchor_native")})
  return out

def ref_for(refs: dict, cls: str, mark: str, floor: str | None) -> dict | None:
  nm = norm_mark(mark)
  return refs.get((cls, nm, floor)) or refs.get((cls, nm, None)) or next((v for (c, m, _f), v in refs.items() if c == cls and m == nm), None)

@dataclass
class CrossResult:
  findings: list = field(default_factory=list)
  totals: dict = field(default_factory=dict)
  by_sheet: dict = field(default_factory=dict)
  row_expect: dict = field(default_factory=dict)

def index_results(results: list) -> dict:
  idx: dict = {}
  for job, e in results:
    idx.setdefault((job["cls"], norm_mark(job["mark"])), []).append((job, e))
  return idx

def _find_expectation(idx: dict, el: dict):
  cands = idx.get((el.get("class"), norm_mark(el.get("mark"))), [])
  if not cands:
    return None
  floor = el.get("floor")
  exact = [c for c in cands if c[0]["floor"] == floor]
  return (exact or [c for c in cands if c[0]["floor"] is None] or cands)[0]

def _below_ground(sheet_name: str) -> bool:
  up = sheet_name.upper()
  return "SUB-STRUCTURE" in up or "SUB STRUCTURE" in up or "BASEMENT" in up

def _rework_height(job: dict, decisions: dict):
  heights = storey_heights_ft(decisions.get("storeys")) or decisions.get("floor_heights_ft") or {}
  inputs = [i for i in job["inputs"] if i.name != "height_ft"]
  if "BASEMENT" in heights:
    inputs.append(RX.defaulted("height_ft", D(str(heights["BASEMENT"])), "decision storeys (BASEMENT)", None))
  new = {**job, "inputs": inputs}
  return new, ES.run_jobs([new])[0][1]

def _signature(e) -> tuple:
  return tuple((role_key(l.role), l.dia, str(l.count), str(l.cut_ft)) for l in e.lines)

def _variant_cut(job: dict, e, line_no: int, overrides: dict, lap_same: str | None = None) -> D | None:
  inputs = []
  seen = set()
  for i in job["inputs"]:
    seen.add(i.name)
    inputs.append(RX.Input(i.name, overrides[i.name], RX.DEFAULTED, "switched off to find the cause", "VARIANT") if i.name in overrides else i)
  for name, value in overrides.items():
    if name not in seen:
      inputs.append(RX.Input(name, value, RX.DEFAULTED, "switched on to find the cause", "VARIANT"))
  if lap_same:
    value = next((i.value for i in inputs if i.name == lap_same), None)
    if value is not None:
      inputs = [RX.Input(i.name, value, i.state, i.source, i.flag) if LAP_NAME.match(i.name) else i for i in inputs]
  try:
    again = ES.run_jobs([{**job, "inputs": inputs}])[0][1]
  except Exception:
    return None
  return again.lines[line_no].cut_ft if line_no < len(again.lines) else None

def _cover_of(job: dict, line) -> D | None:
  name = "COVER_FOOTING" if job["cls"] == "FOOTING" else "COVER_SLAB_WALL" if job["cls"] in ("SLAB", "TANK") else "COVER_COLUMN_BEAM"
  v = _inp(job, name)
  return None if v is None else D(str(v))

def _cut_cause(job: dict, e, line_no: int, line, billed: D, bands: CrossBands, is_link: bool) -> tuple:
  tol = bands.cut_in / 12
  names = [i.name for i in job["inputs"]]
  variants = []
  covers = {n: 0 for n in names if n.startswith("COVER_")}
  embeds = {n: 0 for n in names if n.startswith("EMBEDMENT_")}
  laps = {n: 0 for n in names if LAP_NAME.match(n)}
  
  if is_link:
    variants.append(("the outside perimeter of the member is used (no cover deducted, no hooks added)", {"link_cut_basis": "PERIMETER"}, None, "METHOD", {"key": "link_cut_basis", "value": "PERIMETER"}))
  if covers:
    variants.append(("cover ignored", covers, None, "ERROR", None))
  if embeds:
    variants.append(("embedment ignored", embeds, None, "ERROR", None))
  if laps:
    variants.append(("lap not added", laps, None, "ERROR", None))
    for n in sorted(laps):
      value = _inp(job, n)
      variants.append((f"the lap of #{n[4:]} bars ({float(value):g} in) used for every bar size", {}, n, "CHECK", None))
      
  for text, over, same, klass, conv in variants:
    cut = _variant_cut(job, e, line_no, over, same)
    if cut is not None and abs(cut - billed) <= tol:
      return klass, text, conv
  cover = _cover_of(job, line)
  if cover and line.cut_ft is not None:
    for places in (2, 4, 6):
      if abs(line.cut_ft + places * cover / 12 - billed) <= tol:
        return "ERROR", f"cover ({cover:g} in) not deducted at {places} place(s)", None
  return "CHECK", None, None

def _zones_expected(job: dict, row, span_in: D, decisions: dict) -> tuple:
  cls = job["cls"]
  end = _inp(job, "tie_end_in" if cls == "COLUMN" else "stirrup_end_in")
  mid = _inp(job, "tie_mid_in" if cls == "COLUMN" else "stirrup_mid_in")
  if end is None or mid is None:
    return None, None
  end, mid = D(str(end)), D(str(mid))
  if cls == "COLUMN":
    l0d = decisions.get("column_l0")
    if l0d is not None:
      l0 = D(str(l0d))
    else:
      w, d = _inp(job, "size_w_in"), _inp(job, "size_d_in")
      l0 = max(D(str(max(w, d))) if w and d else ZERO, span_in / 6, D(18))
  else:
    l0 = span_in / 4
  return 2 * RX.ceil_d(l0 / end) + RX.ceil_d(max(span_in - 2 * l0, ZERO) / mid), f"l0 {l0.quantize(D('0.1'))} in"

def _fit_faces(n: int) -> tuple | None:
  if n < 4 or n % 2:
    return None
  s = (n + 4) // 2
  a = (s + 1) // 2
  b = s - a
  return (a, b) if b >= 2 else None

def crosscheck(rows: list, sheet_names: dict, match, results: list, members: list, decisions: dict, bands: CrossBands, refs: dict | None = None,
  conflicts: list | None = None) -> CrossResult:
  out = CrossResult()
  refs = refs or {}
  idx = index_results(results)
  conflict_marks = {norm_mark(c["mark"]) for c in conflicts or []}
  states = {i: RowState(i, r, r.dia, r.each, r.cut_ft, r.total_kg or ZERO) for i, r in enumerate(rows)}
  
  raw: list = []   
  skipped = {"combined": 0, "no_line": 0, "no_expectation": 0, "not_matched": 0, "blocked": {}}
  compared = {"rows": 0, "lines": 0}
  expected_kg_by_sheet: dict = {}
  billed_kg_by_sheet: dict = {}
  sources: dict = {}
  for m in members:
    sources.setdefault((m.cls, norm_mark(m.mark), m.floor), set()).add(m.source)

  def add(code, klass, i, **kw):
    raw.append({"code": code, "class": klass, "row": i, **kw})

  groups: dict = {}
  for it in match.items:
    groups.setdefault((rows[it.row_index].sheet, rows[it.row_index].member), []).append(it)
  for (sheet, member), its in groups.items():
    first = its[0]
    if first.kind != "MATCH" or not first.elements:
      skipped["not_matched"] += len(its)
      continue
    found = [_find_expectation(idx, el) for el in first.elements]
    found = [f for f in found if f is not None]
    if not found:
      skipped["no_expectation"] += len(its)
      continue
    if len({_signature(e) for _, e in found}) > 1:
      skipped["combined"] += len(its)
      continue
    
    job, e = found[0]
    if job["cls"] == "COLUMN" and _below_ground(sheet_names.get(sheet, "")) and job["floor"] != "BASEMENT":
      job, e = _rework_height(job, decisions)
    by_role_lines: dict = {}
    for n, line in enumerate(e.lines):
      by_role_lines.setdefault(role_key(line.role), []).append((n, line))
    by_role_rows: dict = {}
    for it in sorted(its, key=lambda t: (rows[t.row_index].sr or 0, t.row_index)):
      by_role_rows.setdefault(role_key(rows[it.row_index].description), []).append(it.row_index)
    for role, row_ids in by_role_rows.items():
      lines = by_role_lines.get(role, [])
      for k, i in enumerate(row_ids):
        if k >= len(lines) and job["cls"] != "COLUMN":
          skipped["no_line"] += 1
          continue
        n, line = lines[k % len(lines)]
        _check_pair(out, add, states[i], rows[i], job, e, n, line, role, k, lines, row_ids, rows, states, decisions, bands, skipped, compared, conflict_marks)
        sheet_idx = rows[i].sheet
        if line.kg is not None:
          expected_kg_by_sheet[sheet_idx] = expected_kg_by_sheet.get(sheet_idx, ZERO) + (rows[i].members or D(1)) * line.kg
          billed_kg_by_sheet[sheet_idx] = billed_kg_by_sheet.get(sheet_idx, ZERO) + (rows[i].total_kg or ZERO)

  for it in match.items:
    row = rows[it.row_index]
    if it.kind == "EXTRA":
      has_els = bool(it.elements)
      add("FLOOR_NOT_IN_SCHEDULE" if has_els else "EXTRA_MEMBER", "ERROR" if has_els else "EXTRA", it.row_index, reason=it.reason, elements=it.elements, floors=it.floors)
    elif it.kind == "ASK":
      add("NO_DETAIL", "UNVERIFIABLE", it.row_index, reason=it.reason, family=it.family)
    elif it.kind == "MATCH" and it.method == "USER":
      for el in it.elements:
        key = (el.get("class"), norm_mark(el.get("mark")), el.get("floor"))
        if el.get("class") in FLOORED and "SCHEDULE" not in sources.get(key, set()) and any(k[0] == key[0] and k[1] == key[1] and "SCHEDULE" in v for k, v in sources.items()):
          add("FLOOR_NOT_IN_SCHEDULE", "CONFLICT", it.row_index, reason="confirmed by the user as drawn on this floor, but the schedule cell is blank", elements=it.elements, floors=it.floors)
          break
    elif it.kind == "MATCH" and it.method == "FAMILY_MARK":
      for el in it.elements:
        key = (el.get("class"), norm_mark(el.get("mark")), el.get("floor"))
        src = sources.get(key, set())
        if el.get("class") == "COLUMN" and src and "SCHEDULE" not in src and "PLANTED" in src and any(k[0] == "COLUMN" and k[1] == key[1] and "SCHEDULE" in v for k, v in sources.items()):
          add("FLOOR_NOT_IN_SCHEDULE", "CONFLICT", it.row_index, reason="the plan draws this column on the floor, the schedule cell is blank", elements=it.elements, floors=it.floors)
          break
  for miss in match.missing:
    add("MISSING_MEMBER", "MISSING", None, reason=miss.get("reason"), element=miss)

  per_sheet_floors: dict = {}
  for it in match.items:
    if it.kind == "MATCH" and it.method == "ROOM_PANEL" and it.elements:
      per_sheet_floors.setdefault(rows[it.row_index].sheet, []).append((it.row_index, it.elements[0].get("floor"), it.floors))
  for sheet, lst in per_sheet_floors.items():
    wrong = [(i, f, fl) for i, f, fl in lst if f and fl and f not in fl]
    if lst and len(wrong) / len(lst) >= 0.6:
      add("LABEL_FLOOR", "NAMING", wrong[0][0], reason=f"the sheet label says {', '.join(wrong[0][2]).lower()} but its rows match panels on the {wrong[0][1].lower()} floor", rows_wrong=[w[0] for w in wrong], sheet_only=sheet)

  stock_dec = decisions.get("stock_length_ft")
  stock = D(str(stock_dec)) if stock_dec is not None else RX.STOCK_DEFAULT_FT
  lap_rules = _rules_from(results)
  for i, row in enumerate(rows):
    st = states[i]
    if st.cut is None or st.cut <= stock or st.dia is None or row.notes and any("lap" in str(n).lower() for n in row.notes):
      continue
    lap_in = lap_rules.get(f"LAP_{st.dia}")
    if lap_in is None:
      continue
    k = RX.laps(st.cut, stock, D(str(lap_in)))
    if k:
      add("LAPS_MISSING", "ERROR", i, laps=k, lap_in=D(str(lap_in)), stock=stock, stock_assumed=stock_dec is None)

  _lap_by_size(add, rows, states, match, lap_rules)

  for c in conflicts or []:
    add("SIZE_CONFLICT", "CONFLICT", None, conflict=c)

  for i, line in compared.get("lines_of", {}).items():
    st = states[i]
    each = st.each if line.count is not None else None
    cut = st.cut if line.cut_ft is not None else None
    out.row_expect[i] = {"dia": st.dia if line.dia is not None else None, "each": None if each is None else str(each), "cut": None if cut is None else str(cut),
      "kg": str(r2(st.kg())) if None not in (each, cut, st.dia) else None}
  out.totals["compared_rows"] = compared["rows"]
  out.totals["compared_lines"] = compared["lines"]
  out.totals["skipped_combined_rows"] = skipped["combined"]
  out.totals["skipped_no_line_rows"] = skipped["no_line"]
  out.totals["skipped_no_expectation_rows"] = skipped["no_expectation"]
  out.totals["skipped_not_matched_rows"] = skipped["not_matched"]
  out.totals["unchecked_blockers"] = dict(sorted(skipped["blocked"].items(), key=lambda t: -t[1]))
  _assemble(out, raw, rows, sheet_names, states, refs, results, bands, decisions, match)
  for sh, idx_name in sheet_names.items():
    out.by_sheet[sh] = {"name": idx_name, "rows": sum(1 for r in rows if r.sheet == sh), "billed_kg": str(sum((r.total_kg or ZERO for r in rows if r.sheet == sh), ZERO).quantize(D("0.01"))),
      "compared_billed_kg": str(r2(billed_kg_by_sheet.get(sh, ZERO))), "expected_kg": str(r2(expected_kg_by_sheet.get(sh, ZERO)))}
  return out

def _rules_from(results: list) -> dict:
  for job, _e in results:
    return {i.name: i.value for i in job["inputs"] if i.name.startswith(("LAP_", "COVER_", "EMBEDMENT_"))}
  return {}

def _lap_by_size(add, rows: list, states: dict, match, lap_rules: dict) -> None:
  by_sheet: dict = {}
  for it in match.items:
    row = rows[it.row_index]
    if it.kind == "MATCH" and row.description.lower().startswith("vertical") and it.family == "COLUMN":
      by_sheet.setdefault(row.sheet, []).append(it.row_index)
  for sheet, ids in by_sheet.items():
    dias: dict = {}
    
    for i in ids:
      st = states[i]
      if st.dia is not None and st.each is not None:
        dias[st.dia] = dias.get(st.dia, ZERO) + st.each * (rows[i].members or D(1))
    if len(dias) < 2:
      continue
    ref = max(dias, key=lambda d: dias[d])
    ref_cuts = {states[i].cut for i in ids if states[i].dia == ref and states[i].cut is not None}
    for i in ids:
      st = states[i]
      if st.dia is None or st.dia == ref or st.cut not in ref_cuts or st.cut is None:
        continue
      big, small = lap_rules.get(f"LAP_{st.dia}"), lap_rules.get(f"LAP_{ref}")
      if big is None or small is None or D(str(big)) <= D(str(small)):
        continue
      add("CUT_MISMATCH", "CHECK", i, lap_by_size=True, ref_dia=ref, longer_by_ft=(D(str(big)) - D(str(small))) / 12)

def _check_pair(out, add, st: RowState, row, job, e, n, line, role, k, lines, row_ids, rows, states, decisions, bands, skipped, compared, conflict_marks) -> None:
  i = st.index
  compared["rows"] += 1
  compared["lines"] += 1
  compared.setdefault("lines_of", {})[i] = line
  def blocked(name):
    skipped["blocked"][name] = skipped["blocked"].get(name, 0) + 1
  # diameter
  if line.dia is not None and st.dia is not None and st.dia != line.dia:
    before = st.kg()
    st.dia = line.dia
    add("DIA_MISMATCH", "ERROR", i, effect=st.kg() - before, billed=f"#{row.dia}", expected=f"#{line.dia}", job=job, line=line)
  
  if job["cls"] == "COLUMN" and role == "verticalbars" and row.dia is not None and row.each is not None:
    w, d, c, tie = _inp(job, "size_w_in"), _inp(job, "size_d_in"), _inp(job, "COVER_COLUMN_BEAM"), _inp(job, "tie_bar")
    faces = _fit_faces(int(row.each))
    if None not in (w, d, c) and faces:
      bar = D(row.dia) * RX.IN_PER_BAR_NO
      tie_d = D(int(tie)) * RX.IN_PER_BAR_NO if tie else ZERO
      gap = max(bands.fit_min_gap_in, bar, D("1.33") * bands.fit_aggregate_in)
      for count, side in zip(faces, sorted((D(str(w)), D(str(d))), reverse=True)):
        need = count * bar + (count - 1) * gap
        clear = side - 2 * D(str(c)) - 2 * tie_d
        if need > clear:
          add("BARS_DO_NOT_FIT", "ERROR", i, need=need, clear=clear, count=count, side=side, job=job)
          break
  
  zoned_done = False
  if role in LINK_ROLES and row.spacing_in is not None:
    end = _inp(job, "tie_end_in" if job["cls"] == "COLUMN" else "stirrup_end_in")
    mid = _inp(job, "tie_mid_in" if job["cls"] == "COLUMN" else "stirrup_mid_in")
    if end is not None and mid is not None and D(str(end)) != D(str(mid)) and decisions.get("tie_zones") != "AVERAGE":
      sp = D(str(row.spacing_in))
      if sp not in (D(str(end)), D(str(mid))) or "consider" in " ".join(str(x) for x in row.notes).lower():
        span_in = None
        basis = "ESTIMATE"
        if job["cls"] == "COLUMN" and _inp(job, "height_ft") is not None:
          span_in, basis = D(str(_inp(job, "height_ft"))) * 12, "EXPECTATION"
        elif job["cls"] == "BEAM" and _inp(job, "span_ft") is not None:
          span_in, basis = D(str(_inp(job, "span_ft"))) * 12, "EXPECTATION"
        if span_in is None and st.each is not None:
          span_in = st.each * sp
        if span_in:
          zoned, how = _zones_expected(job, row, span_in, decisions)
          if zoned is not None:
            before = st.kg()
            st.each = zoned
            add("ZONES_AVERAGED", "METHOD", i, effect=st.kg() - before, billed=f"{row.each} at {sp:g} in", expected=f"{zoned} ({end:g} in at the ends, {mid:g} in in the middle; {how})", basis=basis,
              notes=[str(x) for x in row.notes], printed=f"#{line.dia}@{end:g}\"/{mid:g}\"")
            zoned_done = True

  if line.count is not None and st.each is not None:
    exp_count = line.count
    tol = _tol_count(bands, exp_count)
    if abs(st.each - exp_count) > tol:
      plus_one = abs(st.each - (exp_count + 1)) <= tol and not decisions.get("bar_count_plus_one")
      before = st.kg()
      st.each = exp_count
      add("COUNT_MISMATCH", "METHOD" if plus_one else "ERROR", i, effect=st.kg() - before, billed=f"{row.each}", expected=f"{exp_count}" + (" (one more with bar_count_plus_one)" if plus_one else ""),
        plus_one=plus_one, job=job, line=line)
  else:
    for nme in e.blocked:
      blocked(nme)
  
  if line.spacing_in is not None and row.spacing_in is not None and not (role in LINK_ROLES and (zoned_done or decisions.get("tie_zones") != "AVERAGE")):
    if abs(D(str(row.spacing_in)) - line.spacing_in) > bands.spacing_tol_in:
      add("SPACING_MISMATCH", "ERROR", i, billed=f"{row.spacing_in} in", expected=f"{line.spacing_in} in", job=job, line=line)
  
  is_extra = "(extra" in line.role.lower() and "full length" not in line.role.lower()
  if is_extra and st.cut is not None and k >= 1 and decisions.get("curtail_extras") is not False and _inp(job, "curtail_extras"):
    through = [j for j in row_ids[:k] if states[j].cut is not None]
    if through:
      ref_cut = states[through[0]].cut
      if st.cut >= bands.extras_full_share * ref_cut:
        frac = _inp(job, "CURTAILMENT_TOP" if line.role.lower().startswith("top") else "CURTAILMENT_BOTTOM")
        bar_d = _inp(job, "EMBEDMENT_%s" % st.dia) if st.dia else None
        if frac in RX.FRACTIONS and bar_d is not None:
          span = ref_cut - 2 * D(str(bar_d)) / 12
          if span <= 0 and line.cut_ft is None:
            return
          basis = "ESTIMATE"
          if line.cut_ft is not None:
            exp_cut, basis = line.cut_ft, "EXPECTATION"
          elif line.role.lower().startswith("top"):
            exp_cut = span * RX.FRACTIONS[frac]
          else:
            exp_cut = span * (1 - 2 * RX.FRACTIONS[frac])
          before = st.kg()
          st.cut = exp_cut
          add("EXTRAS_FULL_LENGTH", "ERROR", i, effect=st.kg() - before, billed=f"{row.cut_ft} ft", expected=f"{_fmt(exp_cut)} ft ({frac}{'' if line.role.lower().startswith('top') else ' per end'})", basis=basis, job=job, line=line,
            span=span)
          return
 
  if line.cut_ft is not None and st.cut is not None and not is_extra and norm_mark(job["mark"]) not in conflict_marks:
    billed = st.cut
    if abs(billed - line.cut_ft) * 12 > bands.cut_in:
      klass, cause, conv = _cut_cause(job, e, n, line, billed, bands, role in LINK_ROLES)
      before = st.kg()
      st.cut = line.cut_ft
      add("CUT_MISMATCH", klass, i, effect=st.kg() - before, billed=f"{row.cut_ft} ft", expected=f"{_fmt(line.cut_ft)} ft", cause=cause, convention=conv, job=job, line=line)
  elif line.cut_ft is None:
    for nme in e.blocked:
      blocked(nme)

TEXT = {
  "DIA_MISMATCH": "bar diameter against the drawing",
  "COUNT_MISMATCH": "bars per member against the drawing",
  "SPACING_MISMATCH": "spacing against the drawing",
  "CUT_MISMATCH": "cut length against the drawing",
  "LAPS_MISSING": "a run longer than the stock bar has no lap length",
  "ZONES_AVERAGED": "ties or stirrups at one average spacing where the drawing prints zones",
  "EXTRAS_FULL_LENGTH": "extra bars billed full length where the drawing curtails them",
  "FLOOR_NOT_IN_SCHEDULE": "a row bills a mark on a floor whose schedule cell is blank",
  "SIZE_CONFLICT": "the drawing's text and sketch give different sizes",
  "BARS_DO_NOT_FIT": "the billed bars do not fit across the member",
  "MISSING_MEMBER": "a drawing member with no row",
  "EXTRA_MEMBER": "a row with no drawing member",
  "NO_DETAIL": "a row whose member has no drawing detail",
  "LABEL_FLOOR": "the sheet label disagrees with the matched floor",
}

def _group_key(h: dict, rows: list) -> tuple:
  code = h["code"]
  if code == "MISSING_MEMBER":
    el = h["element"]
    return (code, el.get("class"), el.get("mark"), el.get("floor"))
  if code == "SIZE_CONFLICT":
    c = h["conflict"]
    return (code, c["mark"])
  row = rows[h["row"]]
  if code == "ZONES_AVERAGED":
    return (code, row.sheet)
  if code == "NO_DETAIL":
    return (code, row.sheet)
  if code == "LABEL_FLOOR":
    return (code, h["sheet_only"])
  if code == "CUT_MISMATCH" and h.get("lap_by_size"):
    return (code, row.sheet, "lap_by_size")
  if code == "CUT_MISMATCH" and h.get("convention") is not None:
    return (code, row.sheet, "convention", h.get("cause"))
  extra = (h.get("cause"), h.get("class")) if code == "CUT_MISMATCH" else ()
  return (code, row.sheet, row.member) + extra

def _assemble(out: CrossResult, raw: list, rows: list, sheet_names: dict, states: dict, refs: dict, results: list, bands: CrossBands, decisions: dict, match) -> None:
  groups: dict = {}
  for h in raw:
    groups.setdefault(_group_key(h, rows), []).append(h)
  for key, hs in groups.items():
    f = _finding(key, hs, rows, sheet_names, refs, bands, decisions)
    if f is not None:
      out.findings.append(f)
  counts: dict = {}
  for f in out.findings:
    counts[f.code] = counts.get(f.code, 0) + 1
  out.totals["by_code"] = counts
  out.totals["by_class"] = {c: sum(1 for f in out.findings if f.finding_class == c) for c in ("ERROR", "CONFLICT", "METHOD", "CHECK", "MISSING", "EXTRA", "UNVERIFIABLE", "NAMING")}
  
  net = {}
  for f in out.findings:
    if f.diff_kg is not None:
      net[f.finding_class] = net.get(f.finding_class, ZERO) + f.diff_kg
  out.totals["net_effect_kg_by_class"] = {k: str(v.quantize(D("0.01"))) for k, v in net.items()}
  out.totals["net_effect_kg"] = str(sum(net.values(), ZERO).quantize(D("0.01")))
  out.totals["net_effect_kg_error_only"] = str(net.get("ERROR", ZERO).quantize(D("0.01")))
  out.totals["match_stats"] = {k: v for k, v in match.stats.items() if k in ("rows", "matched", "ask", "extra", "matched_without_asking", "share_without_asking")}

def _rows_note(idxs: list, rows: list) -> list:
  return [_row_note(rows[i], i) for i in idxs]

def _finding(key: tuple, hs: list, rows: list, sheet_names: dict, refs: dict, bands: CrossBands, decisions: dict):
  code = key[0]
  h0 = hs[0]
  klass = h0["class"]
  if code == "MISSING_MEMBER":
    el = h0["element"]
    ref = ref_for(refs, el.get("class"), el.get("mark"), el.get("floor"))
    return XFinding(code, klass, TEXT[code], {"page": None, "sheet": None, "sheet_name": None, "member": f"{el.get('mark')}", "sr": None, "y": None, "rows": []},
      bbs_value="no row", trace_value=f"{el.get('class', '').lower()} {el.get('mark')} on {str(el.get('floor') or 'the plan').lower()}", diff_kg=None, confidence=D("0.7"),
      question=h0.get("reason"), drawing_ref=ref)
  if code == "SIZE_CONFLICT":
    c = h0["conflict"]
    ref = {"pdf_key": c.get("pdf_key"), "page": c.get("page"), "sheet_no": c.get("sheet_no"), "what": f"column schedule {c['mark']}", "uv": c.get("cell_uv"), "anchor_native": c.get("anchor_native")}
    follows = c.get("bbs_follows")
    return XFinding(code, "CONFLICT", TEXT[code], {"page": None, "sheet": None, "sheet_name": None, "member": c["mark"], "sr": None, "y": None, "rows": c.get("rows") or []},
      bbs_value=f"schedule follows the {follows}" if follows else None, trace_value=f"printed {c['printed_in'][0]:g}x{c['printed_in'][1]:g} in, sketched {c['sketch_in'][0]:g}x{c['sketch_in'][1]:g} in",
      confidence=D("0.8"), question=f"{c['mark']}: the schedule cell prints {c['printed_in'][0]:g}x{c['printed_in'][1]:g} in and its section sketch is {c['sketch_in'][0]:g}x{c['sketch_in'][1]:g} in. Which size is right?",
      drawing_ref=ref)
    
  idxs = sorted({h["row"] for h in hs if h.get("row") is not None})
  row = rows[idxs[0]]
  kg_total = sum((rows[i].total_kg or ZERO for i in idxs), ZERO)
  ref = {**_ref(row, sheet_names), "rows": _rows_note(idxs, rows)}
  effect_sum = sum((h["effect"] for h in hs if h.get("effect") is not None), ZERO) if any(h.get("effect") is not None for h in hs) else None
  job = h0.get("job")
  dref = None
  if job is not None:
    dref = ref_for(refs, job["cls"], job["mark"], job["floor"])
  member = row.member
  basis = "EXPECTATION" if all(h.get("basis", "EXPECTATION") == "EXPECTATION" for h in hs) else "ESTIMATE"
  if code == "DIA_MISMATCH":
    return XFinding(code, klass, TEXT[code], ref, bbs_value=h0["billed"], trace_value=h0["expected"], diff_kg=r2(effect_sum), confidence=D("1"),
      question=f"{member}: the drawing gives {h0['expected']}; the schedule bills {h0['billed']}.", drawing_ref=dref, effect_basis="EXPECTATION")
  if code == "COUNT_MISMATCH":
    plus = h0.get("plus_one")
    conv = {"key": "bar_count_plus_one", "value": True} if plus else None
    return XFinding(code, klass, TEXT[code] if not plus else "bar counts that add one", ref, bbs_value=h0["billed"], trace_value=h0["expected"], diff_kg=r2(effect_sum),
      confidence=D("0.9"), question=(f"{member}: the schedule adds one bar to the count. Is that the project's convention?" if plus else f"{member}: the drawing gives {h0['expected']} bars; the schedule bills {h0['billed']}."),
      drawing_ref=dref, effect_basis="EXPECTATION", convention=conv)
  if code == "SPACING_MISMATCH":
    return XFinding(code, klass, TEXT[code], ref, bbs_value=h0["billed"], trace_value=h0["expected"], confidence=D("0.9"),
      question=f"{member}: the drawing gives {h0['expected']} spacing; the schedule bills {h0['billed']}.", drawing_ref=dref, effect_basis=None)
  if code == "CUT_MISMATCH":
    if h0.get("lap_by_size"):
      longer = h0["longer_by_ft"]
      effect = sum((longer * (states_each(rows[h["row"]]) ) * unit_kg(rows[h["row"]].dia) for h in hs), ZERO)
      mem = ", ".join(sorted({str(rows[h["row"]].member) for h in hs}))
      ref["members"] = sorted({str(rows[h["row"]].member) for h in hs})
      return XFinding(code, "CHECK", "bars of a larger size billed at the cut length of the smaller size, although the printed lap is longer", ref,
        bbs_value=f"same cut as #{h0['ref_dia']} bars", trace_value=f"{_fmt(longer)} ft longer for the larger lap", diff_kg=r2(effect), confidence=D("0.7"),
        question=f"{mem}: the larger bars have the same cut length as the #{h0['ref_dia']} bars of the same floor, but their lap (S-0A) is longer. Is the lap left out of the larger bars?", drawing_ref=None, effect_basis="ESTIMATE")
    cause = h0.get("cause")
    conv = h0.get("convention")
    
    text = TEXT[code] if not cause else f"cut length against the drawing: {cause}"
    q = (f"{member}: the cut length is {cause}. " if cause else f"{member}: the cut length differs from the drawing's by more than the band and no single rule explains it. ") + (
      "Sign the convention for this project or correct the rows." if klass == "METHOD" else "Correct the rows." if klass == "ERROR" else "Check the cut against the detail.")
    return XFinding(code, klass, text, ref, bbs_value=h0["billed"], trace_value=h0["expected"], diff_kg=r2(effect_sum), confidence=D("0.8" if cause else "0.6"), question=q, drawing_ref=dref,
      effect_basis="EXPECTATION", convention=conv)
    
  if code == "LAPS_MISSING":
    effect = ZERO
    for h in hs:
      r = rows[h["row"]]
      effect += h["laps"] * (h["lap_in"] / 12) * (r.members or D(1)) * (r.each or D(1)) * unit_kg(r.dia)
    assumed = h0["stock_assumed"]
    return XFinding(code, "ERROR", TEXT[code], ref, bbs_value=f"{row.cut_ft} ft in one piece", trace_value=f"{h0['laps']} lap(s) of {h0['lap_in']:g} in at {h0['stock']:g} ft stock",
      diff_kg=r2(effect), confidence=D("0.6" if assumed else "0.9"), effect_basis="ESTIMATE" if assumed else "EXPECTATION",
      question=(f"{member}: the cut length is longer than a stock bar. " + ("The stock length is assumed to be 40 ft (no decision). " if assumed else "") + "Confirm the stock length and add the laps."),
      drawing_ref=None)
  if code == "ZONES_AVERAGED":
    members = sorted({str(rows[h["row"]].member) for h in hs}, key=str)
    ref["members"] = members
    note = next((n for h in hs for n in h.get("notes", []) if "onsider" in n), None)
    basis = "EXPECTATION" if all(h["basis"] == "EXPECTATION" for h in hs) else "ESTIMATE"
    return XFinding(code, "METHOD", TEXT[code], ref, bbs_value=h0["billed"], trace_value=h0["expected"], diff_kg=r2(effect_sum), confidence=D("0.8"),
      question=(f"The schedule note reads {note}. " if note else "") + f"The drawing prints {h0['printed']}. Sign the convention (one average spacing) for this project, or correct the rows. {len(members)} member(s) on this sheet.",
      drawing_ref=dref, effect_basis=basis, convention={"key": "tie_zones", "value": "AVERAGE"})
    
  if code == "EXTRAS_FULL_LENGTH":
    basis = "EXPECTATION" if all(h["basis"] == "EXPECTATION" for h in hs) else "ESTIMATE"
    return XFinding(code, "ERROR", TEXT[code], ref, bbs_value=h0["billed"], trace_value=h0["expected"], diff_kg=r2(effect_sum), confidence=D("0.7" if basis == "ESTIMATE" else "0.9"),
      question=f"{member}: the extra bars are billed at the length of the through bars. The general notes print their curtailment. " + ("The span is taken from the through bars. " if basis == "ESTIMATE" else ""),
      drawing_ref=dref, effect_basis=basis)
  if code == "BARS_DO_NOT_FIT":
    return XFinding(code, "ERROR", TEXT[code], ref, bbs_value=f"{row.each} bars of #{row.dia}", trace_value=f"{h0['count']} bars across {h0['side']:g} in need {_fmt(h0['need'])} in, {_fmt(h0['clear'])} in is clear",
      confidence=D("0.9"), question=f"{member}: {row.each} bars of #{row.dia} cannot be placed in the section with the printed cover and ties.", drawing_ref=dref, effect_basis=None)
  if code == "FLOOR_NOT_IN_SCHEDULE":
    effect = -kg_total
    where = ", ".join(sorted({str(e.get("floor")).lower() for h in hs for e in h["elements"] if e.get("floor")})) or "another floor"
    floors = ", ".join(f.lower() for f in h0.get("floors") or [])
    if klass == "CONFLICT":
      q = f"{member}: the schedule cell is blank but the plan draws it on this floor. Keep or remove the {_fmt(kg_total)} kg?"
    else:
      q = f"{member}: billed on the {floors or 'floor'} floor; the schedule cell is blank and the plans read show it on the {where} floor only. Remove the {_fmt(kg_total)} kg?"
    el = h0["elements"][0] if h0["elements"] else None
    dr = ref_for(refs, el["class"], el["mark"], None) if el else None
    return XFinding(code, klass, TEXT[code], ref, bbs_value=f"{_fmt(kg_total)} kg billed", trace_value="no schedule cell on this floor", diff_kg=r2(effect), confidence=D("0.9" if klass == "ERROR" else "0.5"),
      question=q, drawing_ref=dr, effect_basis="BBS_ROWS")
  if code == "EXTRA_MEMBER":
    return XFinding(code, "EXTRA", TEXT[code], ref, bbs_value=f"{_fmt(kg_total)} kg billed", trace_value="no drawing member", diff_kg=r2(-kg_total), confidence=D("0.6"), question=h0.get("reason"),
      drawing_ref=None, effect_basis="BBS_ROWS")
  if code == "NO_DETAIL":
    members = sorted({str(rows[h["row"]].member) for h in hs}, key=str)
    ref["members"] = members
    kg = sum((rows[h["row"]].total_kg or ZERO for h in hs), ZERO)
    ref["rows"] = _rows_note(sorted({h["row"] for h in hs}), rows)
    return XFinding(code, "UNVERIFIABLE", TEXT[code], ref, bbs_value=f"{len(members)} member(s), {_fmt(kg)} kg", trace_value="no detail read from the drawings", diff_kg=None, confidence=D("1"),
      question=f"{sheet_names.get(row.sheet)}: {len(members)} member(s) ({_fmt(kg)} kg) cannot be checked because the drawings read give no detail for them. Is there a detail sheet?", drawing_ref=None, effect_basis=None)
  if code == "LABEL_FLOOR":
    return XFinding(code, "NAMING", TEXT[code], ref, bbs_value=sheet_names.get(row.sheet), trace_value=h0["reason"], confidence=D("0.8"), question="The sheet name misnames the floor; rename it or confirm the floor map.", drawing_ref=None)
  return None

def states_each(row) -> D:
  return (row.members or D(1)) * (row.each or D(1))

def size_conflicts(sheets: list, rows: list, match, sheet_names: dict) -> list:
  found: dict = {}
  for sh in sheets:
    meta = sh.get("meta") or {}
    no = (meta.get("identity") or {}).get("sheet_no")
    for c in ((meta.get("structure_tables") or {}).get("column_schedule") or {}).get("cells") or []:
      for conf in ((c.get("sketch") or {}).get("conflicts") or []):
        if conf.get("kind") == "SIZE_TEXT_VS_SKETCH" and conf.get("printed_in") and conf.get("sketch_in") and c.get("mark"):
          found.setdefault(norm_mark(c["mark"]), {"class": "COLUMN", "mark": c["mark"], "floor": c.get("floor"), "printed_in": conf["printed_in"], "sketch_in": conf["sketch_in"], "pdf_key": sh["pdf_key"],
            "page": sh["page_no"], "sheet_no": no, "cell_uv": c.get("cell_uv"), "anchor_native": c.get("anchor_native"), "rows": []})
          
  for it in match.items:
    if it.kind != "MATCH":
      continue
    row = rows[it.row_index]
    for el in it.elements:
      conf = found.get(norm_mark(el.get("mark"))) if el.get("class") == "COLUMN" else None
      if conf is not None and role_key(row.description) == "rings" and row.cut_ft is not None:
        cut_in = row.cut_ft * 12
        near = lambda sz: abs(cut_in - 2 * (D(str(sz[0])) + D(str(sz[1])))) <= 1
        follows = "sketch" if near(conf["sketch_in"]) else "printed size" if near(conf["printed_in"]) else None
        if follows and not conf.get("bbs_follows"):
          conf["bbs_follows"] = follows
        conf["rows"].append(_row_note(row, it.row_index))
        break
  return list(found.values())
