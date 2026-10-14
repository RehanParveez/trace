from __future__ import annotations
from reportlab.lib import colors
import re
from decimal import Decimal, InvalidOperation
from collections import OrderedDict, Counter
from reportlab.platypus import TableStyle, Paragraph, KeepTogether, PageBreak, SimpleDocTemplate, Spacer, Table
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from io import BytesIO
from reportlab.pdfgen import canvas as rl_canvas
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from datetime import datetime

MAX_REPORT_ROWS = 10000
MAX_CELL = 400
NO_FLOOR = "(no floor)"

KIND_ORDER = ("IfcFooting", "IfcColumn", "IfcBeam", "IfcWall", "IfcSpace", "IfcDoor", "IfcWindow")
KIND_LABEL = {
  "IfcFooting": "Footings", "IfcColumn": "Columns", "IfcBeam": "Beams", "IfcWall": "Walls", "IfcSpace": "Rooms", "IfcDoor": "Doors",
  "IfcWindow": "Windows", "IfcSlab": "Slabs", "IfcStair": "Stairs", "IfcRoof": "Roofs", "IfcCovering": "Coverings", "IfcRailing": "Railings",
}
STATUS_ORDER = ("VALID", "WARNING", "INVALID", "PENDING")
STATUS_COLOR = {"VALID": "#15803d", "WARNING": "#b45309", "INVALID": "#b91c1c", "PENDING": "#475569"}
MODE_LABEL = {"EXACT": "Exact", "APPROXIMATE": "Bbox", "NONE": "No geometry", "PDF_MEASURED": "PDF measured", "PDF_FOUND": "PDF found"}
SHEET_STATE_LABEL = {"READ": "Read", "WAITING": "Not read yet", "NOT_PREPARED": "Not prepared", "SET_ASIDE": "Set aside"}

NAVY = colors.HexColor("#1e293b")
GRID = colors.HexColor("#cbd5e1")
BAND = colors.HexColor("#e2e8f0")
SOFT = colors.HexColor("#f1f5f9")

_PUNCT_ORDER = " _-,;:!?.\u00b7'\"()[]{}@*/\\&#%`^+<=>|~$"
_PUNCT_RANK = {c: i for i, c in enumerate(_PUNCT_ORDER)}
_TOKEN = re.compile(r"[0-9]+|[^\W\d_]+|.", re.S)

def natural(text) -> tuple:
  """A key that puts D2 before D10 and C-2 before C1, ignoring case: the order the screen uses."""
  out = []
  for match in _TOKEN.finditer(str(text or "").casefold()):
    tok = match.group()
    if tok.isascii() and tok.isdigit():
      out.append((2, int(tok), ""))
    elif tok[0].isalpha():
      out.append((3, 0, tok))
    else:
      out.append((0, _PUNCT_RANK.get(tok, len(_PUNCT_ORDER) + ord(tok)), ""))
  return tuple(out)

def kind_rank(ifc_type) -> int:
  try:
    return KIND_ORDER.index(ifc_type)
  except ValueError:
    return len(KIND_ORDER)

def level_of(row, level_names: dict | None = None) -> str:
  name = getattr(row, "level_name", None)
  if not name and level_names:
    name = level_names.get(getattr(row, "level_id", None))
  return name or ""

def sort_rows(rows: list, level_names: dict | None = None) -> list:
  """Floor by floor (lowest first), kind by kind, mark by mark."""
  def key(row):
    seq = getattr(row, "level_sequence", None)
    return (seq if seq is not None else 1e9, natural(level_of(row, level_names)), kind_rank(getattr(row, "ifc_type", None)),
      natural(getattr(row, "ifc_type", "")), natural(getattr(row, "name", "")), natural(getattr(row, "id", "")))
  return sorted(rows, key=key)

def to_decimal(value) -> Decimal | None:
  if value is None or value == "":
    return None
  try:
    d = Decimal(str(value))
  except (InvalidOperation, ValueError):
    return None
  return d if d.is_finite() else None

def num(value, places: int = 4) -> str:
  d = to_decimal(value)
  if d is None:
    return ""
  text = f"{d.quantize(Decimal(1).scaleb(-places)):,.{places}f}" if places > 0 else f"{d.quantize(Decimal(1)):,}"
  if "." in text:
    text = text.rstrip("0").rstrip(".")
  return text

def clean(value, limit: int = MAX_CELL) -> str:
  """Text safe for the PDF: one line, only characters the built-in font can draw, escaped for the markup, never longer than a cell can hold."""
  text = " ".join(("" if value is None else str(value)).split())
  text = text.encode("cp1252", "replace").decode("cp1252")
  if len(text) > limit:
    text = text[: limit - 3].rstrip() + "..."
  return escape(text)

def size_lines(row) -> tuple[str, str]:
  linear = [f"{label} {num(getattr(row, key, None), 1)}" for key, label in (("length_mm", "L"), ("width_mm", "W"), ("height_mm", "H"), ("thickness_mm", "T"))
    if to_decimal(getattr(row, key, None)) is not None]
  first = (", ".join(linear) + " mm") if linear else ""
  extra = []
  area, volume = to_decimal(getattr(row, "area_mm2", None)), to_decimal(getattr(row, "volume_mm3", None))
  if area is not None:
    extra.append(f"A {num(area / Decimal(1000000), 3)} m²")
  if volume is not None:
    extra.append(f"V {num(volume / Decimal(1000000000), 4)} m³")
  return first, ", ".join(extra)

def pdf_meta(row) -> dict:
  props = getattr(row, "properties", None) or {}
  return (props.get("_pdf") or {}) if props.get("source") == "pdf_takeoff" else {}

def issue_list(row) -> list[dict]:
  return [i for i in (getattr(row, "normalization_issues", None) or []) if isinstance(i, dict)]

def issue_codes(row) -> list[str]:
  seen, out = set(), []
  for i in issue_list(row):
    code = i.get("code") or ""
    if code and code not in seen:
      seen.add(code)
      out.append(code)
  return out

def measure_mode(row) -> str:
  mode = getattr(row, "measure_mode", None)
  if mode:
    return mode
  return pdf_meta(row).get("mode") or ""

def reconcile(rows: list, expected: int, everything: int, level_names: dict | None = None) -> dict:
  """What the report holds against what the database counted for the same view. `ok` is true only when the rows listed are exactly the rows counted
  and no row appears twice."""
  
  floors: OrderedDict = OrderedDict()
  for row in rows:
    name = level_of(row, level_names) or NO_FLOOR
    floors[name] = floors.get(name, 0) + 1
  kinds: OrderedDict = OrderedDict()
  quantities: OrderedDict = OrderedDict()
  statuses = Counter()
  
  for row in rows:
    kind = getattr(row, "ifc_type", "") or ""
    kinds[kind] = kinds.get(kind, 0) + 1
    unit = getattr(row, "unit", None) or ""
    slot = quantities.setdefault((kind, unit), [0, Decimal(0)])
    slot[0] += 1
    slot[1] += to_decimal(getattr(row, "quantity", None)) or Decimal(0)
    statuses[getattr(row, "normalization_status", None) or "PENDING"] += 1
  ids = [str(getattr(row, "id", "")) for row in rows]
  duplicates = len(ids) - len(set(ids))
  listed = len(rows)
  return {
    "listed": listed, "expected": expected, "everything": everything, "duplicates": duplicates, "floors": floors, "kinds": kinds,
    "quantities": quantities, "statuses": statuses,
    "ok": listed == expected and duplicates == 0 and sum(floors.values()) == listed and sum(kinds.values()) == listed and sum(statuses.values()) == listed,
  }

def sheet_states(sheets: list, read_ids: set, per_sheet: dict, levels: dict) -> list[dict]:
  """One line per sheet of a PDF drawing: whether it was read and how many rows came from it. The same states the elements screen shows."""
  
  out = []
  for sh in sheets:
    meta = getattr(sh, "prep_meta", None) or {}
    issue = meta.get("read_issue") or {}
    title = meta.get("title") or {}
    if sh.id in read_ids:
      state = "READ"
    elif issue.get("severity") == "INFO":
      state = "SET_ASIDE"
    elif getattr(sh, "prep_status", None) != "READY":
      state = "NOT_PREPARED"
    else:
      state = "WAITING"
    out.append({
      "page_no": sh.page_no, "sheet_id": str(sh.id), "title": title.get("title") or getattr(sh, "label", None) or f"Sheet {sh.page_no}",
      "level": levels.get(getattr(sh, "level_id", None)), "state": state, "items": per_sheet.get(str(sh.id), 0),
      "message": None if state == "READ" else (issue.get("message") or getattr(sh, "prep_error", None)), "code": issue.get("code"),
    })
  return out

def filter_text(filters: dict) -> str:
  parts = [f"{label} = {value}" for label, value in filters.items() if value]
  return "; ".join(parts)

def _styles() -> dict:
  base = getSampleStyleSheet()
  cell = ParagraphStyle("Cell", parent=base["Normal"], fontName="Helvetica", fontSize=6.5, leading=7.7)
  return {
    "title": ParagraphStyle("T", parent=base["Heading1"], fontSize=17, leading=20, spaceAfter=2),
    "sub": ParagraphStyle("S", parent=base["Normal"], fontSize=9, leading=11.5, textColor=colors.HexColor("#334155")),
    "h2": ParagraphStyle("H2", parent=base["Heading2"], fontSize=11, leading=13, spaceBefore=8, spaceAfter=4),
    "note": ParagraphStyle("N", parent=base["Normal"], fontSize=7.5, leading=9.5, textColor=colors.HexColor("#475569")),
    "body": ParagraphStyle("B", parent=base["Normal"], fontSize=8.5, leading=11),
    "cell": cell,
    "cellr": ParagraphStyle("CR", parent=cell, alignment=2),
    "head": ParagraphStyle("Hd", parent=cell, fontName="Helvetica-Bold", textColor=colors.white),
    "headr": ParagraphStyle("HdR", parent=cell, fontName="Helvetica-Bold", textColor=colors.white, alignment=2),
    "band": ParagraphStyle("Bd", parent=cell, fontName="Helvetica-Bold", fontSize=7.5, leading=9),
    "bold": ParagraphStyle("Bo", parent=cell, fontName="Helvetica-Bold"),
    "boldr": ParagraphStyle("BoR", parent=cell, fontName="Helvetica-Bold", alignment=2),
    "muted": ParagraphStyle("Mu", parent=cell, textColor=colors.HexColor("#64748b")),
  }

def _p(text, style) -> Paragraph:
  return Paragraph(text, style)

def _table(data, widths, extra=None, repeat: int = 1, align_right_from: int | None = None) -> Table:
  table = Table(data, colWidths=widths, repeatRows=repeat)
  style = [
    ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.25, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
  ]
  table.setStyle(TableStyle(style + (extra or [])))
  return table

def _canvas_class(left: str, middle: str):
  class Numbered(rl_canvas.Canvas):
    def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      self._saved: list = []

    def showPage(self):
      self._saved.append(dict(self.__dict__))
      self._startPage()

    def save(self):
      total = len(self._saved)
      for state in self._saved:
        self.__dict__.update(state)
        self._frame(total)
        super().showPage()
      super().save()

    def _frame(self, total: int):
      width, height = landscape(A4)
      self.setStrokeColor(GRID)
      self.setLineWidth(0.4)
      self.line(10 * mm, 11 * mm, width - 10 * mm, 11 * mm)
      self.setFont("Helvetica", 7)
      self.setFillColor(colors.HexColor("#475569"))
      self.drawString(10 * mm, 7 * mm, left)
      self.drawCentredString(width / 2, 7 * mm, middle)
      self.drawRightString(width - 10 * mm, 7 * mm, f"Page {self._pageNumber} of {total}")
  return Numbered

def _columns(is_pdf: bool) -> list[tuple[str, float, bool]]:
 
  last = ("Sheet", 9.0, False) if is_pdf else ("IFC id", 26.0, False)
  material = 25.0 if is_pdf else 22.0
  measured = 45.0 if is_pdf else 36.0
  return [("#", 8.0, True), ("Type", 17.0, False), ("Name", 30.0, False), ("Role", 16.0, False), ("Discipline", 24.0, False), ("Level", 17.0, False),
    ("Material", material, False), ("Quantity", 19.0, True), ("Size", 27.0, False), ("Status", 14.0, False), ("Measured as", measured, False),
    ("Flags", 25.0 if is_pdf else 22.0, False), last]

def _summary_block(st, reco: dict, is_pdf: bool, facts: dict | None, rows: list, filters: dict) -> list:
  listed, expected, everything = reco["listed"], reco["expected"], reco["everything"]
  filt = filter_text(filters)
  measured = sum(1 for r in rows if measure_mode(r) == "PDF_MEASURED") if is_pdf else None
  review = sum(1 for r in rows if (getattr(r, "normalization_status", None) or "PENDING") != "VALID")
  lines = [
    ("Rows in this report", f"{listed:,}"),
    ("Rows the register holds" + (" (no filter)" if filt else ""), f"{everything:,}"),
    ("Filter", filt or "None. Every row of the register is listed."),
  ]
  
  if is_pdf and facts:
    lines.append(("Sheets read", f"{facts['sheets_read']} of {facts['sheets_total']}"))
  if is_pdf:
    lines.append(("Measured / need a look", f"{measured:,} measured, {review:,} need a look"))
  else:
    lines.append(("Need a look", f"{review:,} of {listed:,} rows are not VALID"))
  data = [[_p(clean(k), st["bold"]), _p(clean(v), st["cell"])] for k, v in lines]
  info = Table(data, colWidths=[52 * mm, 86 * mm])
  info.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, GRID), ("BACKGROUND", (0, 0), (0, -1), SOFT), ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
  ok = reco["ok"]
  colour = "#15803d" if ok else "#b91c1c"
  twice = "" if reco["duplicates"] == 0 else f" {reco['duplicates']:,} rows appear twice."
  verdict = (f"<b>Row count check: {'PASSED' if ok else 'FAILED'}.</b> The database counts {expected:,} rows for this view and this report lists {listed:,}."
    + (" No row appears twice." if reco["duplicates"] == 0 else twice))
  banner = Table([[_p(f'<font color="{colour}">{verdict}</font>', st["body"])]], colWidths=[138 * mm])
  banner.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor(colour)), ("BACKGROUND", (0, 0), (-1, -1), SOFT),
    ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
  return [info, Spacer(1, 5), banner]

def _floor_table(st, reco: dict) -> Table:
  data = [[_p("Floor", st["head"]), _p("Rows", st["headr"])]]
  for name, count in reco["floors"].items():
    data.append([_p(clean(name), st["cell"]), _p(f"{count:,}", st["cellr"])])
  data.append([_p("All floors", st["bold"]), _p(f"{sum(reco['floors'].values()):,}", st["boldr"])])
  n = len(data) - 1
  return _table(data, [50 * mm, 18 * mm], [("BACKGROUND", (0, n), (-1, n), BAND)])

def _kind_table(st, reco: dict) -> Table:
  data = [[_p("Type", st["head"]), _p("Rows", st["headr"]), _p("Unit", st["head"]), _p("Total quantity", st["headr"])]]
  ordered = sorted(reco["quantities"].items(), key=lambda kv: (kind_rank(kv[0][0]), natural(kv[0][0]), natural(kv[0][1])))
  last = None
  for (kind, unit), (count, total) in ordered:
    label = KIND_LABEL.get(kind, kind) if kind != last else ""
    data.append([_p(clean(label), st["cell"]), _p(f"{count:,}", st["cellr"]), _p(clean(unit), st["cell"]), _p(num(total, 3), st["cellr"])])
    last = kind
  data.append([_p("All types", st["bold"]), _p(f"{reco['listed']:,}", st["boldr"]), "", ""])
  n = len(data) - 1
  return _table(data, [40 * mm, 20 * mm, 20 * mm, 40 * mm], [("BACKGROUND", (0, n), (-1, n), BAND)])

def _status_table(st, reco: dict) -> Table:
  data = [[_p("Status", st["head"]), _p("Rows", st["headr"])]]
  seen = list(STATUS_ORDER) + [s for s in reco["statuses"] if s not in STATUS_ORDER]
  for status in seen:
    if reco["statuses"].get(status):
      data.append([_p(f'<font color="{STATUS_COLOR.get(status, "#475569")}"><b>{clean(status)}</b></font>', st["cell"]), _p(f"{reco['statuses'][status]:,}", st["cellr"])])
  data.append([_p("All statuses", st["bold"]), _p(f"{reco['listed']:,}", st["boldr"])])
  n = len(data) - 1
  return _table(data, [38 * mm, 18 * mm], [("BACKGROUND", (0, n), (-1, n), BAND)])

def _sheet_table(st, sheets: list[dict], listed: int) -> Table:
  data = [[_p("Sheet", st["head"]), _p("Title", st["head"]), _p("Floor", st["head"]), _p("State", st["head"]), _p("Rows", st["headr"]), _p("Note", st["head"])]]
  total = 0
  for sh in sheets:
    total += sh["items"]
    note = sh["message"] or ""
    data.append([_p(str(sh["page_no"]), st["cell"]), _p(clean(sh["title"], 80), st["cell"]), _p(clean(sh["level"] or "", 40), st["cell"]),
      _p(SHEET_STATE_LABEL.get(sh["state"], sh["state"]), st["cell"]), _p(f"{sh['items']:,}", st["cellr"]), _p(clean(note, 220), st["cell"])])
  data.append([_p("All sheets", st["bold"]), "", "", "", _p(f"{total:,}", st["boldr"]), _p("Equals the rows of this report." if total == listed else
    f"The report lists {listed:,} rows; {listed - total:,} are not tied to a sheet in this list.", st["muted"])])
  n = len(data) - 1
  return _table(data, [14 * mm, 70 * mm, 36 * mm, 24 * mm, 14 * mm, 119 * mm], [("BACKGROUND", (0, n), (-1, n), BAND), ("SPAN", (0, n), (3, n))])

SEVERITY_RANK = {"error": 0, "warning": 1, "info": 2}
SEVERITY_LABEL = {"error": "Error", "warning": "Warning", "info": "Note"}
SEVERITY_COLOR = {"error": "#b91c1c", "warning": "#b45309", "info": "#475569"}
ROW_NUMBERS_CAP = 700

def ranges(numbers: list[int]) -> str:
  """1, 2, 3, 7, 9, 10 -> '1-3, 7, 9-10'."""
  out, nums = [], sorted(set(numbers))
  i = 0
  while i < len(nums):
    j = i
    while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
      j += 1
    out.append(str(nums[i]) if i == j else f"{nums[i]}-{nums[j]}")
    i = j + 1
  return ", ".join(out)

def flag_summary(rows: list, numbers: dict) -> list[dict]:
  """Every flag code that appears on the rows: how many rows carry it, which rows, and what it says. A row with a status but no recorded reason is listed
  under NO_REASON_RECORDED so no row that needs a look goes missing."""
  
  buckets: dict = {}
  for row in rows:
    n = numbers[id(row)]
    issues = issue_list(row)
    if not issues and (getattr(row, "normalization_status", None) or "PENDING") != "VALID":
      issues = [{"code": "NO_REASON_RECORDED", "severity": "warning", "message": "The row is not VALID and no reason was recorded."}]
    for issue in issues:
      code = issue.get("code") or "UNCODED"
      sev = issue.get("severity") if issue.get("severity") in SEVERITY_RANK else "info"
      slot = buckets.setdefault(code, {"code": code, "severity": sev, "rows": [], "messages": Counter()})
      if SEVERITY_RANK[sev] < SEVERITY_RANK[slot["severity"]]:
        slot["severity"] = sev
      if n not in slot["rows"]:
        slot["rows"].append(n)
      if issue.get("message"):
        slot["messages"][issue["message"]] += 1
  return sorted(buckets.values(), key=lambda b: (SEVERITY_RANK[b["severity"]], -len(b["rows"]), b["code"]))

def _flag_story(st, rows: list, numbers: dict, facts: dict | None, checks: list, level_names: dict | None) -> list:
  story: list = [_p("Flags", st["h2"])]
  flagged = [r for r in rows if (getattr(r, "normalization_status", None) or "PENDING") != "VALID"]
  sheets_open = [s for s in (facts or {}).get("sheets", []) if s["state"] != "READ"]
  if sheets_open:
    story.append(_p("Sheets that were not read", st["bold"]))
    data = [[_p("Sheet", st["head"]), _p("State", st["head"]), _p("Why", st["head"])]]
    
    for s in sheets_open:
      data.append([_p(str(s["page_no"]), st["cell"]), _p(SHEET_STATE_LABEL.get(s["state"], s["state"]), st["cell"]),
        _p(clean(s["message"] or "Press Read sheets. If it stays unread, confirm the scale of that sheet on the Measure page.", 300), st["cell"])])
    story += [_table(data, [16 * mm, 30 * mm, 231 * mm]), Spacer(1, 6)]
    
  if checks:
    story.append(_p("Checks on the drawing", st["bold"]))
    data = [[_p("Severity", st["head"]), _p("Check", st["head"]), _p("What it found", st["head"]), _p("Marks", st["head"]), _p("Sheets", st["head"])]]
    for c in checks:
      sev = "warning" if c.get("severity") == "warning" else "info"
      data.append([_p(f'<font color="{SEVERITY_COLOR[sev]}"><b>{SEVERITY_LABEL[sev]}</b></font>', st["cell"]), _p(clean(c.get("title"), 90), st["cell"]),
        _p(clean(c.get("message"), 420), st["cell"]), _p(clean(", ".join(c.get("marks") or []), 80), st["cell"]),
        _p(clean(", ".join(str(p) for p in (c.get("pages") or [])), 40), st["cell"])])
    story += [_table(data, [18 * mm, 48 * mm, 148 * mm, 40 * mm, 23 * mm]), Spacer(1, 6)]
  summary = flag_summary(rows, numbers)
  if summary:
    story.append(_p(f"Flags on the rows: {len(flagged):,} of {len(rows):,} rows need a look", st["bold"]))
    story.append(_p("Each flag is explained once, with the numbers of the rows that carry it (the # column of the register).", st["note"]))
    data = [[_p("Flag", st["head"]), _p("Severity", st["head"]), _p("Rows", st["headr"]), _p("What it says", st["head"]), _p("Row numbers", st["head"])]]
    
    for b in summary:
      msgs = b["messages"].most_common()
      said = msgs[0][0] if msgs else ""
      if len(msgs) > 1:
        said += f" (This flag is worded {len(msgs)} ways across the rows; the most common is shown.)"
      numbers_text = ranges(b["rows"])
      if len(numbers_text) > ROW_NUMBERS_CAP:
        numbers_text = numbers_text[:ROW_NUMBERS_CAP].rsplit(",", 1)[0] + f", ... (the register lists the rest)"
      data.append([_p(clean(b["code"], 60), st["cell"]), _p(f'<font color="{SEVERITY_COLOR[b["severity"]]}"><b>{SEVERITY_LABEL[b["severity"]]}</b></font>', st["cell"]),
        _p(f"{len(b['rows']):,}", st["cellr"]), _p(clean(said, MAX_CELL), st["cell"]), _p(clean(numbers_text, ROW_NUMBERS_CAP + 40), st["cell"])])
    story.append(_table(data, [44 * mm, 17 * mm, 12 * mm, 110 * mm, 94 * mm]))
  elif not sheets_open and not checks:
    story.append(_p("Nothing is flagged: every row is VALID and no sheet or check needs attention.", st["body"]))
  return story

def _register_story(st, rows: list, is_pdf: bool, level_names: dict | None) -> tuple[list, dict]:
  cols = _columns(is_pdf)
  widths = [w * mm for _, w, _ in cols]
  head = [_p(clean(name), st["headr"] if right else st["head"]) for name, _, right in cols]
  per_floor = Counter((level_of(r, level_names) or NO_FLOOR) for r in rows)
  data: list = [head]
  extra: list = []
  numbers: dict = {}
  floor = object()
  
  for index, row in enumerate(rows, start=1):
    numbers[id(row)] = index
    name = level_of(row, level_names) or NO_FLOOR
    if name != floor:
      floor = name
      data.append([_p(f"{clean(name)}  —  {per_floor[name]:,} rows", st["band"])] + [""] * (len(cols) - 1))
      at = len(data) - 1
      extra += [("SPAN", (0, at), (-1, at)), ("BACKGROUND", (0, at), (-1, at), BAND)]
    status = getattr(row, "normalization_status", None) or "PENDING"
    first, second = size_lines(row)
    size = clean(first) + (f"<br/>{clean(second)}" if second else "")
    role = clean(getattr(row, "structural_role", None) or "")
    predefined = getattr(row, "predefined_type", None)
    
    if predefined and predefined != getattr(row, "structural_role", None):
      role += f" ({clean(predefined)})"
    mode = MODE_LABEL.get(measure_mode(row), "")
    as_text = clean(getattr(row, "measured_as", None) or "", 260)
    measured = (f"<b>{clean(mode)}</b>" if mode else "") + (f"<br/>{as_text}" if as_text else "")
    codes = issue_codes(row)
    flags = ", ".join(clean(c.replace("_", " "), 40) for c in codes)
    quantity = (num(getattr(row, "quantity", None)) + (" " + clean(getattr(row, "unit", None) or "") if getattr(row, "unit", None) else "")).strip()
    last = clean(str(pdf_meta(row).get("page_no") or "")) if is_pdf else clean(getattr(row, "ifc_global_id", None) or "", 40)
    data.append([
      _p(str(index), st["cellr"]), _p(clean(getattr(row, "ifc_type", ""), 40), st["cell"]), _p(clean(getattr(row, "name", None) or "", 160), st["cell"]),
      _p(role, st["cell"]), _p(clean(getattr(row, "discipline", None) or ""), st["cell"]), _p(clean(level_of(row, level_names)), st["cell"]),
      _p(clean(getattr(row, "raw_material_text", None) or "", 160), st["cell"]), _p(quantity, st["cellr"]), _p(size, st["cell"]),
      _p(f'<font color="{STATUS_COLOR.get(status, "#475569")}"><b>{clean(status)}</b></font>', st["cell"]), _p(measured, st["cell"]), _p(flags, st["cell"]),
      _p(last, st["cell"]),
    ])
  return [_table(data, widths, extra)], numbers

def build_elements_pdf(*, drawing_name: str, drawing_format: str, revision: str | None, organization: str, generated_at: datetime, rows: list, expected: int,
  everything: int, filters: dict | None = None, level_names: dict | None = None, facts: dict | None = None, checks: list | None = None) -> bytes:
  """The report. `rows` are the register rows the screen lists (in any order); `expected` is the count the database gave for the same filter and
  `everything` the count with no filter. `facts` (PDF drawings only) carries the sheets; `checks` the checks made on the drawing."""
  
  filters = filters or {}
  rows = sort_rows(list(rows), level_names)
  is_pdf = str(drawing_format).upper().endswith("PDF")
  reco = reconcile(rows, expected, everything, level_names)
  st = _styles()
  buffer = BytesIO()
  doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=12 * mm, bottomMargin=15 * mm, leftMargin=10 * mm, rightMargin=10 * mm,
    title=f"Elements register - {clean(drawing_name, 120)}", author=clean(organization, 80))
  stamp = generated_at.strftime("%d %B %Y, %H:%M") + (" UTC" if generated_at.tzinfo is not None else "")
  verdict = f"{reco['listed']:,} rows - count check {'passed' if reco['ok'] else 'FAILED'}"
  maker = _canvas_class(f"{clean(organization, 60)} | {clean(drawing_name, 70)} | {stamp}".replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">"), verdict)

  story: list = [
    _p("Elements register", st["title"]),
    _p(f"{clean(drawing_name)} &nbsp;|&nbsp; {clean(str(drawing_format).split('.')[-1])}" + (f" &nbsp;|&nbsp; Revision {clean(revision)}" if revision else "") +
      f" &nbsp;|&nbsp; {clean(organization)} &nbsp;|&nbsp; Made {clean(stamp)}", st["sub"]),
    Spacer(1, 8),
    
  ]
  block = _summary_block(st, reco, is_pdf, facts, rows, filters)
  by_floor, by_kind, by_status = _floor_table(st, reco), _kind_table(st, reco), _status_table(st, reco)
  grid = Table([[block, [by_floor], [by_status]]], colWidths=[142 * mm, 72 * mm, 62 * mm])
  grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
  story += [grid, Spacer(1, 4), KeepTogether([_p("Rows by type, with the quantity each adds up to", st["h2"]), by_kind])]
  if is_pdf and facts and facts.get("sheets"):
    story += [Spacer(1, 4), _p("Rows by sheet", st["h2"]), _sheet_table(st, facts["sheets"], reco["listed"])]
  story.append(Spacer(1, 6))
  story.append(_p("The rows are listed floor by floor, lowest first, and inside a floor by kind (footings, columns, beams, walls, rooms, doors, windows) and then by mark: the "
    "order of the elements screen. The row numbers here are the row numbers there.", st["note"]))

  register, numbers = _register_story(st, rows, is_pdf, level_names)
  story += [PageBreak()] + _flag_story(st, rows, numbers, facts, checks or [], level_names)
  story += [Spacer(1, 10), _p(f"Register - {reco['listed']:,} rows", st["h2"])] + register
  story += [Spacer(1, 6), _p(f"<b>End of register.</b> {reco['listed']:,} rows listed, numbered 1 to {reco['listed']:,}." if rows else "<b>End of register.</b> This view has no rows.", st["body"])]
  doc.build(story, canvasmaker=maker)
  return buffer.getvalue()
