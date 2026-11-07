from __future__ import annotations
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from app.modules.drawings_boq.schedule_parsing import ScheduleParseError
from app.modules.drawings_boq.rebar import bbs_diameter

MAX_BBS_PAGES = 400
MAX_PAGE_CHARS = 30000
GIVE_UP_AFTER_PAGES = 6
_NUMBER = re.compile(r"-?\d[\d,]*(?:\.\d+)?|-?\.\d+")
_PAGE_COUNTER = re.compile(r"^Page\s+(\d+)\s+of\s+(\d+)$", re.IGNORECASE)
_SPACING = re.compile(r"(\d+(?:\.\d+)?)\s*C\s*to\s*C", re.IGNORECASE)
_DIA = re.compile(r"#\s*(\d+)")
_DASH_JOIN = re.compile(r"(?<=[A-Za-z0-9\)]) -(?=[A-Za-z0-9])")
_COLUMNS = ("sr", "description", "dia", "spacing", "members", "each", "total", "cut_ft", "total_ft", "unit_kg_ft", "total_kg")

@dataclass(frozen=True)
class BbsProfile:
  name: str
  header_tokens: tuple
  header_min_hits: int
  header_scan_lines: int
  header_window: int
  sheet_marker: str
  total_phrase: tuple
  dia_totals_phrase: tuple
  note_starts: tuple
  line_tol: float
  band_tol: float
  chain_gap: float
  part_gap: float
  parts_offset: float
  centered_reach: float
  min_page_words: int

PK_BBS_FEET = BbsProfile(
  name="PK_BBS_FEET",
  header_tokens=("no", "bars", "each", "total", "cut", "length", "unit", "weight", "bar", "parts", "shape", "dia", "c/c"),
  header_min_hits=8,
  header_scan_lines=25,
  header_window=6,
  sheet_marker="job/area",
  total_phrase=("total", "steel", "kgs"),
  dia_totals_phrase=("dia", "of", "bar"),
  note_starts=("consider", "at mid", "at joint", "left & right side", "rings for"),
  line_tol=2.0,
  band_tol=3.0,
  chain_gap=13.0,
  part_gap=5.0,
  parts_offset=8.0,
  centered_reach=18.0,
  min_page_words=40,
)

@dataclass
class _W:
  text: str
  x0: float
  y0: float
  x1: float
  y1: float

  @property
  def xc(self) -> float:
    return (self.x0 + self.x1) / 2

  @property
  def yc(self) -> float:
    return (self.y0 + self.y1) / 2

@dataclass
class BbsRow:
  page: int
  y: float
  sheet: int
  member: str | None
  sr: int | None
  description: str
  dia: int | None
  spacing_in: Decimal | None
  members: Decimal | None
  each: Decimal | None
  total: Decimal | None
  cut_ft: Decimal | None
  total_ft: Decimal | None
  unit_kg_ft: Decimal | None
  total_kg: Decimal | None
  parts: list = field(default_factory=list)
  notes: list = field(default_factory=list)
  issues: list = field(default_factory=list)

@dataclass
class BbsSheet:
  index: int
  name: str
  first_page: int
  last_page: int
  printed_total_kg: Decimal | None = None
  dia_totals_kg: dict = field(default_factory=dict)
  closed: bool = False

@dataclass
class BbsUnreadLine:
  page: int
  y: float
  text: str
  reason: str

@dataclass
class BbsDocument:
  title: str | None
  pages: int
  profile: str
  page_counters: list = field(default_factory=list)
  sheets: list = field(default_factory=list)
  rows: list = field(default_factory=list)
  dropped_repeats: list = field(default_factory=list)
  unread_lines: list = field(default_factory=list)

def _dec(text) -> Decimal | None:
  s = re.sub(r"[\s,]", "", str(text or ""))
  if not s or not _NUMBER.fullmatch(s):
    return None
  try:
    return Decimal(s)
  except InvalidOperation:
    return None

def page_words(page) -> list:
  import pypdfium2.raw as raw
  tp = page.get_textpage()
  try:
    n = tp.count_chars()
    if n > MAX_PAGE_CHARS:
      return []
    words: list = []
    cur: list = []
    prev = None

    def flush():
      if cur:
        words.append(_W("".join(c[0] for c in cur), min(c[1] for c in cur), min(c[2] for c in cur),
          max(c[3] for c in cur), max(c[4] for c in cur)))
        cur.clear()

    for i in range(n):
      u = raw.FPDFText_GetUnicode(tp.raw, i)
      ch = chr(u) if 0 < u < 0x110000 else ""
      if not ch or ch.isspace() or raw.FPDFText_IsGenerated(tp.raw, i):
        flush()
        prev = None
        continue
    
      l, b, r, t = tp.get_charbox(i)
      if r <= l and t <= b:
        flush()
        prev = None
        continue
      h = max(t - b, 1.0)
      if prev is not None and (l - prev[3] > 0.5 * h or abs((b + t) / 2 - (prev[2] + prev[4]) / 2) > 0.5 * h):
        flush()
      cur.append((ch, l, b, r, t))
      prev = (ch, l, b, r, t)
    flush()
    return words
  finally:
    tp.close()

def _merge_numbers(words: list, gap: float) -> list:
  out: list = []
  for _, ws in _lines(words, 3.5):
    cur: list = []
    for w in ws:
      if cur:
        p = cur[-1]
        close = 0 <= w.x0 - p.x1 < gap
        joins = (re.search(r"\d$", p.text) and re.match(r"^[.,]\d*$", w.text)) or (re.search(r"[.,]$", p.text) and re.match(r"^\d", w.text)) or w.text == "."
        if close and joins:
          cur[-1] = _W(p.text + w.text, p.x0, min(p.y0, w.y0), w.x1, max(p.y1, w.y1))
          continue
      
      cur.append(w)
    out.extend(cur)
  return out

def _lines(words: list, tol: float) -> list:
  out: list = []
  for w in sorted(words, key=lambda w: -w.yc):
    if out and abs(out[-1][0] - w.yc) <= tol:
      out[-1][1].append(w)
      out[-1][0] = sum(x.yc for x in out[-1][1]) / len(out[-1][1])
    else:
      out.append([w.yc, [w]])
  return [(y, sorted(ws, key=lambda w: w.x0)) for y, ws in out]

def _text(words: list) -> str:
  return _DASH_JOIN.sub("-", " ".join(w.text for w in sorted(words, key=lambda w: w.x0))).strip()

def _find_header(lines: list, prof: BbsProfile):
  best = None
  scan = lines[:prof.header_scan_lines]
  for i in range(0, max(1, len(scan) - 1)):
    window = scan[i:i + prof.header_window]
    found = {re.sub(r"[^a-z/]", "", w.text.lower()) for _, ws in window for w in ws}
    hits = len(found & set(prof.header_tokens))
    if hits >= prof.header_min_hits and (best is None or hits > best[0]):
      best = (hits, i)
      
  return best

def _header_geometry(lines: list, start: int, prof: BbsProfile):
  region = []
  top_y = lines[start][0]
  for y, ws in lines[start:start + 14]:
    if top_y - y <= 36:
      region.append((y, ws))
  words = [w for _, ws in region for w in ws]

  def pick(pred, nth=0):
    hits = sorted((w for w in words if pred(w)), key=lambda w: w.x0)
    return hits[nth] if len(hits) > nth else None

  def low(w):
    return re.sub(r"[^a-z/]", "", w.text.lower())

  sr = pick(lambda w: low(w) == "sr")
  desc = pick(lambda w: low(w).startswith("descri"))
  dia = pick(lambda w: low(w) == "dia")
  cc = pick(lambda w: low(w) == "c/c")
  no = None
  if dia is not None:
    cand = [w for w in words if low(w) == "no" and abs(w.yc - dia.yc) <= 2.5 and w.x0 > dia.x1]
    no = min(cand, key=lambda w: w.x0) if cand else None
  each = pick(lambda w: low(w) == "each")
  totals = sorted((w for w in words if low(w) == "total"), key=lambda w: w.x0)
  cut = pick(lambda w: low(w) == "cut")
  unit = pick(lambda w: low(w) == "unit")
  bar = pick(lambda w: low(w) == "bar")
  
  if None in (sr, desc, dia, cc, no, each, cut, unit, bar) or len(totals) < 3:
    return None
  lengths = sorted((w for w in words if low(w) == "length"), key=lambda w: w.x0)
  total_ft_x1 = max((w.x1 for w in lengths if w.x0 > totals[1].x0), default=totals[1].x1)
  s_end = no.x1
  for w in words:
    if low(w) == "s" and abs(w.yc - no.yc) <= 2.5 and w.x0 > no.x0:
      s_end = max(s_end, w.x1)
  centers = {
    "sr": sr.xc, "description": desc.xc, "dia": dia.xc, "spacing": cc.xc, "members": (no.x0 + s_end) / 2, "each": each.xc,
    "total": totals[0].xc, "cut_ft": cut.xc + 2, "total_ft": (totals[1].x0 + total_ft_x1) / 2, "unit_kg_ft": unit.xc,
    "total_kg": totals[2].xc,
  }
  
  bottoms = [y for y, ws in region if any(low(w) in ("(kg)", "kg/ft", "(ft)") for w in ws)]
  bottom = (min(bottoms) if bottoms else min(y for y, _ in region)) - 2.0
  kg_right = max((w.x1 for w in words if low(w) == "(kg)"), default=totals[2].x1)
  return {"centers": centers, "bottom": bottom, "parts_x0": max(kg_right, totals[2].x1) + prof.parts_offset, "top": top_y}

def _column_of(xc: float, centers: dict) -> str:
  return min(_COLUMNS, key=lambda k: abs(centers[k] - xc))

def _split_notes(texts: list, prof: BbsProfile):
  desc: list = []
  notes: list = []
  depth = 0
  cur: list | None = None
  
  for t in texts:
    low = t.lower()
    starts = low.startswith("(") or any(low.startswith(p) for p in prof.note_starts)
    if depth > 0 or starts:
      if cur is None or (depth == 0 and starts):
        cur = []
        notes.append(cur)
      cur.append(t)
      depth += t.count("(") - t.count(")")
      depth = max(depth, 0)
      if depth == 0 and not any(low.startswith(p) for p in prof.note_starts) and not low.startswith("("):
        cur = None
      if depth == 0 and t.rstrip().endswith(")"):
        cur = None
    else:
      cur = None
      desc.append(t)
      
  return " ".join(desc).strip(), [" ".join(n).strip() for n in notes if n]

def _row_from_words(prof, geom, page_no, y, words, sheet_index, member, member_notes) -> BbsRow:
  centers = geom["centers"]
  dia_left = (centers["description"] + centers["dia"]) / 2 + 12
  cells: dict = {k: [] for k in _COLUMNS}
  for w in _merge_numbers([w for w in words if w.xc >= dia_left], 6.0):
    cells[_column_of(w.xc, centers)].append(w)
  issues: list = []

  def number(key):
    txt = _text(cells[key])
    if not txt:
      return None
    v = _dec(txt)
    if v is None:
      issues.append(f"{key}:{txt}")
    return v

  sr_words = [w for w in words if w.xc < (centers["sr"] + centers["description"]) / 2 and re.fullmatch(r"\d+", w.text)]
  sr = int(sr_words[0].text) if sr_words else None
  dia_text = _text(cells["dia"])
  dm = _DIA.search(dia_text)
  sm = _SPACING.search(_text(cells["spacing"]))
  members = number("members")
  each = number("each")
  total = number("total")
  
  return BbsRow(page=page_no, y=round(y, 1), sheet=sheet_index, member=member, sr=sr, description="", dia=int(dm.group(1)) if dm else None,
    spacing_in=Decimal(sm.group(1)) if sm else None, members=members, each=each, total=total, cut_ft=number("cut_ft"),
    total_ft=number("total_ft"), unit_kg_ft=number("unit_kg_ft"), total_kg=number("total_kg"), notes=list(member_notes), issues=issues)

def _same_numbers(a: BbsRow, b: BbsRow) -> bool:
  keys = ("sr", "description", "dia", "spacing_in", "members", "each", "total", "cut_ft", "total_ft", "unit_kg_ft", "total_kg", "member")
  return a.sheet == b.sheet and all(getattr(a, k) == getattr(b, k) for k in keys)

def _clean_name(text: str) -> str:
  t = re.sub(r"\s+([\"'])", r"\1", text)
  t = re.sub(r"(?<=['\"])\s+(?=-)", "", t)
  t = re.sub(r"(?<=[A-Za-z]) \.(?=[A-Za-z])", ".", t)
  return re.sub(r"\s+", " ", t).strip()

def _continuation(texts: list) -> bool:
  joined = " ".join(texts)
  return joined.count(")") > joined.count("(") or bool(re.match(r"^[a-z]", joined))

def _page_header_info(lines, head_top, words, doc):
  sheet_name = None
  for y, ws in lines:
    if y < head_top - 0.1:
      break
    toks = [w.text.lower() for w in ws]
    if any(t.startswith("job/area") for t in toks):
      colon = next((i for i, w in enumerate(ws) if w.text == ":"), None)
      x_from = ws[colon].x1 if colon is not None else ws[0].x1
      near = [w for w in words if abs(w.yc - y) <= 8.0 and w.x0 >= x_from]
      sheet_name = _clean_name(_text(near))
    elif "schedule" in toks and "bending" in toks:
      if doc.title is None:
        doc.title = re.sub(r"\s+,", ",", _text([w for w in words if abs(w.yc - y) <= 6.0]))
  return sheet_name

def _read_page(prof, page_no, words, doc, st) -> None:
  words = _merge_numbers(words, 6.0)
  lines = _lines(words, prof.line_tol)
  found = _find_header(lines, prof)
  geom = _header_geometry(lines, found[1], prof) if found is not None and len(words) >= prof.min_page_words else None
  if geom is None:
    for y, ws in lines:
      doc.unread_lines.append(BbsUnreadLine(page_no, round(y, 1), _text(ws), "NO_HEADER" if found is None else "HEADER_INCOMPLETE"))
    return
  centers = geom["centers"]
  head_top = geom["top"]
  sheet_name = _page_header_info(lines, head_top, words, doc)
  
  for y, ws in lines[:found[1]]:
    txt = _text(ws)
    low = txt.lower()
    if low.startswith("job/area") or "bending" in low or low.startswith("dha") or re.fullmatch(r"[,.'\"\s]*", txt):
      continue
    doc.unread_lines.append(BbsUnreadLine(page_no, round(y, 1), txt, "ABOVE_HEADER"))
    
  body = [w for w in words if w.yc < geom["bottom"]]
  footer_lines = [(y, ws) for y, ws in _lines(body, prof.line_tol) if _PAGE_COUNTER.match(_text(ws))]
  for y, ws in footer_lines:
    m = _PAGE_COUNTER.match(_text(ws))
    doc.page_counters.append((int(m.group(1)), int(m.group(2))))
  foot_ids = {id(w) for _, ws in footer_lines for w in ws}
  body = [w for w in body if id(w) not in foot_ids]
  split_y = None
  for y, ws in _lines(body, prof.line_tol):
    low = [w.text.lower() for w in ws]
    if all(t in low for t in prof.total_phrase) or all(t in low for t in prof.dia_totals_phrase) or _text(ws).lower().startswith("weight of steel"):
      split_y = y
      break
  
  data = [w for w in body if split_y is None or w.yc > split_y + prof.line_tol / 2]
  tail = [w for w in body if split_y is not None and w.yc <= split_y + prof.line_tol / 2]
  anchors = sorted({round(w.yc, 1) for w in data if w.text.startswith("#") and abs(w.xc - centers["dia"]) < 24}, reverse=True)
  
  if sheet_name is None:
    sheet_name = st["sheet"].name if st["sheet"] else "UNNAMED"
  cur = st["sheet"]
  if cur is None or cur.name != sheet_name or (cur.closed and anchors):
    cur = BbsSheet(index=len(doc.sheets), name=sheet_name, first_page=page_no, last_page=page_no)
    doc.sheets.append(cur)
    st["sheet"] = cur
    st["member"] = None
    st["member_notes"] = []
    st["last_row"] = None
  cur.last_page = page_no
  if tail:
    for y, ws in _lines(tail, prof.line_tol):
      low = [w.text.lower() for w in ws]
      if all(t in low for t in prof.total_phrase):
        nums = [v for v in (_dec(w.text) for w in ws if w.text.lower() not in prof.total_phrase) if v is not None]
        if nums:
          cur.printed_total_kg = nums[-1]
        cur.closed = True
    _read_summary(prof, page_no, tail, cur, doc, st)
    
  dia_left = (centers["description"] + centers["dia"]) / 2 + 12
  sr_right = (centers["sr"] + centers["description"]) / 2
  px = geom["parts_x0"]
  row_words: dict = {a: [] for a in anchors}
  left_src: list = []
  part_words: list = []
  
  for w in data:
    a = next((x for x in anchors if abs(w.yc - x) <= prof.band_tol), None)
    if w.xc >= px:
      part_words.append(w)
    elif a is not None:
      row_words[a].append(w)
    elif w.xc < dia_left or re.fullmatch(r"[A-Za-z()\-]+", w.text):
      left_src.append(w)
    else:
      doc.unread_lines.append(BbsUnreadLine(page_no, round(w.yc, 1), w.text, "NUMERIC_OUTSIDE_ROW"))
      
  left_items: list = []
  for a in anchors:
    lw = [w for w in row_words[a] if w.xc < dia_left and not (w.xc < sr_right and re.fullmatch(r"\d+", w.text))]
    made = _lines(lw, prof.line_tol)
    for y, ws in made:
      left_items.append((y, ws, a))
    if not made:
      left_items.append((a, [], a))
  for y, ws in _lines(left_src, prof.line_tol):
    left_items.append((y, ws, None))
  left_items.sort(key=lambda t: -t[0])
  chains: list = []
  for item in left_items:
    if chains and chains[-1][-1][0] - item[0] <= prof.chain_gap:
      chains[-1].append(item)
    else:
      chains.append([item])
  events: list = []
  chained: set = set()
  for chain in chains:
    owned = []
    for _, _, a in chain:
      if a is not None and a not in owned:
        owned.append(a)
    chained.update(owned)
    events.append((owned[0] if owned else chain[0][0], "chain" if owned else "heading", chain, owned))
    
  for a in anchors:
    if a not in chained:
      events.append((a, "chain", [], [a]))
  events.sort(key=lambda e: (-e[0], 0 if e[1] == "heading" else 1))
  first_anchor = anchors[0] if anchors else None
  rows_by_anchor: dict = {}
  last = st["last_row"]
  for y, kind, chain, owned in events:
    if kind == "heading":
      texts = [_clean_name(_text(ws)) for _, ws, _ in chain if ws]
      if last is not None and (first_anchor is None or y > first_anchor) and not rows_by_anchor and _continuation(texts):
        last.notes.append(" ".join(texts))
        continue
      name, notes = _split_notes(texts, prof)
      if name:
        st["member"] = name
      st["member_notes"] = notes
      continue
  
    per_anchor: dict = {a: [] for a in owned}
    for cy, ws, a in chain:
      owner = a if a is not None else min(owned, key=lambda k: abs(k - cy))
      if ws:
        per_anchor[owner].append(_clean_name(_text(ws)))
    for a in owned:
      row = _row_from_words(prof, geom, page_no, a, row_words[a], cur.index, st["member"], st["member_notes"])
      desc, notes = _split_notes(per_anchor.get(a, []), prof)
      if not desc:
        desc = next(("Rings" for n in notes if n.lower().startswith("rings for")), "")
      row.description = desc
      row.notes = list(st["member_notes"]) + notes
      rows_by_anchor[a] = row
  on_line = {a: 0 for a in anchors}
  
  for pw in part_words:
    for a in anchors:
      if abs(pw.yc - a) <= prof.band_tol:
        on_line[a] += 1
  for pw in part_words:
    near = next((a for a in anchors if abs(pw.yc - a) <= prof.band_tol), None)
    above = [a for a in anchors if a + prof.band_tol >= pw.yc]
    below = [a for a in anchors if a < pw.yc - prof.band_tol]
    if near is None and below and on_line[below[0]] == 0 and pw.yc - below[0] <= prof.centered_reach:
      near = below[0]
    if near is None and above:
      near = min(above, key=lambda a: a - pw.yc)
    if near is None:
      if last is not None and last.sheet == cur.index:
        last.parts.append(pw)
      else:
        doc.unread_lines.append(BbsUnreadLine(page_no, round(pw.yc, 1), pw.text, "PART_WITHOUT_ROW"))
      continue
  
    rows_by_anchor[near].parts.append(pw)
  ordered = [rows_by_anchor[a] for a in anchors if a in rows_by_anchor]
  for r in ordered + ([last] if last is not None and any(isinstance(p, _W) for p in last.parts) else []):
    vals = []
    for w in sorted((p for p in r.parts if isinstance(p, _W)), key=lambda w: (-round(w.yc / prof.line_tol), w.x0)):
      v = _dec(w.text)
      if v is None:
        r.issues.append(f"part:{w.text}")
      else:
        vals.append(v)
        
    r.parts = [p for p in r.parts if not isinstance(p, _W)] + vals
  if ordered and last is not None and _same_numbers(ordered[0], last):
    if len(ordered[0].parts) > len(last.parts):
      last.parts = ordered[0].parts
    doc.dropped_repeats.append({"page": page_no, "sheet": cur.index, "sr": ordered[0].sr, "member": ordered[0].member, "y": ordered[0].y})
    ordered = ordered[1:]
  doc.rows.extend(ordered)
  if ordered:
    st["last_row"] = ordered[-1]

def _read_summary(prof, page_no, words, sheet, doc, st) -> None:
  lines = _lines(words, prof.line_tol)
  header_x: list = list(st.get("summary_x") or [])
  
  for y, ws in lines:
    low = [w.text.lower() for w in ws]
    if all(t in low for t in prof.dia_totals_phrase):
      header_x = []
      toks = [w for w in ws]
      for i, w in enumerate(toks):
        if w.text == "#" and i + 1 < len(toks):
          header_x.append((toks[i + 1].text, (w.x0 + toks[i + 1].x1) / 2))
      tot = [w for w in ws if w.text.lower() == "total"]
      if tot:
        header_x.append(("Total", tot[-1].xc))
      st["summary_x"] = header_x
      continue
  
    text = _text(ws).lower()
    if text.startswith("weight of steel in kgs") and header_x:
      merged = _merge_numbers([w for w in ws if w.x0 > header_x[0][1] - 30], 6.0)
      for w in merged:
        key = min(header_x, key=lambda h: abs(h[1] - w.xc))[0]
        v = _dec(w.text)
        if v is not None:
          sheet.dia_totals_kg[key] = v
    elif text.startswith("weight of steel in ton") or not text or all(t in low for t in prof.total_phrase) or re.fullmatch(r"[,.\s]*", text):
      continue
    elif not text.startswith("weight of steel"):
      doc.unread_lines.append(BbsUnreadLine(page_no, round(y, 1), _text(ws), "SUMMARY_UNKNOWN"))

PROFILES = (PK_BBS_FEET,)
SHEET_TOLERANCE_KG = Decimal("0.05")
VOTE_PAGES = 6

class UnknownBbsLayout(ScheduleParseError):
  """No known layout matches the document. Carries the closest header text and every profile's score so the person sees what was found."""
  def __init__(self, message: str, header_text: str = "", scores: dict | None = None):
    super().__init__(message)
    self.header_text = header_text
    self.scores = scores or {}

def header_hits(lines: list, prof: BbsProfile):
  """Best header-word count in any window of one page's lines, and the text of that window. Unlike _find_header it has no minimum."""
  best = (0, "")
  scan = lines[:prof.header_scan_lines]
  for i in range(0, max(1, len(scan) - 1)):
    window = scan[i:i + prof.header_window]
    found = {re.sub(r"[^a-z/]", "", w.text.lower()) for _, ws in window for w in ws}
    hits = len(found & set(prof.header_tokens))
    if hits > best[0]:
      best = (hits, " | ".join(_text(ws) for _, ws in window))
  return best

def choose_profile(scores: dict, profiles: tuple) -> str | None:
  """The profile with the most header words, if it reaches its own minimum. A tie is broken by the share of the profile's own header it matched; a tie still left is no choice."""
  eligible = [(hits, hits / len(p.header_tokens), p.name) for p in profiles for hits in [scores.get(p.name, 0)] if hits >= p.header_min_hits]
  if not eligible:
    return None
  eligible.sort(reverse=True)
  if len(eligible) > 1 and eligible[0][:2] == eligible[1][:2]:
    return None
  return eligible[0][2]

def vote_profile(contents: bytes, profiles: tuple = PROFILES) -> BbsProfile:
  import pypdfium2 as pdfium
  try:
    pdf = pdfium.PdfDocument(contents)
  except Exception:
    raise ScheduleParseError("This PDF could not be opened for a bar schedule read.")
  scores = {p.name: 0 for p in profiles}
  nearest = (0, "")
  words_seen = 0
  try:
    for i in range(min(len(pdf), VOTE_PAGES)):
      page = pdf[i]
      try:
        words = _merge_numbers(page_words(page), 6.0)
      finally:
        page.close()
      words_seen += len(words)
      for prof in profiles:
        hits, text = header_hits(_lines(words, prof.line_tol), prof)
        if hits > scores[prof.name]:
          scores[prof.name] = hits
        if hits > nearest[0]:
          nearest = (hits, text)
  finally:
    pdf.close()
  chosen = choose_profile(scores, profiles)
  if chosen is not None:
    return next(p for p in profiles if p.name == chosen)
  shown = ", ".join(f"{p.name} {scores[p.name]} of {p.header_min_hits} needed" for p in profiles)
  if words_seen == 0:
    raise UnknownBbsLayout("This PDF has no text to read; a scanned bar schedule cannot be read.", "", scores)
  if any(scores[p.name] >= p.header_min_hits for p in profiles):
    raise UnknownBbsLayout(f"The layout matches more than one known layout equally ({shown}); none was chosen.", nearest[1], scores)
  raise UnknownBbsLayout(f"Unknown bar schedule layout ({shown}). Closest header read: {nearest[1] or 'none'}", nearest[1], scores)

def bbs_summary(doc: BbsDocument) -> dict:
  sheets = []
  for s in doc.sheets:
    rows = [r for r in doc.rows if r.sheet == s.index]
    computed = sum((r.total_kg or Decimal("0") for r in rows), Decimal("0"))
    diff = None if s.printed_total_kg is None else computed - s.printed_total_kg
    sheets.append({"name": s.name, "first_page": s.first_page, "last_page": s.last_page, "rows": len(rows),
      "printed_total_kg": None if s.printed_total_kg is None else str(s.printed_total_kg), "computed_kg": str(computed),
      "diff_kg": None if diff is None else str(diff), "reconciled": diff is not None and abs(diff) <= SHEET_TOLERANCE_KG,
      "dia_totals_kg": {k: str(v) for k, v in s.dia_totals_kg.items()}})
    
  printed = [s.printed_total_kg for s in doc.sheets if s.printed_total_kg is not None]
  return {"profile": doc.profile, "title": doc.title, "pages": doc.pages, "row_count": len(doc.rows), "sheet_count": len(doc.sheets),
    "sheets": sheets, "printed_total_kg": str(sum(printed, Decimal("0"))), "rows_total_kg": str(sum((r.total_kg or Decimal("0") for r in doc.rows), Decimal("0"))),
    "all_reconciled": all(x["reconciled"] for x in sheets), "dropped_repeats": doc.dropped_repeats,
    "page_counters": [[n, m] for n, m in doc.page_counters], "unread_count": len(doc.unread_lines),
    "unread_lines": [{"page": u.page, "y": u.y, "text": u.text[:120], "reason": u.reason} for u in doc.unread_lines[:50]]}

def read_bbs_pdf(contents: bytes, profiles: tuple = PROFILES) -> BbsDocument:
  return _read_with_profile(contents, vote_profile(contents, profiles))

def _read_with_profile(contents: bytes, prof: BbsProfile) -> BbsDocument:
  import pypdfium2 as pdfium
  try:
    pdf = pdfium.PdfDocument(contents)
  except Exception:
    raise ScheduleParseError("This PDF could not be opened for a bar schedule read.")
  n = len(pdf)
  if n > MAX_BBS_PAGES:
    raise ScheduleParseError(f"A bar schedule of more than {MAX_BBS_PAGES} pages cannot be read.")
  doc = BbsDocument(title=None, pages=n, profile=prof.name)
  st = {"sheet": None, "member": None, "member_notes": [], "last_row": None}
  
  try:
    for i in range(n):
      page = pdf[i]
      try:
        _read_page(prof, i + 1, page_words(page), doc, st)
      finally:
        page.close()
      if i + 1 >= GIVE_UP_AFTER_PAGES and not doc.rows:
        break
  finally:
    pdf.close()
  if not doc.rows:
    raise ScheduleParseError("No schedule table header was found in the PDF text.")
  bbs_diameter.carry_down(doc.rows)
  return doc
