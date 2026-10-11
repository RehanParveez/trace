from __future__ import annotations
from decimal import Decimal, InvalidOperation
from app.modules.drawings_boq import boq_logic as logic
from dataclasses import dataclass, field
import re
import csv
from collections import Counter, defaultdict
import io
import math
import hashlib
from statistics import median

UNIT_SPELLINGS: dict[str, str] = {
  "cft": "cft", "cu.ft": "cft", "cu.ft.": "cft", "cuft": "cft", "cu ft": "cft", "cubic feet": "cft", "cubic foot": "cft", "c.ft": "cft",
  "sft": "sft", "sq.ft": "sft", "sq.ft.": "sft", "sqft": "sft", "sq ft": "sft", "square feet": "sft", "square foot": "sft", "s.ft": "sft",
  "rft": "rft", "r.ft": "rft", "r.ft.": "rft", "rft.": "rft", "running feet": "rft", "running foot": "rft", "rf": "rft",
  "cum": "m3", "cu.m": "m3", "cu.m.": "m3", "cu m": "m3", "m3": "m3", "m³": "m3", "cubic metre": "m3", "cubic meter": "m3",
  "sqm": "m2", "sq.m": "m2", "sq.m.": "m2", "sq m": "m2", "m2": "m2", "m²": "m2", "square metre": "m2", "square meter": "m2",
  "rm": "m", "rmt": "m", "mtr": "m", "m": "m", "metre": "m", "meter": "m", "r.m": "m", "r.m.": "m",
  "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg",
  "quintal": "quintal", "quintals": "quintal", "qtl": "quintal", "qtls": "quintal",
  "tonne": "tonne", "tonnes": "tonne", "mt": "tonne", "metric ton": "tonne", "metric tonne": "tonne", "m.ton": "tonne", "m.t": "tonne",
  "nos": "nos", "nos.": "nos", "no": "nos", "no.": "nos", "each": "nos", "ea": "nos", "pcs": "nos", "pc": "nos", "piece": "nos",
  "pieces": "nos", "nr": "nos",
}

OTHER_UNITS = {"ton": "ton", "tons": "ton", "bag": "bag", "bags": "bag", "set": "set", "pair": "pair", "l.s": "ls", "l.s.": "ls", "ls": "ls",
  "job": "job", "ltr": "litre", "litre": "litre", "liter": "litre", "gallon": "gallon", "sack": "sack", "day": "day", "month": "month",
  "hour": "hour", "trip": "trip", "point": "point", "pts": "point", "acre": "acre", "marla": "marla", "kanal": "kanal", "ft": "ft"}
BASIS_VALUES = (10, 100, 1000, 10000)

def _unit_alternation() -> str:
  words = sorted({*UNIT_SPELLINGS, *OTHER_UNITS}, key=len, reverse=True)
  return "|".join(re.escape(w) for w in words)

_UNIT_ALT = _unit_alternation()
_BASIS_ALT = "|".join(str(b) for b in sorted(BASIS_VALUES, reverse=True))
_NUM = r"(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
_UNIT_PHRASE = rf"(?:(?:per\s+)?(?:%|(?:{_BASIS_ALT}))\s*)?(?:per\s+)?(?:{_UNIT_ALT})"

@dataclass(frozen=True)
class UnitBasis:
  basis_qty: Decimal
  unit: str | None
  known: bool
  note: str | None = None

def parse_unit_basis(raw: str | None) -> UnitBasis:
  """'% cft', 'per 100 Cft' and '100 cft' all mean a price for 100 cft; '1000 Nos' a price for 1000 pieces."""
  text = re.sub(r"\s+", " ", (raw or "").strip().lower())
  text = re.sub(r"^(rs\.?|pkr)\s*/?\s*", "", text)
  text = re.sub(r"^per\s+", "", text)
  basis = Decimal(1)
  if text.startswith("%"):
    basis, text = Decimal(100), text[1:].strip()
    
  else:
    m = re.match(rf"^({_BASIS_ALT})\s*(.*)$", text)
    if m and m.group(2):
      basis, text = Decimal(m.group(1)), m.group(2).strip()
  text = re.sub(r"^per\s+", "", text).strip(" .") if text not in UNIT_SPELLINGS and text not in OTHER_UNITS else text
  
  if text in UNIT_SPELLINGS:
    canonical = UNIT_SPELLINGS[text]
    known = canonical in logic.UNIT_TABLE
    return UnitBasis(basis, canonical, known, None if known else f"'{canonical}' is not a unit the pricing engine converts")

  if text in OTHER_UNITS:
    other = OTHER_UNITS[text]
    note = "'ton' is ambiguous (metric tonne or imperial ton); pick the unit explicitly" if other == "ton" else f"'{other}' is not a unit the pricing engine converts"
    return UnitBasis(basis, other, False, note)
  return UnitBasis(basis, None, False, f"unit '{raw}' not recognised")

def unit_rate_from(rate: Decimal, basis: Decimal) -> Decimal:
  """Price for one unit: a rate of 450 per 100 cft is 4.50 per cft."""
  return (rate / basis) if basis and basis > 0 else rate

def parse_rate(raw: str | None) -> Decimal | None:
  """'1,234.50', 'Rs. 1234/-', '1234.5' -> Decimal. Anything with two numbers, text, or a minus sign -> None."""
  text = (raw or "").strip()
  text = re.sub(r"^(rs\.?|pkr)\s*", "", text, flags=re.I)
  text = re.sub(r"\s*(/-|/=|-/)\s*$", "", text).strip()
  if not re.fullmatch(_NUM, text):
    return None
  try:
    value = Decimal(text.replace(",", ""))
  except InvalidOperation:
    return None
  return value if value.is_finite() else None

@dataclass(frozen=True)
class LayoutProfile:
  
  name: str
  rate_columns: int = 1                     
  alt_unit: str | None = None               
  integer_item_numbers: bool = True         
  min_chapter_letters: int = 6
  drop_running_lines: bool = True           
  running_line_share: float = 0.4

GENERIC = LayoutProfile("GENERIC")
GENERIC_TWO_RATES_METRIC = LayoutProfile("GENERIC_TWO_RATES_METRIC", rate_columns=2, alt_unit="m3")
PROFILES: dict[str, LayoutProfile] = {p.name: p for p in (GENERIC, GENERIC_TWO_RATES_METRIC)}

def get_profile(name: str | None) -> LayoutProfile:
  if not name:
    return GENERIC
  if name not in PROFILES:
    raise ValueError(f"unknown layout profile '{name}'")
  return PROFILES[name]

@dataclass
class RawRow:
  page: int | None
  line_no: int | None
  chapter: str | None
  item_no: str | None
  description: str
  unit_raw: str | None
  basis_qty: Decimal
  unit: str | None
  unit_known: bool
  rate_raw: str | None = None
  rate: Decimal | None = None
  rate_alt: Decimal | None = None
  raw_line: str | None = None
  flags: list = field(default_factory=list)

  @property
  def unit_rate(self) -> Decimal | None:
    return unit_rate_from(self.rate, self.basis_qty) if self.rate is not None else None

  def flag(self, code: str) -> None:
    if code not in self.flags:
      self.flags.append(code)

REVIEW_FLAGS = frozenset({"NO_ITEM_NO", "UNIT_UNKNOWN", "RATE_MISSING", "RATE_ZERO", "RATE_OUTLIER", "DUPLICATE_ITEM_NO",
  "SECOND_PASS_MISSING", "ALT_RATE_MISMATCH", "UNIT_AMBIGUOUS"})
INFO_FLAGS = frozenset({"WRAPPED_DESCRIPTION", "BASIS_APPLIED"})

FLAG_TEXT = {
  "NO_ITEM_NO": "The row has no item number in the document.",
  "UNIT_UNKNOWN": "The unit is not one the pricing engine can convert. Pick the unit before mapping.",
  "UNIT_AMBIGUOUS": "The unit is ambiguous (for example 'ton'). Pick the unit before mapping.",
  "RATE_MISSING": "No rate could be read.",
  "RATE_ZERO": "The rate reads as zero.",
  "RATE_OUTLIER": "The rate is far from the other rates with the same unit in this chapter. Check it against the page.",
  "DUPLICATE_ITEM_NO": "The same item number appears more than once with a different rate.",
  "SECOND_PASS_MISSING": "The rate was not found when the same page was read a second way. Check it against the page.",
  "ALT_RATE_MISMATCH": "The two rate columns disagree once converted to the same unit. One of them was misread.",
  "WRAPPED_DESCRIPTION": "The description ran over several lines and was joined.",
  "BASIS_APPLIED": "The rate is for a block of units (for example per 100 cft) and was divided down to one unit.",
}

_ITEM_DOTTED = re.compile(r"^(?P<no>\d{1,3}(?:[.\-/]\d{1,3}){1,4}[a-zA-Z]?)(?:\)|\.)?(?:\s+|$)(?P<rest>.*)$")
_ITEM_INT = re.compile(r"^(?P<no>\d{1,4}[a-zA-Z]?)(?:\)|\.)\s*(?P<rest>.*)$")
_ITEM_INT_SPACED = re.compile(r"^(?P<no>\d{1,4})(?:\s{2,}|\t)(?P<rest>\S.*)$")
_ITEM_SUB = re.compile(r"^(?P<no>\(?[a-zA-Z]{1,2}\)|\([ivxIVX]{1,5}\)|[ivx]{1,4}\))\s*(?P<rest>.*)$")
_ROW_END = re.compile(
  rf"^(?P<head>.*?)(?:(?<=\s)|^)(?P<unit>{_UNIT_PHRASE})\s+(?:rs\.?\s*)?(?P<rates>{_NUM}(?:\s+{_NUM}){{0,1}})\s*(?:/-|/=|-/)?\s*$", re.I)
_CHAPTER = re.compile(r"^(?:chapter|section|part|schedule)\b.*$", re.I)
_PAGE_NOISE = re.compile(r"^\s*(?:page\s*\d+(?:\s*of\s*\d+)?|\d+\s*/\s*\d+|-\s*\d+\s*-)\s*$", re.I)

def _clean_line(line: str) -> str:
  return re.sub(r"[ \t]+", " ", line.replace(" ", " ").strip())

def strip_running_lines(pages: list[list[str]], share: float = 0.4) -> list[list[str]]:
 
  if len(pages) < 5:
    return pages
  counts: Counter = Counter()
  for lines in pages:
    for text in {_clean_line(l) for l in lines if l.strip()}:
      counts[text] += 1
  limit = max(3, math.ceil(share * len(pages)))
  noisy = {t for t, n in counts.items() if n >= limit and not _ROW_END.match(t)}
  return [[l for l in lines if _clean_line(l) not in noisy and not _PAGE_NOISE.match(l)] for lines in pages]

def _split_item(line: str, profile: LayoutProfile, raw_line: str) -> tuple[str | None, str]:
  m = _ITEM_DOTTED.match(line)
  
  if m:
    return m.group("no"), m.group("rest").strip()

  if profile.integer_item_numbers:
    m = _ITEM_INT.match(line)
    
    if m:
      return m.group("no"), m.group("rest").strip()
    m = _ITEM_INT_SPACED.match(raw_line.strip())
    
    if m:
      return m.group("no"), re.sub(r"\s+", " ", m.group("rest")).strip()
  m = _ITEM_SUB.match(line)
  
  if m:
    return m.group("no"), m.group("rest").strip()
  return None, line

def _is_chapter(line: str, profile: LayoutProfile) -> bool:
  if _CHAPTER.match(line) and len(line) < 160:
    return True
  letters = re.sub(r"[^A-Za-z]", "", line)
  return len(letters) >= profile.min_chapter_letters and line.upper() == line and not re.search(r"\d{3,}", line) and len(line) < 120

def _row_from(match: re.Match, profile: LayoutProfile) -> tuple[str, str, list[str]]:
  rates = match.group("rates").split()
  return match.group("head").strip(), match.group("unit").strip(), rates

def parse_pages(pages: list[list[str]], profile: LayoutProfile = GENERIC) -> tuple[list[RawRow], list[dict]]:

  if profile.drop_running_lines:
    pages = strip_running_lines(pages, profile.running_line_share)
  rows: list[RawRow] = []
  unparsed: list[dict] = []
  state = {"chapter": None, "pending": None, "parent_no": None}

  def drop_pending() -> None:
    p = state["pending"]
    if p is not None:
      unparsed.append({"page": p["page"], "line": p["line"], "text": p["raw"][:200]})
      state["pending"] = None

  def close(item_no, description, unit_text, rates, page, line_no, raw, wrapped) -> None:
    ub = parse_unit_basis(unit_text)
    sub = item_no is not None and _ITEM_SUB.match(item_no + " ") is not None and not _ITEM_DOTTED.match(item_no + " ")
    
    if sub and state["parent_no"]:
      item_no = f"{state['parent_no']}{item_no if item_no.startswith('(') else '(' + item_no.rstrip(')') + ')'}"
    elif item_no is not None and not sub:
      state["parent_no"] = item_no
    use = list(rates)
    row = RawRow(page=page, line_no=line_no, chapter=state["chapter"], item_no=item_no, description=description.strip(),
      unit_raw=unit_text, basis_qty=ub.basis_qty, unit=ub.unit, unit_known=ub.known, raw_line=raw)
    if profile.rate_columns >= 2 and len(use) >= 2:
      row.rate_raw, row.rate, row.rate_alt = use[0], parse_rate(use[0]), parse_rate(use[1])
    else:
      if len(use) == 2:
       
        row.description = f"{row.description} {use[0]}".strip()
      row.rate_raw, row.rate = use[-1], parse_rate(use[-1])
    if item_no is None:
      row.flag("NO_ITEM_NO")
      
    if wrapped:
      row.flag("WRAPPED_DESCRIPTION")
    if ub.basis_qty != 1:
      row.flag("BASIS_APPLIED")
    if ub.unit is None or not ub.known:
      row.flag("UNIT_AMBIGUOUS" if ub.unit == "ton" else "UNIT_UNKNOWN")
    if row.rate is None:
      row.flag("RATE_MISSING")
    elif row.rate == 0:
      row.flag("RATE_ZERO")
    rows.append(row)

  for page_no, lines in enumerate(pages, start=1):
    for line_no, raw in enumerate(lines, start=1):
      line = _clean_line(raw)
      if not line or _PAGE_NOISE.match(line):
        continue
      item_no, rest = _split_item(line, profile, raw)
      end = _ROW_END.match(rest if item_no is not None else line)

      if end:
        head, unit_text, rates = _row_from(end, profile)
        pending = state["pending"]
        if pending is not None and item_no is None:
          close(pending["item"], f"{pending['desc']} {head}".strip(), unit_text, rates, pending["page"], pending["line"],
            f"{pending['raw']} | {line}", True)
          state["pending"] = None
        else:
          drop_pending()
          close(item_no, head, unit_text, rates, page_no, line_no, line, False)
        continue

      if item_no is not None:
        drop_pending()
        state["pending"] = {"item": item_no, "desc": rest, "page": page_no, "line": line_no, "raw": line}
        continue

      if state["pending"] is not None:
        state["pending"]["desc"] = f"{state['pending']['desc']} {line}".strip()
        state["pending"]["raw"] = f"{state['pending']['raw']} | {line}"
        continue

      if _is_chapter(line, profile):
        state["chapter"] = line[:200]
        continue
      if re.search(r"\d", line) and re.search(_NUM + r"\s*(?:/-)?$", line):
        unparsed.append({"page": page_no, "line": line_no, "text": line[:200]})
  drop_pending()
  return rows, unparsed

_CSV_ALIASES = {
  "item_no": ("item_no", "item no", "item", "ref", "sr", "sr no", "s.no", "sno", "specification no", "specification_no", "spec_no", "no"),
  "description": ("description", "desc", "particulars", "item description", "details"),
  "unit": ("unit", "uom"),
  "rate": ("rate", "rate_rs", "rate (rs)", "price", "amount"),
  "rate_alt": ("rate_alt", "rate_metric", "metric_rate", "alt_rate"),
  "chapter": ("chapter", "section", "group"),
  "page": ("page", "page_no"),
}

def parse_csv(content: bytes, profile: LayoutProfile = GENERIC) -> list[RawRow]:
  try:
    text = content.decode("utf-8-sig")
  except UnicodeDecodeError:
    raise ValueError("The file must be UTF-8 CSV.")
  reader = csv.DictReader(io.StringIO(text))
  if not reader.fieldnames:
    raise ValueError("The CSV is empty.")
  headers = {h.strip().lower(): h for h in reader.fieldnames if h}
  def col(name: str) -> str | None:
    for alias in _CSV_ALIASES[name]:
      if alias in headers:
        return headers[alias]
    return None
  need = [n for n in ("description", "unit", "rate") if col(n) is None]
  if need:
    raise ValueError(f"Missing column(s): {', '.join(need)}.")
  rows: list[RawRow] = []
  for n, raw in enumerate(reader, start=2):
    get = lambda name: ((raw.get(col(name)) or "").strip() if col(name) else "")
    if not any((v or "").strip() for v in raw.values() if v is not None):
      continue
  
    unit_text = get("unit")
    ub = parse_unit_basis(unit_text)
    rate_text = get("rate")
    row = RawRow(page=int(get("page")) if get("page").isdigit() else None, line_no=n, chapter=get("chapter") or None,
      item_no=get("item_no") or None, description=get("description"), unit_raw=unit_text or None, basis_qty=ub.basis_qty, unit=ub.unit,
      unit_known=ub.known, rate_raw=rate_text or None, rate=parse_rate(rate_text),
      rate_alt=parse_rate(get("rate_alt")) if get("rate_alt") else None, raw_line=None)
    
    if row.item_no is None:
      row.flag("NO_ITEM_NO")
    if ub.basis_qty != 1:
      row.flag("BASIS_APPLIED")
    if ub.unit is None or not ub.known:
      row.flag("UNIT_AMBIGUOUS" if ub.unit == "ton" else "UNIT_UNKNOWN")
    if row.rate is None:
      row.flag("RATE_MISSING")
    elif row.rate == 0:
      row.flag("RATE_ZERO")
    rows.append(row)
  return rows

MIN_SECOND_PASS_SHARE = Decimal("0.90")
MAX_UNKNOWN_UNIT_SHARE = Decimal("0.30")
MAX_UNPARSED_SHARE = Decimal("0.25")
MIN_PAGE_COVERAGE = Decimal("0.60")
OUTLIER_LOG10 = 1.5
OUTLIER_MIN_GROUP = 8
ALT_RATE_TOLERANCE = Decimal("0.015")

_TOKEN = re.compile(_NUM)

def number_tokens(lines: list[str]) -> set[str]:
  out: set[str] = set()
  for line in lines:
    for tok in _TOKEN.findall(line):
      try:
        out.add(format(Decimal(tok.replace(",", "")).normalize(), "f"))
      except InvalidOperation:
        continue
  return out

def _norm_num(value: Decimal | None) -> str | None:
  return None if value is None else format(value.normalize(), "f")

def apply_checks(rows: list[RawRow], unparsed: list[dict], *, page_count: int | None, second_pass_tokens: dict[int, set[str]] | None,
  content_hash: str, profile: LayoutProfile = GENERIC) -> dict:
  checks: list[dict] = []

  def check(code: str, label: str, status: str, detail: str, count: int | None = None) -> None:
    checks.append({"code": code, "label": label, "status": status, "detail": detail, "count": count})

  total = len(rows)
  if total == 0:
    check("ROWS_PARSED", "Rows read", "fail", "No rows could be read. The layout is probably not recognised; use the layout probe and add a profile.", 0)
    return _report(checks, rows, unparsed, page_count, content_hash, None)
  check("ROWS_PARSED", "Rows read", "pass", f"{total} rows read.", total)

  pages_with_rows = {r.page for r in rows if r.page is not None}
  empty_pages: list[int] = []
  coverage = None
  if page_count:
    empty_pages = [p for p in range(1, page_count + 1) if p not in pages_with_rows]
    coverage = Decimal(len(pages_with_rows)) / Decimal(page_count)
    status = "pass" if coverage >= Decimal("0.85") else "warn" if coverage >= MIN_PAGE_COVERAGE else "fail"
    check("PAGE_COVERAGE", "Pages that gave at least one row", status,
      f"{len(pages_with_rows)} of {page_count} pages. Pages with no rows: {', '.join(map(str, empty_pages[:40]))}{' ...' if len(empty_pages) > 40 else ''}"
      if empty_pages else f"All {page_count} pages gave rows.", len(empty_pages))

  share = Decimal(len(unparsed)) / Decimal(total)
  status = "pass" if share <= Decimal("0.02") else "warn" if share <= MAX_UNPARSED_SHARE else "fail"
  check("UNPARSED_LINES", "Lines that look like rows but were not read", status,
    f"{len(unparsed)} lines ({share:.1%} of rows read). They are listed so you can see what was skipped.", len(unparsed))

  bad_unit = [r for r in rows if "UNIT_UNKNOWN" in r.flags or "UNIT_AMBIGUOUS" in r.flags]
  unit_share = Decimal(len(bad_unit)) / Decimal(total)
  status = "pass" if not bad_unit else "warn" if unit_share <= MAX_UNKNOWN_UNIT_SHARE else "fail"
  by_unit = Counter((r.unit_raw or "?") for r in bad_unit)
  check("UNITS", "Units the pricing engine understands", status,
    "All units recognised." if not bad_unit else "Not usable for pricing: " + ", ".join(f"{u} ({n})" for u, n in by_unit.most_common(8)), len(bad_unit))

  missing = [r for r in rows if r.rate is None or r.rate == 0]
  check("RATES_PRESENT", "Every row has a positive rate", "pass" if not missing else "warn" if len(missing) / total < 0.05 else "fail",
    "All rows have a rate." if not missing else f"{len(missing)} rows have no usable rate.", len(missing))

  seen: dict = defaultdict(set)
  for r in rows:
    if r.item_no:
      seen[(r.chapter, r.item_no, r.unit)].add(_norm_num(r.unit_rate))
  dup_keys = {k for k, v in seen.items() if len(v) > 1}
  for r in rows:
    if r.item_no and (r.chapter, r.item_no, r.unit) in dup_keys:
      r.flag("DUPLICATE_ITEM_NO")
  check("DUPLICATE_ITEMS", "Same item number, different rate", "pass" if not dup_keys else "warn",
    "None." if not dup_keys else f"{len(dup_keys)} item numbers appear with more than one rate (often a page break repeated or a misread digit).", len(dup_keys))

  gaps = _numbering_gaps(rows)
  check("NUMBERING_GAPS", "Gaps in item numbering", "pass" if not gaps else "warn",
    "No gaps found." if not gaps else "Possible missed rows after: " + ", ".join(gaps[:20]) + (" ..." if len(gaps) > 20 else ""), len(gaps))

  groups: dict = defaultdict(list)
  for r in rows:
    if r.unit_rate and r.unit_rate > 0 and r.unit:
      groups[(r.chapter, r.unit)].append(r)
  outliers = 0
  for g in groups.values():
    if len(g) < OUTLIER_MIN_GROUP:
      continue
    center = median(math.log10(float(r.unit_rate)) for r in g)
    for r in g:
      if abs(math.log10(float(r.unit_rate)) - center) > OUTLIER_LOG10:
        r.flag("RATE_OUTLIER")
        outliers += 1
  check("OUTLIERS", "Rates far from their neighbours", "pass" if not outliers else "warn",
    "None." if not outliers else f"{outliers} rates are more than about 30 times away from the middle of their chapter and unit group.", outliers)

  if second_pass_tokens is not None:
    checked = missed = 0
    for r in rows:
      if r.page is None or r.rate is None or r.page not in second_pass_tokens:
        continue
      checked += 1
      if _norm_num(r.rate) not in second_pass_tokens[r.page]:
        r.flag("SECOND_PASS_MISSING")
        missed += 1
    agree = Decimal(checked - missed) / Decimal(checked) if checked else Decimal(1)
    check("SECOND_READ", "Rates found again when the page is read a second way", "pass" if agree >= Decimal("0.98") else "warn" if agree >= MIN_SECOND_PASS_SHARE else "fail",
      f"{checked - missed} of {checked} rates found again ({agree:.1%}).", missed)

  if profile.rate_columns >= 2 and profile.alt_unit:
    compared = bad = 0
    for r in rows:
      if r.rate is None or r.rate_alt is None or not r.unit:
        continue
      expected = logic.convert_rate(r.unit_rate, r.unit, profile.alt_unit)
      if expected is None or expected == 0:
        continue
      compared += 1
      alt_unit_rate = r.rate_alt / r.basis_qty
      if abs(alt_unit_rate - expected) / expected > ALT_RATE_TOLERANCE:
        r.flag("ALT_RATE_MISMATCH")
        bad += 1
    check("ALT_RATES", "British and metric rate columns agree", "pass" if bad == 0 else "warn" if compared and bad / compared < 0.05 else "fail",
      f"{compared - bad} of {compared} rows agree within {ALT_RATE_TOLERANCE:.1%}.", bad)

  return _report(checks, rows, unparsed, page_count, content_hash, coverage)

def _numbering_gaps(rows: list[RawRow]) -> list[str]:

  last: dict = {}
  gaps: list[str] = []
  for r in rows:
    m = re.fullmatch(r"(\d+(?:[.\-]\d+)*)[.\-](\d+)", r.item_no or "")
    if not m:
      continue
    prefix, num = m.group(1), int(m.group(2))
    key = (r.chapter, prefix)
    if key in last and num - last[key] > 1:
      gaps.append(f"{prefix}.{last[key]}")
    if key not in last or num > last[key]:
      last[key] = num
  return gaps

def _report(checks, rows, unparsed, page_count, content_hash, coverage) -> dict:
  statuses = {c["status"] for c in checks}
  status = "FAIL" if "fail" in statuses else "PASS_WITH_WARNINGS" if "warn" in statuses else "PASS"
  flagged = sum(1 for r in rows if any(f in REVIEW_FLAGS for f in r.flags))
  return {
    "status": status,
    "checks": checks,
    "counts": {"rows": len(rows), "flagged_for_review": flagged, "unparsed_lines": len(unparsed),
      "with_alt_rate": sum(1 for r in rows if r.rate_alt is not None), "pages": page_count},
    "page_coverage": None if coverage is None else float(round(coverage, 4)),
    "unparsed_sample": unparsed[:50],
    "content_hash": content_hash,
  }

def can_publish(report: dict | None) -> bool:
  return bool(report) and report.get("status") in ("PASS", "PASS_WITH_WARNINGS")

def spot_sample_indices(row_count: int, seed_hex: str, *, minimum: int = 15, share: float = 0.03, cap: int = 40) -> list[int]:
  
  if row_count <= 0:
    return []
  k = min(row_count, min(cap, max(minimum, math.ceil(row_count * share))))
  stride = row_count / k
  picks = []
  for n in range(k):
    digest = hashlib.sha256(f"{seed_hex}:{n}".encode()).digest()
    jitter = int.from_bytes(digest[:4], "big") / 2**32
    picks.append(min(row_count - 1, int((n + jitter) * stride)))
  return sorted(set(picks))

SUGGESTION_RULES: list[tuple[re.Pattern, str, str]] = [
  (re.compile(r"\b(p\.?c\.?c|plain cement concrete|plain concrete|lean concrete|blinding)\b", re.I), "CON-PCC", "m3"),
  (re.compile(r"\b(r\.?c\.?c|reinforced (cement )?concrete|structural concrete)\b", re.I), "CON-RCC", "m3"),
  (re.compile(r"\b(brick ?work|brick masonry|masonry in bricks|brick wall)\b", re.I), "MAS-BRICK", "m3"),
  (re.compile(r"\b(plaster|plastering)\b", re.I), "FIN-PLASTER", "m2"),
  (re.compile(r"\b(paint|painting|distemper|emulsion|weather ?shield)\b", re.I), "FIN-PAINT", "m2"),
  (re.compile(r"\b(tile|tiles|tiling|marble|terrazzo|mosaic|flooring)\b", re.I), "FIN-FLOOR", "m2"),
  (re.compile(r"\b(shuttering|formwork|form work|centering)\b", re.I), "FRM-STRUCT", "m2"),
  (re.compile(r"\b(excavation|excavating)\b", re.I), "EXC-FOUND", "m3"),
  (re.compile(r"\b(steel reinforcement|reinforcement|reinforcing steel|deformed bars?|m\.?s\.? bars?)\b", re.I), "STL-REBAR", "kg"),
  (re.compile(r"\b(structural steel|steel sections?|rolled steel|fabricat\w+ steel|steel work)\b", re.I), "STL-STRUCT", "kg"),
  (re.compile(r"\b(steel pil\w+)\b", re.I), "STL-PILE", "m"),
  (re.compile(r"\b(door|doors)\b", re.I), "DOR-NOS", "nos"),
  (re.compile(r"\b(window|windows)\b", re.I), "WIN-NOS", "nos"),
]

def suggest_work_item(description: str | None, unit: str | None) -> tuple[str, str] | None:
    
  if not description or not unit or unit not in logic.UNIT_TABLE:
    return None
  family = logic.UNIT_TABLE[unit][0]
  for pattern, code, wanted in SUGGESTION_RULES:
    m = pattern.search(description)
    if m and family == wanted:
      return code, f"description mentions '{m.group(0)}'"
  return None

@dataclass(frozen=True)
class PublishPlan:
  items: list         
  conflicts: list    
  problems: list      

def plan_publish(mapped_rows: list[dict]) -> PublishPlan:

  by_key: dict = defaultdict(list)
  problems: list = []
  for r in mapped_rows:
    if not r.get("unit") or r["unit"] not in logic.UNIT_TABLE:
      problems.append({"row_id": r["id"], "reason": "unit is not one the pricing engine converts"})
      continue
  
    rate = r.get("unit_rate")
    if rate is None or Decimal(rate) <= 0:
      problems.append({"row_id": r["id"], "reason": "no positive rate"})
      continue
  
    if logic.q2(Decimal(rate)) <= 0:
      problems.append({"row_id": r["id"], "reason": "rate rounds to zero at 2 decimals; use a larger unit"})
      continue
    by_key[(r["work_item_code"], r["unit"])].append(r)
  conflicts = [{"work_item_code": k[0], "unit": k[1], "rows": [x["id"] for x in v], "item_nos": [x.get("item_no") for x in v]}
    for k, v in by_key.items() if len(v) > 1]
  items = [v[0] for k, v in by_key.items() if len(v) == 1]
  return PublishPlan(items, conflicts, problems)

def book_code(province: str | None, district: str | None) -> str:
  def slug(value: str | None, n: int) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", (value or "").upper()).strip("-")[:n] or "NA"
  prov = {"PUNJAB": "PB", "SINDH": "SD", "KHYBER PAKHTUNKHWA": "KP", "KPK": "KP", "BALOCHISTAN": "BL"}.get((province or "").upper(), slug(province, 4))
  return f"MRS-{prov}-{slug(district, 30)}"[:50]
