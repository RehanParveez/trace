from __future__ import annotations
from decimal import Decimal
import re
from app.modules.drawings_boq.schedule_parsing import MAX_ROWS, ScheduleParseError, _clean, _length_mm, _header_key, parse_decimal, table_from_layout_text

CSV_CONFIDENCE = Decimal("0.9")
PDF_TEXT_CONFIDENCE = Decimal("0.7")
GUESSED_UNIT_CONFIDENCE = Decimal("0.5")
_SHAPE_PARAMS = ("A", "B", "C", "D", "E")

_HEADERS = {
  "member_mark": {"member", "member mark", "member no", "member id", "element", "element mark", "location", "tag"},
  "mark": {"mark", "bar mark", "bar no", "bar", "bar ref", "item", "ref"},
  "role": {"role", "member type", "type of member", "structure", "structural element", "element type", "use"},
  "shape": {"shape", "shape code", "bend", "bar shape", "shape type"},
  "size": {"size", "dia", "diameter", "bar size", "bar dia", "dia mm", "size mm", "type size", "bar type"},
  "grade": {"grade", "steel grade", "bar grade", "fy", "strength"},
  "count": {"no", "nos", "no of bars", "number", "qty", "quantity", "count", "no bars", "total no", "total nos"},
  "spacing": {"spacing", "spacing mm", "c c", "cc", "centres", "centers"},
  "length": {"length", "cut length", "length each", "length of each bar", "bar length", "cutting length", "len", "length mm", "length m"},
  "weight": {"weight", "total weight", "weight kg", "total kg", "wt", "total wt", "kg"},
  "level": {"level", "storey", "story", "floor"},
}

_PARAM_HEADERS = {p.lower(): p for p in _SHAPE_PARAMS} | {f"dim {p.lower()}": p for p in _SHAPE_PARAMS}
_LOOKUP = {name: key for key, names in _HEADERS.items() for name in names}
_ROLE_WORDS = (("column", "COLUMN"), ("beam", "BEAM"), ("lintel", "LINTEL"), ("slab", "SLAB"), ("footing", "FOOTING"),
  ("foundation", "FOOTING"), ("raft", "FOOTING"), ("pile", "PILE"), ("wall", "WALL"), ("stair", "STAIR"))

def infer_role(*texts) -> str | None:
  hay = " ".join(str(t or "") for t in texts).lower()
  for word, role in _ROLE_WORDS:
    if word in hay:
      return role
  return None

def parse_bar_size(text) -> tuple[str | None, Decimal | None]:
  """'#4' -> ('#4', 19.05 style by n*3.175); 'T12', 'Y12', 'Ø12', '12 mm', '12' -> ('12', 12)."""
  s = str(text or "").strip()
  if not s:
    return None, None
  m = re.fullmatch(r"#\s*(\d{1,2})", s)
  if m:
    n = int(m.group(1))
    return f"#{n}", (Decimal(n) * Decimal("3.175")).quantize(Decimal("0.001"))
  m = re.fullmatch(r"(?:[a-zA-Z\u00d8\u03a6\u03c6\u2300]{1,2})?\s*(\d{1,2}(?:\.\d+)?)\s*(?:mm)?", s)
  if m:
    n = Decimal(m.group(1))
    return (str(n.normalize()) if n == n.to_integral_value() else str(n)), n
  return None, None

def parse_grade(text) -> str | None:
  s = re.sub(r"\s+", " ", str(text or "")).strip().upper()
  return s[:30] or None

_UNIT_WORDS = ("mm", "cm", "m", "ft", "in", "kg", "ton", "tons", "tonne", "mt")

def _lookup_key(cell, table: dict) -> str | None:
  k = _header_key(cell)
  for _ in range(2):
    if k in table:
      return k
    head, _, tail = k.rpartition(" ")
    if not head or tail not in _UNIT_WORDS:
      return None
    k = head
  return k if k in table else None

def _col_unit(header) -> str | None:
  t = str(header or "").lower()
  m = re.search(r"\((mm|cm|m|ft|in)\)|\b(mm|cm)\b|\bin (m|ft)\b", t)
  if m:
    return next(g for g in m.groups() if g)
  return "m" if re.search(r"\blength m\b", t) else None

def _to_mm(value, unit) -> tuple[Decimal | None, str | None]:
  if value in (None, ""):
    return None, None
  if unit in ("ft", "in") and re.fullmatch(r"\d+(?:\.\d+)?", str(value).strip()):
    return (Decimal(str(value).strip()) * (Decimal("304.8") if unit == "ft" else Decimal("25.4"))).quantize(Decimal("0.001")), None
  return _length_mm(str(value), unit)

def _find_header(table: list[list]):
  best = None
  for i, row in enumerate(table[:200]):
    keys = {j: _LOOKUP[k] for j, c in enumerate(row) if (k := _lookup_key(c, _LOOKUP))}
    params = {j: _PARAM_HEADERS[k] for j, c in enumerate(row) if (k := _lookup_key(c, _PARAM_HEADERS))}
    vals = set(keys.values())
    if "size" in vals and "count" in vals and (vals & {"length", "shape", "mark", "weight"}):
      score = len(keys) + len(params)
      if best is None or score > best[0]:
        best = (score, i, keys, params)
  return best

def _row_from_cells(cells: dict, params: dict, units: dict, default_unit_for_length: str | None) -> dict | None:
  designation, dia = parse_bar_size(cells.get("size"))
  count_d = parse_decimal(cells.get("count"))
  mark = _clean(cells.get("mark")) or _clean(cells.get("member_mark"))
  if not (mark or designation or count_d):
    return None

  count = int(count_d) if count_d is not None and count_d >= 0 else None
  length, length_note = _to_mm(cells.get("length"), units.get("length") or default_unit_for_length)
  weight = parse_decimal(cells.get("weight"))
  notes: list[str] = []
  if length_note:
    notes.append(f"Cut length has no unit; {length_note.lower()} Check it.")
  
  if units.get("weight") == "ton" and weight is not None:
    weight, _ = weight * 1000, notes.append("Weight read as tonnes.")
    
  shape_params: dict = {}
  for p in params:
    v, note = _to_mm(cells.get(f"param:{p}"), units.get("param"))
    if v is not None:
      shape_params[p] = str(v)
      if note:
        notes.append(f"Dimension {p} has no unit; {note.lower()} Check it.")
  spacing = parse_decimal(cells.get("spacing"))
  member = _clean(cells.get("member_mark"))
  role_text = _clean(cells.get("role"))
  role = infer_role(role_text) or infer_role(member) or (role_text.upper()[:50] if role_text else None)
  
  return {"member_mark": member, "mark": mark, "role": role, "shape_code": (_clean(cells.get("shape")) or "").upper()[:40] or None,
    "shape_params": shape_params, "designation": designation, "dia_mm": dia, "grade": parse_grade(cells.get("grade")),
    "count": count, "spacing_mm": spacing if spacing and spacing > 0 else None, "cut_len_mm": length if length and length > 0 else None,
    "declared_total_kg": weight if weight and weight > 0 else None, "level_text": _clean(cells.get("level")), "notes": notes,
    "guessed_unit": bool(length_note) or any(n.startswith("Dimension") for n in notes)}

def rows_from_table(table: list[list], *, confidence: Decimal = CSV_CONFIDENCE, length_unit: str | None = None) -> list[dict]:
  found = _find_header(table)
  if found is None:
    raise ScheduleParseError("Could not find the bar schedule header. Expected columns such as mark, size/dia, no and length.")
  _, hdr, keys, params = found
  header = table[hdr]
  units = {"length": next((_col_unit(header[j]) for j, k in keys.items() if k == "length"), None),
    "weight": "ton" if any(k == "weight" and re.search(r"\b(ton|tons|tonne|mt)\b", str(header[j]).lower()) for j, k in keys.items()) else "kg",
    "param": next((_col_unit(header[j]) for j in params), None)}
  
  out: list[dict] = []
  for raw in table[hdr + 1:]:
    cells: dict = {}
    for j, key in keys.items():
      if j < len(raw) and raw[j] not in (None, ""):
        cells.setdefault(key, raw[j])
    for j, p in params.items():
      if j < len(raw) and raw[j] not in (None, ""):
        cells[f"param:{p}"] = raw[j]
    row = _row_from_cells(cells, {p: p for p in params.values()}, units, length_unit)
    if row is None:
      continue
  
    row["raw_text"] = " | ".join(str(c) for c in raw if c not in (None, ""))[:2000]
    row["confidence"] = min(confidence, GUESSED_UNIT_CONFIDENCE) if row.pop("guessed_unit") else confidence
    out.append(row)
    if len(out) > MAX_ROWS:
      raise ScheduleParseError(f"The schedule has more than {MAX_ROWS} rows. Split it and import in parts.")
  if not out:
    raise ScheduleParseError("No bar rows found under the header.")
  return out

def rows_from_pdf_text(text: str) -> list[dict]:
  table = table_from_layout_text(text, header_probe=lambda row: _find_header([row]) is not None)
  return rows_from_table(table, confidence=PDF_TEXT_CONFIDENCE)