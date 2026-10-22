from __future__ import annotations
from collections import defaultdict, Counter
import re
from app.modules.drawings_boq.pricing import mrs_parse as mp
from decimal import Decimal
from statistics import median
from app.modules.drawings_boq.pricing import mrs_cells, mrs_spec, mrs_table, mrs_units

CHAPTER_CHARS = 200
ITEM_NO_CHARS = 60

def chapter_names(rows: list[mrs_table.TableRow]) -> dict:
  votes: dict = defaultdict(Counter)
  for r in rows:
    if r.chapter_no is not None and r.chapter:
      votes[r.chapter_no][r.chapter.strip()] += 1
  return {no: c.most_common(1)[0][0] for no, c in votes.items()}

def _chapter_label(row: mrs_table.TableRow, names: dict) -> str | None:
  if row.chapter_no is None:
    return None
  return f"{row.chapter_no} {names.get(row.chapter_no, '')}".strip()[:CHAPTER_CHARS]

def _norm(text: str) -> str:
  return re.sub(r"[^a-z0-9]+", "", text.lower())

def raw_rows(rows: list[mrs_table.TableRow]) -> list[mp.RawRow]:
  seen: Counter = Counter()
  out: list[mp.RawRow] = []
  per_page: Counter = Counter()
  groups = Counter((r.chapter_no, r.code) for r in rows)
  names = chapter_names(rows)
  
  for r in rows:
    per_page[r.page] += 1
    seen[(r.chapter_no, r.code)] += 1
    n = seen[(r.chapter_no, r.code)]
    base_no = f"{r.chapter_no if r.chapter_no is not None else 0}-{r.code}"
    item_no = (base_no if n == 1 else f"{base_no}-n{n}")[:ITEM_NO_CHARS]
    british = r.unit_b is not None and (r.comp_b is not None or r.labour_b is not None)
    
    if british:
      unit_text, labour, comp, alt_comp, alt_labour = r.unit_b, r.labour_b, r.comp_b, r.comp_m, r.labour_m
    else:
      unit_text, labour, comp, alt_comp, alt_labour = (r.unit_m or r.unit_b), r.labour_m, r.comp_m, None, None
    rate, kind, alt = None, None, None
    if comp is not None:
      rate, kind, alt = comp, "COMPOSITE", alt_comp
    elif labour is not None:
      rate, kind, alt = labour, "LABOUR", alt_labour
    ub = mp.parse_unit_basis(mrs_units.unit_core(unit_text))
    
    raw = mp.RawRow(page=r.page, line_no=per_page[r.page], chapter=_chapter_label(r, names), item_no=item_no, description=r.description,
      unit_raw=unit_text, basis_qty=ub.basis_qty, unit=ub.unit, unit_known=ub.known, rate_raw=None if rate is None else format(rate, "f"),
      rate=rate, rate_alt=alt, raw_line=_side_note(r), flags=list(r.flags), spec_key=mrs_spec.spec_key(r.path, r.leaf), labour=labour, rate_kind=kind)
    raw.alt_unit_raw = r.unit_m if british else None       
         
    raw.alt_labour = alt_labour
    if groups[(r.chapter_no, r.code)] > 1:
      raw.flag("DUPLICATE_CODE")
    if ub.basis_qty != 1:
      raw.flag("BASIS_APPLIED")
    if ub.unit is None or not ub.known:
      raw.flag("UNIT_AMBIGUOUS" if ub.unit == "ton" else "UNIT_UNKNOWN")
    if rate is None:
      raw.flag("RATE_MISSING")
    elif rate == 0:
      raw.flag("RATE_ZERO")
    if kind == "LABOUR":
      raw.flag("RATE_LABOUR_ONLY")
    out.append(raw)
  return out

def _side_note(r: mrs_table.TableRow) -> str | None:
  bits = []
  if r.spec_no:
    bits.append(f"spec {r.spec_no}")
  if r.remarks:
    bits.append(f"remarks: {r.remarks}")
  return (" | ".join(bits))[:1000] or None

def compare_systems(rows: list[mp.RawRow]) -> tuple[int, int, int]:
  compared = bad = skipped = 0
  for r in rows:
    if r.rate is None or r.rate_alt is None or r.rate_kind != "COMPOSITE":
      continue
           
    unit_b, unit_m = r.unit_raw, getattr(r, "alt_unit_raw", None)
    verdict = mrs_units.agree(r.rate, unit_b, r.rate_alt, unit_m)
    if verdict is False and r.rate == r.rate_alt and mrs_units.agree(r.rate, unit_b, r.rate_alt, unit_m, tolerance=0.03):
      verdict = True        
    if verdict is None:
      skipped += 1
      r.flag("UNITS_NOT_COMPARED")
      continue
    compared += 1
    if not verdict:
      bad += 1
      r.flag("ALT_RATE_MISMATCH")
  return compared, bad, skipped

def report_for(rows: list[mp.RawRow], infos: list, *, page_count: int, digest: str, first_page: int) -> dict:
  report = mp.apply_checks(rows, [], page_count=len(infos), second_pass_tokens=None, content_hash=digest, profile=mp.GENERIC)
  compared, bad, skipped = compare_systems(rows)
  report["checks"] = [c for c in report["checks"] if c["code"] != "PAGE_COVERAGE"]
  rate_pages = [i for i in infos if i.table]
  with_rows = [i for i in rate_pages if i.rows]
  empty = [i.number for i in rate_pages if not i.rows]
  report["checks"].append({"code": "PAGE_COVERAGE", "label": "Rate pages that gave at least one row", "count": len(empty),
    "status": "pass" if not empty else "warn" if len(empty) <= max(2, len(rate_pages) // 20) else "fail",
    "detail": f"{len(with_rows)} of {len(rate_pages)} rate pages gave rows." + (f" No rows from page(s): {', '.join(map(str, empty[:30]))}." if empty else "")})
  
  share = compared and Decimal(bad) / Decimal(compared)
  report["checks"].append({"code": "ALT_RATES", "label": "British and metric rates agree", "count": bad,
    "status": "pass" if bad == 0 else "warn" if compared and share < Decimal("0.05") else "fail",
    "detail": f"{compared - bad} of {compared} rows agree within 1.2% after unit conversion; {bad} do not (misprints in the list, or a misread figure). {skipped} rows have units that cannot be converted into each other."})
  norms = [i.number for i in infos if i.norms]
  if norms:
    report["checks"].append({"code": "NORM_PAGES", "label": "Pages of material coefficients (not rates)", "status": "pass", "count": len(norms),
      "detail": "Left out because they list quantities of materials, not prices: page " + ", ".join(map(str, norms)) + "."})
    
  labour_only = sum(1 for r in rows if "RATE_LABOUR_ONLY" in r.flags)
  report["checks"].append({"code": "LABOUR_ONLY", "label": "Rows with a labour rate only", "status": "pass" if not labour_only else "warn", "count": labour_only,
    "detail": "Every row has a composite rate." if not labour_only else f"{labour_only} rows print a labour rate and no composite (carriage, dismantling, extra labour). They are held for review and are not full prices."})
  statuses = {c["status"] for c in report["checks"]}
  
  report["status"] = "FAIL" if "fail" in statuses else "PASS_WITH_WARNINGS" if "warn" in statuses else "PASS"
  report["counts"]["flagged_for_review"] = sum(1 for r in rows if any(f in mp.REVIEW_FLAGS for f in r.flags))
  report["counts"]["with_alt_rate"] = sum(1 for r in rows if r.rate_alt is not None)
  report["page_range"] = [first_page, first_page + len(infos) - 1 if infos else first_page]
  return report

def read_table(data: bytes, first_page: int, last_page: int | None, digest: str) -> dict:
  pages, total = mrs_cells.read_pdf_cells(data, first_page=first_page, last_page=last_page)
  table_rows, infos, _notes = mrs_table.read_tables(pages)
  rows = raw_rows(table_rows)
  report = report_for(rows, infos, page_count=total, digest=digest, first_page=first_page)
  if not pages or all(not p.cells for p in pages):
    report["checks"].append({"code": "NO_TEXT_PAGES", "label": "Pages with no readable text", "status": "fail", "count": len(pages),
      "detail": "The pages have no text layer. A scanned list cannot be read here."})
    report["status"] = "FAIL"
  return {"rows": rows, "report": report, "page_count": total, "offset": 0, "infos": infos}

def _keyed(rows: list[mp.RawRow]) -> dict:
  seen: Counter = Counter()
  out = {}
  for r in rows:
    base = (r.chapter or "", _norm(r.description))
    seen[base] += 1
    out[base + (seen[base],)] = r
  return out

def edition_changes(old: list[mp.RawRow], new: list[mp.RawRow]) -> dict:
  a, b = _keyed(old), _keyed(new)
  common = set(a) & set(b)
  by_chapter: dict = defaultdict(list)
  lines = []
  
  for k in sorted(common, key=lambda t: (t[0], t[1], t[2])):
    ra, rb = a[k], b[k]
    if ra.rate is None or rb.rate is None or ra.rate <= 0 or ra.rate_kind != rb.rate_kind:
      continue
    if mrs_units.measure_of(ra.unit_raw) != mrs_units.measure_of(rb.unit_raw):
      continue
    pct = (rb.rate - ra.rate) / ra.rate * 100
    by_chapter[k[0]].append(pct)
    if pct != 0:
      lines.append({"chapter": k[0], "item_no": rb.item_no, "description": rb.description[:200], "unit": rb.unit_raw, "old": str(ra.rate), "new": str(rb.rate), "pct": f"{pct:.2f}"})
      
  chapters = []
  for ch, v in sorted(by_chapter.items(), key=lambda kv: (int(kv[0].split()[0]) if kv[0].split()[:1] and kv[0].split()[0].isdigit() else 999, kv[0])):
    changed = [x for x in v if x != 0]
    chapters.append({"chapter": ch, "matched": len(v), "changed": len(changed), "unchanged_share": f"{(1 - len(changed) / len(v)) * 100:.1f}",
      "median_pct_all": f"{float(median(v)):.2f}", "median_pct_changed": f"{float(median(changed)):.2f}" if changed else None,
      "min_pct": f"{float(min(v)):.2f}", "max_pct": f"{float(max(v)):.2f}"})
  return {"matched": len(common), "only_old": len(set(a) - set(b)), "only_new": len(set(b) - set(a)), "chapters": chapters, "lines": lines}
