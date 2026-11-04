from __future__ import annotations
import hashlib
import math
from pathlib import Path
from decimal import Decimal
from app.modules.drawings_boq.rebar.bbs_layouts import BbsDocument
from dataclasses import dataclass, field
import yaml
from app.engine.measure.rebar import RebarError, cut_from_shape

AUDIT_VERSION = "L1.1"
RULES_PATH = Path(__file__).with_name("rebar_audit_rules.yaml")
KG_M_DIVISOR = Decimal("162")
FT_PER_M = Decimal("3.2808")
MM_PER_BAR_NO = Decimal("3.175")
MM_PER_FT = Decimal("304.8")
MM_PER_IN = Decimal("25.4")
ZERO = Decimal("0")
CLASS_ERROR, CLASS_METHOD, CLASS_ROUNDING, CLASS_INFO = "ERROR", "METHOD", "ROUNDING", "INFO"
STIRRUP_WORDS = ("ring", "stirrup", "tie")

@dataclass
class Bands:
  unit_weight_share: Decimal
  length_product_share: Decimal
  fractional_tolerance: Decimal
  sheet_sum_kg: Decimal
  cut_from_parts_in: Decimal
  digest: str

@dataclass
class Finding:
  code: str
  finding_class: str
  rule: str
  bbs_ref: dict
  bbs_value: str | None = None
  trace_value: str | None = None
  diff_kg: Decimal | None = None
  diff_pct: Decimal | None = None
  confidence: Decimal = Decimal("1")
  question: str | None = None

@dataclass
class L1Result:
  findings: list = field(default_factory=list)
  totals: dict = field(default_factory=dict)

def load_bands(text: str | None = None) -> Bands:
  raw = text if text is not None else RULES_PATH.read_text(encoding="utf-8")
  data = yaml.safe_load(raw) or {}
  def pick(key: str) -> Decimal:
    return Decimal(str(data[key]))
  return Bands(unit_weight_share=pick("unit_weight_share"), length_product_share=pick("length_product_share"),
    fractional_tolerance=pick("fractional_tolerance"), sheet_sum_kg=pick("sheet_sum_kg"), cut_from_parts_in=pick("cut_from_parts_in"),
    digest=hashlib.sha256(raw.encode("utf-8")).hexdigest())

def exact_kg_per_ft(dia_no: int) -> Decimal:
  d = Decimal(dia_no) * MM_PER_BAR_NO
  return d * d / KG_M_DIVISOR / FT_PER_M

def _ref(doc: BbsDocument, row) -> dict:
  sheet = next((s for s in doc.sheets if s.index == row.sheet), None)
  return {"page": row.page, "sheet": row.sheet, "sheet_name": sheet.name if sheet else None, "member": row.member, "sr": row.sr,
    "y": row.y, "description": row.description}

def _num(value) -> str | None:
  return None if value is None else str(value)

def _pct(part: Decimal, whole: Decimal) -> Decimal | None:
  return None if not whole else (part / whole * 100).quantize(Decimal("0.001"))

def _shape_code(row, shapes: dict) -> tuple[str | None, list]:
  parts = [p for p in row.parts if p > 0]
  n = len(parts)
  text = (row.description or "").lower()
  if n == 1:
    code = "STRAIGHT"
  elif n == 2 and any(w in text for w in STIRRUP_WORDS):
    code = "STIRRUP_RECT"
  elif n == 2:
    code = "L_BAR"
  else:
    return None, parts
  return (code if code in shapes else None), parts

def _check_cut_from_parts(doc, row, shapes, rule, bands, out: L1Result) -> None:
  code, parts = _shape_code(row, shapes) if shapes else (None, [])
  if code is None or row.cut_ft is None:
    out.totals["cut_from_parts_skipped"] = out.totals.get("cut_from_parts_skipped", 0) + 1
    return

  shape = shapes[code]
  rule = rule.get("STIRRUP" if shape.is_link else "MAIN") if isinstance(rule, dict) else rule
  names = list(dict.fromkeys(shape.segments))
  params = {names[i]: p * MM_PER_FT for i, p in enumerate(parts) if i < len(names)}
  
  try:
    cut_mm, _ = cut_from_shape(shape, params, Decimal(row.dia) * MM_PER_BAR_NO if row.dia else ZERO, rule)
  except RebarError:
    out.totals["cut_from_parts_skipped"] = out.totals.get("cut_from_parts_skipped", 0) + 1
    return
  out.totals["cut_from_parts_checked"] = out.totals.get("cut_from_parts_checked", 0) + 1
  tol = bands.cut_from_parts_in * MM_PER_IN
  printed_mm = row.cut_ft * MM_PER_FT
  if abs(cut_mm - printed_mm) <= tol:
    out.totals["cut_from_parts_match"] = out.totals.get("cut_from_parts_match", 0) + 1
    return
  plain_mm = sum(parts, ZERO) * MM_PER_FT
  if abs(plain_mm - printed_mm) <= tol:
    klass, question = CLASS_METHOD, "The printed cut length is the plain sum of the sketch parts; the engine's bend and hook rules give another length."
  elif printed_mm > cut_mm and printed_mm > plain_mm:
    klass, question = CLASS_METHOD, "The printed cut length is longer than the sketch parts need. Is there a hook or lap allowance that the sketch does not show?"
  else:
    klass, question = CLASS_ERROR, None
  out.findings.append(Finding("CUT_FROM_PARTS", klass, "cut length from the sketch parts", _ref(doc, row),
    bbs_value=f"{row.cut_ft} ft", trace_value=f"{(cut_mm / MM_PER_FT).quantize(Decimal('0.01'))} ft ({code})",
    diff_kg=None, confidence=Decimal("0.7"), question=question))

def run_l1(doc: BbsDocument, bands: Bands, shapes: dict | None = None, rule=None) -> L1Result:
  out = L1Result()
  out.totals.update({"rows": len(doc.rows), "sheets": len(doc.sheets), "cut_from_parts_checked": 0, "cut_from_parts_match": 0, "cut_from_parts_skipped": 0})
  seen: dict = {}
  unit_dev_kg = ZERO
  unit_rows = 0
  frac_kg = ZERO
  
  for row in doc.rows:
    ref = _ref(doc, row)
    if row.total_ft is not None and row.total_kg:
      expect = row.total_ft * exact_kg_per_ft(row.dia) if row.dia else None
      if expect is not None:
        unit_dev_kg += expect - row.total_kg
        unit_rows += 1
        if abs(expect - row.total_kg) > bands.unit_weight_share * row.total_kg:
          out.findings.append(Finding("UNIT_WEIGHT", CLASS_ERROR, "row kg against total length times the unit weight", ref,
            bbs_value=f"{row.total_kg} kg", trace_value=f"{expect.quantize(Decimal('0.01'))} kg", diff_kg=(row.total_kg - expect).quantize(Decimal("0.01")),
            diff_pct=_pct(row.total_kg - expect, expect)))
          
    if row.total is not None and row.cut_ft and row.total_ft is not None:
      product = row.total * row.cut_ft
      gap = abs(product - row.total_ft)
      if gap > max(row.cut_ft, bands.length_product_share * row.total_ft):
        out.findings.append(Finding("LENGTH_PRODUCT", CLASS_ERROR, "total length against bars times cut length", ref,
          bbs_value=f"{row.total_ft} ft", trace_value=f"{product.quantize(Decimal('0.01'))} ft", diff_pct=_pct(row.total_ft - product, product)))
        
      q = row.total_ft / row.cut_ft
      if abs(q - round(q)) > bands.fractional_tolerance:
        extra_bars = Decimal(math.ceil(q)) - q
        kg = (extra_bars * row.cut_ft * (row.unit_kg_ft or ZERO)).quantize(Decimal("0.01"))
        frac_kg += kg
        out.findings.append(Finding("FRACTIONAL_BARS", CLASS_ROUNDING, "total length is not a whole number of bars", ref,
          bbs_value=f"{row.total} bars billed", trace_value=f"{q.quantize(Decimal('0.01'))} bars by length", diff_kg=kg))
        
    if None not in (row.members, row.each, row.total) and row.members * row.each != row.total:
      out.findings.append(Finding("MEMBERS_EACH", CLASS_ROUNDING, "members times bars each is not the bars total", ref,
        bbs_value=f"{row.members} x {row.each}", trace_value=f"{row.members * row.each}", confidence=Decimal("0.9")))
    _check_cut_from_parts(doc, row, shapes, rule, bands, out)
    key = (row.sheet, row.member, row.description, row.dia, row.total, row.cut_ft, row.total_kg, tuple(row.parts))
    if key in seen:
      out.findings.append(Finding("DUPLICATE_MEMBER", CLASS_ERROR, "same member, description, numbers and sketch in two places", ref,
        bbs_value=f"page {row.page} Sr {row.sr}", trace_value=f"also page {seen[key].page} Sr {seen[key].sr}", diff_kg=row.total_kg))
    else:
      seen[key] = row
      
  by_sheet: dict = {}
  by_sheet_dia: dict = {}
  for row in doc.rows:
    by_sheet[row.sheet] = by_sheet.get(row.sheet, ZERO) + (row.total_kg or ZERO)
    k = (row.sheet, str(row.dia))
    by_sheet_dia[k] = by_sheet_dia.get(k, ZERO) + (row.total_kg or ZERO)
  printed_sum = ZERO
  for sheet in doc.sheets:
    ref = {"page": sheet.first_page, "sheet": sheet.index, "sheet_name": sheet.name, "member": None, "sr": None, "y": None}
    if sheet.printed_total_kg is None:
      continue
  
    printed_sum += sheet.printed_total_kg
    diff = by_sheet.get(sheet.index, ZERO) - sheet.printed_total_kg
    if abs(diff) > bands.sheet_sum_kg:
      out.findings.append(Finding("SHEET_SUM", CLASS_ERROR, "rows against the printed sheet total", ref, bbs_value=f"{sheet.printed_total_kg} kg",
        trace_value=f"{by_sheet.get(sheet.index, ZERO)} kg", diff_kg=diff.quantize(Decimal("0.01")), diff_pct=_pct(diff, sheet.printed_total_kg)))
      
    for dia, printed in sheet.dia_totals_kg.items():
      if str(dia).isdigit():
        d = by_sheet_dia.get((sheet.index, str(dia)), ZERO) - printed
        if abs(d) > bands.sheet_sum_kg:
          out.findings.append(Finding("DIA_TOTALS", CLASS_INFO, "rows of one bar size against the printed size total", ref,
            bbs_value=f"#{dia}: {printed} kg", trace_value=f"{by_sheet_dia.get((sheet.index, str(dia)), ZERO)} kg", diff_kg=d.quantize(Decimal("0.01"))))
          
  rows_sum = sum(by_sheet.values(), ZERO)
  out.findings.append(Finding("GRAND_TOTAL", CLASS_INFO, "printed sheet totals against the rows", {"page": None, "sheet": None, "sheet_name": None, "member": None, "sr": None, "y": None},
    bbs_value=f"{printed_sum} kg", trace_value=f"{rows_sum} kg", diff_kg=(rows_sum - printed_sum).quantize(Decimal("0.01"))))
  if unit_rows and abs(unit_dev_kg) > ZERO:
    share = unit_dev_kg / sum((r.total_kg or ZERO for r in doc.rows), ZERO) * 100
    if abs(share) >= Decimal("0.2"):
      out.findings.append(Finding("UNIT_WEIGHT_CONVENTION", CLASS_INFO, "the schedule's weights sit below d squared over 162 on every row",
        {"page": None, "sheet": None, "sheet_name": None, "member": None, "sr": None, "y": None},
        bbs_value="schedule weights", trace_value="d2/162 per metre", diff_kg=(-unit_dev_kg).quantize(Decimal("0.01")), diff_pct=share.quantize(Decimal("0.001")),
        question="The schedule seems to weigh bars by a constant slightly below d2/162 (about d2/533 per foot). Confirm the weight rule the QS used."))
      
  counters = doc.page_counters
  totals_set = sorted({m for _, m in counters})
  nums = [n for n, _ in counters]
  if counters and (any(m != doc.pages for m in totals_set) or nums != list(range(nums[0], nums[0] + len(nums)))):
    out.findings.append(Finding("PAGE_COUNTER", CLASS_INFO, "the printed page counter against the page count",
      {"page": None, "sheet": None, "sheet_name": None, "member": None, "sr": None, "y": None},
      bbs_value="of " + ", ".join(str(m) for m in totals_set), trace_value=f"{doc.pages} pages in the file"))
  out.totals.update({"printed_total_kg": str(printed_sum), "rows_total_kg": str(rows_sum), "fractional_round_up_kg": str(frac_kg.quantize(Decimal("0.01"))),
    "unit_weight_deviation_kg": str(unit_dev_kg.quantize(Decimal("0.01")))})
  counts: dict = {}
  for f in out.findings:
    counts[f.code] = counts.get(f.code, 0) + 1
  out.totals["by_code"] = counts
  out.totals["by_class"] = {c: sum(1 for f in out.findings if f.finding_class == c) for c in (CLASS_ERROR, CLASS_METHOD, CLASS_ROUNDING, CLASS_INFO)}
  return out

DIFF_FIELDS = ("dia", "spacing_in", "members", "each", "total", "cut_ft", "total_ft", "total_kg")
DIFF_LIMIT = 200

def row_keys(rows: list, sheet_names: dict) -> list:
  seen: dict = {}
  keys = []
  for r in rows:
    base = f"{sheet_names.get(r.sheet, '')}|{r.member}|{r.sr}|{r.description}"
    seen[base] = seen.get(base, 0) + 1
    keys.append(base if seen[base] == 1 else f"{base}#{seen[base]}")
  return keys

def diff_rows(old_rows: list, old_names: dict, new_rows: list, new_names: dict) -> dict:
  old = dict(zip(row_keys(old_rows, old_names), old_rows))
  new = dict(zip(row_keys(new_rows, new_names), new_rows))
  added = [k for k in new if k not in old]
  removed = [k for k in old if k not in new]
  
  changed = []
  for k in new:
    if k in old:
      delta = {f: [_num(getattr(old[k], f)), _num(getattr(new[k], f))] for f in DIFF_FIELDS if getattr(old[k], f) != getattr(new[k], f)}
      if delta:
        changed.append({"key": k, "fields": delta})
  return {"counts": {"added": len(added), "removed": len(removed), "changed": len(changed), "same": len(new) - len(added) - len(changed)},
    "added": added[:DIFF_LIMIT], "removed": removed[:DIFF_LIMIT], "changed": changed[:DIFF_LIMIT]}
