from __future__ import annotations
from decimal import Decimal
from app.modules.drawings_boq.pricing import mrs_parse as mp
from app.modules.drawings_boq.pricing.mrs_spec import compose_code
from typing import Iterable
import re
from dataclasses import dataclass, field
from app.modules.drawings_boq import boq_logic as logic
from collections import defaultdict
from statistics import median

ZERO = Decimal("0")
ONE = Decimal("1")
REVIEW_FLAGS = mp.REVIEW_FLAGS
STRUCTURAL_CHECKS = frozenset({"ROWS_PARSED", "PAGE_COVERAGE", "UNPARSED_LINES", "SECOND_READ", "NO_TEXT_PAGES"})
_UNIT_FLAGS = frozenset({"UNIT_UNKNOWN", "UNIT_AMBIGUOUS"})
_RATE_FLAGS = frozenset({"RATE_MISSING", "RATE_ZERO", "RATE_OUTLIER", "SECOND_PASS_MISSING", "ALT_RATE_MISMATCH"})
_MAX_PRECISION_LOSS = Decimal("0.005")

def derive_flags(flags: Iterable[str], *, unit: str | None, unit_known: bool, rate: Decimal | None, edited_unit: bool, edited_rate: bool) -> list[str]:
  """The flags a row has after an edit. Editing the unit re-derives the unit flags; editing the rate re-derives the rate flags
  (a rate a person typed no longer 'disagrees with the second read'); every other flag stays until the person confirms the row."""
  out = [f for f in flags if not (edited_unit and f in _UNIT_FLAGS) and not (edited_rate and f in _RATE_FLAGS)]
  if edited_unit and (unit is None or not unit_known):
    out.append("UNIT_AMBIGUOUS" if unit == "ton" else "UNIT_UNKNOWN")
  if edited_rate:
    if rate is None:
      out.append("RATE_MISSING")
    elif rate == 0:
      out.append("RATE_ZERO")
  seen: list[str] = []
  for f in out:
    if f not in seen:
      seen.append(f)
  return seen

def needs_review(flags: Iterable[str], *, reviewed: bool, skipped: bool) -> bool:
  return (not skipped) and (not reviewed) and any(f in REVIEW_FLAGS for f in flags)

def unit_rate_of(rate: Decimal | None, basis_qty: Decimal) -> Decimal | None:
  if rate is None:
    return None
  return mp.unit_rate_from(Decimal(rate), Decimal(basis_qty))

def resolve_unit(text: str | None) -> tuple[str | None, bool, str | None]:
  """(canonical unit, convertible by the pricing engine, problem). Accepts 'cft', 'Cu.ft', 'sq.m', 'nos' and so on."""
  ub = mp.parse_unit_basis(text)
  if ub.unit is None:
    return None, False, ub.note or "unit not recognised"
  return ub.unit, ub.known, ub.note

_STOP = frozenset("""a an and or of the in on at to for with by from as is are be per all any each including includes inclusive complete finished
including etc than not above below up upto size sizes type kind work works item items rate rates cost labour material materials supply providing provide
laying fixing fix making prepared preparation using used use only other such""".split())
_SPEC = re.compile(r"\b\d+(?:\.\d+)?(?::\d+(?:\.\d+)?)+\b|#\s?\d+\b|\b\d+(?:\.\d+)?\s?(?:mm|cm|inch|inches|in|ft|feet|m|\"|')(?=\W|$)|\b\d+(?:\.\d+)?\s?x\s?\d+(?:\.\d+)?\b", re.I)

def spec_tokens(text: str | None) -> frozenset[str]:
  """The numbers that decide what an item is: mix ratios (1:2:4), thicknesses and sizes (4.5 inch, 12 mm, 9x4.5), bar numbers (#4)."""
  found = set()
  for m in _SPEC.finditer((text or "").lower()):
    token = re.sub(r"\s+", "", m.group(0)).replace("inches", "in").replace("inch", "in").replace("feet", "ft")
    found.add(token)
  return frozenset(found)

def words(text: str | None) -> frozenset[str]:
  out = set()
  for w in re.findall(r"[a-z]+", (text or "").lower()):
    if len(w) > 2 and w not in _STOP:
      out.add(w[:-1] if w.endswith("s") and len(w) > 4 else w)
  return frozenset(out)

def spec_conflict(a: frozenset[str], b: frozenset[str]) -> bool:
  return bool(a) and bool(b) and not (a & b)

def _family(unit: str | None) -> str | None:
  entry = logic.UNIT_TABLE.get(logic.normalise_unit(unit)) if unit else None
  return entry[0] if entry else None

def _norm_ref(value: str | None) -> str:
  return re.sub(r"[^a-z0-9]", "", (value or "").lower())

@dataclass(frozen=True)
class CatalogEntry:
  code: str
  description: str
  unit: str
  csr_ref: str | None = None
  trade: str | None = None

def suggest(description: str | None, unit: str | None, item_no: str | None, catalog: list[CatalogEntry], *, limit: int = 3, floor: float = 0.4) -> list[dict]:
  fam = _family(unit)
  if fam is None:
    return []

  row_words, row_spec = words(description), spec_tokens(description)
  ref = _norm_ref(item_no)
  ranked: list[tuple[float, dict]] = []
  keyword = mp.suggest_work_item(description, unit)
  keyword_code = keyword[0] if keyword else None
  
  for entry in catalog:
    if _family(entry.unit) != fam:
      continue
    if ref and entry.csr_ref and _norm_ref(entry.csr_ref) == ref:
      score, reason = 0.97, "same reference number"
    else:
      w = words(entry.description) or words(entry.trade)
      if not w or not row_words:
        continue
      inter = len(row_words & w)
      if inter == 0:
        continue
    
      contain = inter / len(w)
      jacc = inter / len(row_words | w)
      score, reason = 0.6 * contain + 0.4 * jacc, f"{inter} words in common"
      if keyword_code and entry.code == keyword_code:
        score, reason = max(score, 0.85), "keyword rule"
    conflict = spec_conflict(row_spec, spec_tokens(entry.description))
    if conflict:
      score = min(score, 0.5)
      reason += "; sizes or mix differ"
    if score >= floor:
      ranked.append((score, {"code": entry.code, "description": entry.description[:200], "unit": entry.unit, "score": round(score, 2),
        "reason": reason, "spec_conflict": conflict}))
  ranked.sort(key=lambda x: (-x[0], x[1]["code"]))
  return [r[1] for r in ranked[:limit]]

def confident(suggestions: list[dict], *, threshold: float) -> dict | None:
  if not suggestions:
    return None
  top = suggestions[0]
  if top["spec_conflict"] or top["score"] < threshold:
    return None
  if len(suggestions) > 1 and top["score"] - suggestions[1]["score"] < 0.1:
    return None
  return top

@dataclass
class Readiness:
  can_publish: bool
  blockers: list[dict] = field(default_factory=list)
  warnings: list[dict] = field(default_factory=list)
  counts: dict = field(default_factory=dict)

def readiness(*, status: str, report: dict | None, rows: list[dict], include_unmapped: bool) -> Readiness:
  blockers: list[dict] = []
  warnings: list[dict] = []
  
  live = [r for r in rows if not r["skipped"]]
  unresolved = [r for r in live if r["needs_review"]]
  unverified = [r for r in rows if r["is_sample"] and not r["sample_verified"]]
  mapped = [r for r in live if r["work_item_code"]]
  unmapped = [r for r in live if not r["work_item_code"]]
  counts = {"rows": len(rows), "skipped": len(rows) - len(live), "to_review": len(unresolved), "samples_unverified": len(unverified),
    "mapped": len(mapped), "unmapped": len(unmapped)}
  
  if status != "REVIEW":
    blockers.append({"code": "NOT_IN_REVIEW", "message": f"The import is {status}; only an import in REVIEW can be published."})
  else:
    broken = [c for c in (report or {}).get("checks", []) if c["status"] == "fail" and c["code"] in STRUCTURAL_CHECKS]
    if report is None or broken:
      names = ", ".join(c["label"] for c in broken) or "the file was not checked"
      blockers.append({"code": "CHECKS_FAILED", "message": f"The file was not read reliably ({names}). Fix the file or choose another layout, then read it again."})
    for c in (report or {}).get("checks", []):
      if c["status"] == "fail" and c["code"] not in STRUCTURAL_CHECKS:
        warnings.append({"code": "CHECK_" + c["code"], "message": f'{c["label"]}: {c["detail"]} Each such row is reviewed or skipped below.', "count": c.get("count")})
        
  if unresolved:
    blockers.append({"code": "ROWS_NEED_REVIEW", "message": f"{len(unresolved)} row(s) are flagged and not yet confirmed or skipped.", "count": len(unresolved)})
  if unverified:
    blockers.append({"code": "SAMPLE_UNVERIFIED", "message": f"{len(unverified)} spot-check row(s) have not been checked against the page.", "count": len(unverified)})
  pool = live if include_unmapped else mapped
  if not pool and status == "REVIEW":
    blockers.append({"code": "NOTHING_TO_PUBLISH", "message": "No rows would be published. Map rows to work items or include unmapped rows."})
  keyed = _keyed(pool, include_unmapped)
  plan = mp.plan_publish(keyed)
  if plan.conflicts:
    blockers.append({"code": "CONFLICTS", "message": f"{len(plan.conflicts)} work item(s) have more than one row in the same unit. Skip or remap all but one.",
      "conflicts": plan.conflicts[:50], "count": len(plan.conflicts)})
  if plan.problems:
    blockers.append({"code": "ROW_PROBLEMS", "message": f"{len(plan.problems)} row(s) cannot be published (unit or rate).", "problems": plan.problems[:50], "count": len(plan.problems)})
  if unmapped and not include_unmapped:
    warnings.append({"code": "UNMAPPED_LEFT_OUT", "message": f"{len(unmapped)} row(s) are not mapped to a work item and will be left out.", "count": len(unmapped)})
  return Readiness(not blockers, blockers, warnings, counts)

def derived_code(prefix: str, item_no: str | None, seq: int) -> str:
  base = re.sub(r"[^A-Za-z0-9.\-()]+", "", item_no or "") or f"R{seq}"
  return f"{prefix}-{base}"[:50]

def _keyed(rows: list[dict], include_unmapped: bool, prefix: str = "SRC") -> list[dict]:
  out = []
  for r in rows:
    code = r["work_item_code"] or (derived_code(prefix, r.get("item_no"), r["seq"]) if include_unmapped else None)
    if code:
      out.append({**r, "work_item_code": code, "code_derived": not r["work_item_code"]})
  return out

def publishable_items(rows: list[dict], *, include_unmapped: bool, prefix: str) -> tuple[list[dict], list[dict]]:
  
  items, notes = [], []
  for r in _keyed([x for x in rows if not x["skipped"]], include_unmapped, prefix):
    unit, rate = r["unit"], Decimal(r["unit_rate"])
    loss = abs(logic.q2(rate) - rate) / rate if rate > 0 else ZERO
    if loss > _MAX_PRECISION_LOSS:
      fam = _family(unit)
      big = {"m3": "m3", "m2": "m2", "m": "m"}.get(fam or "")
      
      if big and big != unit:
        converted = logic.convert_rate(rate, unit, big)
        exact = rate * logic.UNIT_TABLE[unit][1] / logic.UNIT_TABLE[big][1]
        if converted is not None and abs(converted - exact) / exact <= _MAX_PRECISION_LOSS:
          notes.append({"row_id": r["id"], "item_no": r.get("item_no"), "from_unit": unit, "to_unit": big})
          unit, rate = big, exact
    base = r["work_item_code"]
    spec = None if r.get("code_derived") else (r.get("spec_key") or None)         # a code made from the item number is already one row's own
    items.append({**r, "unit": unit, "unit_rate": rate, "base_code": base, "code_spec": spec, "work_item_code": compose_code(base, spec)})
  return items, notes

def spec_notes(items: list[dict]) -> list[dict]:
  with_spec = {it["base_code"] for it in items if it.get("code_spec")}
  plain = {it["base_code"] for it in items if not it.get("code_spec")}
  return [{"work_item_code": code, "message": f"{code} is published only with a specification (mix, member or strength). A quantity that does not state its specification will find no rate for it."}
    for code in sorted(with_spec - plain)]

def _key(item: dict, match_on: str) -> tuple | None:
  if match_on == "csr_ref":
    ref = _norm_ref(item.get("csr_ref"))
    return (ref,) if ref else None
  return (item["work_item_code"], logic.normalise_unit(item["unit"]))

def _pct(old: Decimal, new: Decimal) -> Decimal | None:
  return None if old == 0 else ((new - old) / old * 100).quantize(Decimal("0.01"))

def compare_books(items_a: list[dict], items_b: list[dict], *, match_on: str = "code") -> dict:
  a_by, b_by = {}, {}
  for it in items_a:
    k = _key(it, match_on)
    if k is not None:
      a_by.setdefault(k, it)
  for it in items_b:
    k = _key(it, match_on)
    if k is not None:
      b_by.setdefault(k, it)
  if match_on == "code":
    a_left = {k: v for k, v in a_by.items() if k not in b_by}
    taken: set = set()
    
    for kb in [k for k in b_by if k not in a_by]:
      fam = _family(b_by[kb]["unit"])
      for ka, a_item in a_left.items():
        if ka not in taken and ka[0] == kb[0] and fam is not None and _family(a_item["unit"]) == fam:
          b_by[ka] = b_by.pop(kb)
          taken.add(ka)
          break
      
  lines, changed_pcts = [], []
  by_trade: dict[str, list[Decimal]] = defaultdict(list)
  counts = {"added": 0, "removed": 0, "changed": 0, "unchanged": 0, "unit_mismatch": 0}
  for k in sorted(set(a_by) | set(b_by), key=lambda t: tuple(str(x) for x in t)):
    a, b = a_by.get(k), b_by.get(k)
    ref = b or a
    base = {"work_item_code": ref["work_item_code"], "description": ref.get("description"), "trade": ref.get("trade"), "csr_ref": ref.get("csr_ref")}
    if a is None:
      counts["added"] += 1
      lines.append({**base, "status": "ADDED", "unit": b["unit"], "rate_a": None, "rate_b": str(b["rate"]), "delta": None, "pct": None})
      continue
    if b is None:
      counts["removed"] += 1
      lines.append({**base, "status": "REMOVED", "unit": a["unit"], "rate_a": str(a["rate"]), "rate_b": None, "delta": None, "pct": None})
      continue
  
    old = Decimal(a["rate"])
    if logic.normalise_unit(a["unit"]) != logic.normalise_unit(b["unit"]):
      conv = logic.convert_rate(old, a["unit"], b["unit"])
      if conv is None:
        counts["unit_mismatch"] += 1
        lines.append({**base, "status": "UNIT_MISMATCH", "unit": f'{a["unit"]} → {b["unit"]}', "rate_a": str(a["rate"]), "rate_b": str(b["rate"]), "delta": None, "pct": None})
        continue
      old = conv
    new = Decimal(b["rate"])
    if old == new:
      counts["unchanged"] += 1
      continue
  
    counts["changed"] += 1
    pct = _pct(old, new)
    if pct is not None:
      changed_pcts.append(pct)
      if old > 0:
        by_trade[(ref.get("trade") or "").strip() or "—"].append(new / old)
        
    lines.append({**base, "status": "CHANGED", "unit": b["unit"], "rate_a": str(old), "rate_b": str(new), "delta": str(new - old), "pct": str(pct) if pct is not None else None})
  all_ratios = [r for rs in by_trade.values() for r in rs]
  factors = [{"trade": t, "matched": len(rs), "median_ratio": str(Decimal(str(median(rs))).quantize(Decimal("0.0001")))}
    for t, rs in sorted(by_trade.items()) if len(rs) >= 5]
  matched = counts["changed"] + counts["unchanged"]
  return {"counts": counts, "matched": matched,
    "median_change_pct": str(Decimal(str(median(changed_pcts))).quantize(Decimal("0.01"))) if changed_pcts else None,
    "overall_ratio": str(Decimal(str(median(all_ratios))).quantize(Decimal("0.0001"))) if all_ratios else None,
    "suggested_factors": factors, "lines": lines}

def history_series(entries: list[dict]) -> list[dict]:
  ordered = sorted(entries, key=lambda e: (e["effective_from"] or "", e["version"]))
  out, prev = [], None
  
  for e in ordered:
    rate = Decimal(e["rate"])
    pct = None
    if prev is not None:
      before = logic.convert_rate(Decimal(prev["rate"]), prev["unit"], e["unit"]) if logic.normalise_unit(prev["unit"]) != logic.normalise_unit(e["unit"]) else Decimal(prev["rate"])
      pct = _pct(before, rate) if before is not None else None
    out.append({**e, "rate": str(rate), "pct_from_previous": str(pct) if pct is not None else None})
    prev = e
  return out

def plan_refresh(target_items: list[dict], source_items: list[dict], *, match_on: str = "csr_ref", only_trades: set[str] | None = None) -> dict:
  """What would change if the rates of a draft book were taken from `source_items`. Items that are the result of a rate analysis are not touched
  here (they are recomputed from their ingredients). Returns the changes and the reasons nothing changed for the rest."""
  src = {}
  for it in source_items:
    k = _key(it, match_on)
    if k is not None:
      src.setdefault(k, it)
  src_family: dict = {}
  if match_on == "code":
    for it in source_items:
      fam = _family(it["unit"])
      if fam is not None:
        src_family.setdefault((it["work_item_code"], fam), it)
        
  changes, unchanged, unmatched, skipped = [], 0, [], []
  for it in target_items:
    if it.get("analysis_id"):
      skipped.append({"id": it["id"], "work_item_code": it["work_item_code"], "reason": "ANALYSIS"})
      continue
    if only_trades is not None and (it.get("trade") or "") not in only_trades:
      continue
    k = _key(it, match_on)
    other = src.get(k) if k is not None else None
    if other is None and match_on == "code" and _family(it["unit"]) is not None:
      other = src_family.get((it["work_item_code"], _family(it["unit"])))
    if other is None:
      unmatched.append({"id": it["id"], "work_item_code": it["work_item_code"], "unit": it["unit"], "csr_ref": it.get("csr_ref")})
      continue
  
    new = Decimal(other["rate"])
    if logic.normalise_unit(other["unit"]) != logic.normalise_unit(it["unit"]):
      conv = logic.convert_rate(new, other["unit"], it["unit"])
      if conv is None:
        skipped.append({"id": it["id"], "work_item_code": it["work_item_code"], "reason": "UNIT_MISMATCH"})
        continue
    
      new = conv
    old = Decimal(it["rate"])
    if new == old:
      unchanged += 1
      continue
    changes.append({"id": it["id"], "work_item_code": it["work_item_code"], "unit": it["unit"], "old": str(old), "new": str(new),
      "pct": str(_pct(old, new)) if _pct(old, new) is not None else None})
  return {"changes": changes, "unchanged": unchanged, "unmatched": unmatched, "skipped": skipped}
