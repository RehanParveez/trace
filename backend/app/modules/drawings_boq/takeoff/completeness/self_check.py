from __future__ import annotations
import re
from app.engine.catalogue import loader as CAT
from app.engine.catalogue import self_checks as SCK

PASS, FAIL, NOT_CHECKABLE = "PASS", "FAIL", "NOT_CHECKABLE"
RESULTS = (PASS, FAIL, NOT_CHECKABLE)
SHOW = 5
_PAREN = re.compile(r"\([^)]*\)")
_SPACE = re.compile(r"\s+")
_JOIN = re.compile(r"[-_.]")

def norm_mark(mark, strip: tuple = ()) -> str | None:
  m = _SPACE.sub("", _PAREN.sub("", str(mark or ""))).upper()
  for p in strip:
    p = _SPACE.sub("", p).upper()
    if p and m.startswith(p) and len(m) > len(p):
      m = m[len(p):]
      break
  if not m or SCK.placeholder().match(m):
    return None
  return _JOIN.sub("", m) or None

def _rows(evidence: dict, side: dict) -> list:
  classes, roles = set(side.get("classes") or []), set(side.get("roles") or [])
  return [r for r in evidence.get("observed") or [] if r["cls"] in classes and (not roles or r.get("role") in roles)]

def _by_mark(rows: list, strip: tuple = ()) -> dict:
  out: dict = {}
  for r in rows:
    m = norm_mark(r.get("mark"), strip)
    if m:
      out.setdefault(m, []).append(r)
  return out

def _ids(rows: list) -> list:
  return [r["id"] for r in rows]

def _list(names: list) -> str:
  shown = sorted(names)[:SHOW]
  return ", ".join(shown) + (f" and {len(names) - SHOW} more" if len(names) > SHOW else "")

def _result(c: dict, result: str, detail: str, items: list | None = None, agreed: list | None = None, **more) -> dict:
  return {"check": c["id"], "result": result, "items": sorted(set(items or [])), "agreed": sorted(set(agreed or [])), "detail": detail, **more}

def _say(c: dict, which: str, **kw) -> str:
  return c["say"][which].format(**kw)

def _needs(c: dict, evidence: dict) -> str | None:
  have = {r["cls"] for r in evidence.get("observed") or []}
  fams = {ln["family"] for ln in evidence.get("lines") or []}
  for n in c["needs"]:
    if n == "bbs":
      if evidence.get("bbs_kg") is None:
        return "no bar bending schedule total was read"
    elif n.startswith("lines:"):
      if n[6:] not in fams:
        return f"the calculation run gave no {n[6:]} quantity"
    elif n not in have:
      return f"no {n} was read"
  return None

def _marks_in(c: dict, evidence: dict, ledger: list) -> dict:
  cmp_ = c["compares"]
  
  left, right = _by_mark(_rows(evidence, cmp_["left"]), tuple(cmp_["left"].get("strip_prefix") or ())), _by_mark(_rows(evidence, cmp_["right"]), tuple(cmp_["right"].get("strip_prefix") or ()))
  if not left or not right:
    return _result(c, NOT_CHECKABLE, "one side has no marks to compare")
  missing = sorted(m for m in left if m not in right)
  both = [m for m in left if m in right]
  bad = len(missing) / len(left) > c["tolerance"]
  items = [i for m in missing for i in _ids(left[m])]
  agreed = [i for m in both for i in _ids(left[m]) + _ids(right[m])]
  if bad:
    return _result(c, FAIL, _say(c, "fail", n=len(missing), total=len(left), list=_list(missing)), items, agreed, total=len(left), failing=len(missing))
  return _result(c, PASS, _say(c, "pass", n=0, total=len(left), list=""), [], agreed + items, total=len(left), failing=len(missing))

def _marks_agree(c: dict, evidence: dict, ledger: list) -> dict:
  cmp_ = c["compares"]
  
  left, right = _by_mark(_rows(evidence, cmp_["left"]), tuple(cmp_["left"].get("strip_prefix") or ())), _by_mark(_rows(evidence, cmp_["right"]), tuple(cmp_["right"].get("strip_prefix") or ()))
  if not left or not right:
    return _result(c, NOT_CHECKABLE, "one side has no marks to compare")
  odd = sorted(set(left) ^ set(right))
  total = len(set(left) | set(right))
  items = [i for m in odd for i in _ids(left.get(m, [])) + _ids(right.get(m, []))]
  agreed = [i for m in set(left) & set(right) for i in _ids(left[m]) + _ids(right[m])]
  if len(odd) / total > c["tolerance"]:
    return _result(c, FAIL, _say(c, "fail", n=len(odd), total=total, list=_list(odd)), items, agreed, total=total, failing=len(odd))
  return _result(c, PASS, _say(c, "pass", n=0, total=total, list=""), [], agreed + items, total=total, failing=len(odd))

def _sum_field(rows: list, field: str) -> float | None:
  vals = [float((r.get("attrs") or {})[field]) for r in rows if (r.get("attrs") or {}).get(field) is not None]
  return sum(vals) if vals else None

def _area_fill(c: dict, evidence: dict, ledger: list) -> dict:
  cmp_ = c["compares"]
  lo, hi = cmp_["band"]
  left, right = _rows(evidence, cmp_["left"]), _rows(evidence, cmp_["right"])
  lf, rf = cmp_["left"]["field"], cmp_["right"]["field"]
  if not any((r.get("attrs") or {}).get(lf) is not None for r in left):
    return _result(c, NOT_CHECKABLE, f"the {'/'.join(cmp_['left']['classes']).lower()} readings carry no {lf}")
  if not any((r.get("attrs") or {}).get(rf) is not None for r in right):
    return _result(c, NOT_CHECKABLE, f"the {'/'.join(cmp_['right']['classes']).lower()} readings carry no {rf}")
  floors = sorted({r["floor"] for r in left + right if r.get("floor")})
  bad, ok, items, agreed = [], [], [], []
  for fl in floors:
    a, b = _sum_field([r for r in left if r.get("floor") == fl], lf), _sum_field([r for r in right if r.get("floor") == fl], rf)
    if not a or not b:
      continue
    
    mine = [r["id"] for r in left + right if r.get("floor") == fl]
    good = lo <= a / b <= hi
    (ok if good else bad).append(fl)
    (agreed if good else items).extend(mine)
  total = len(ok) + len(bad)
  
  if not total:
    return _result(c, NOT_CHECKABLE, "no floor has both rooms and a slab with areas")
  if len(bad) / total > c["tolerance"]:
    return _result(c, FAIL, _say(c, "fail", n=len(bad), total=total, list=_list(bad)), items, agreed, total=total, failing=len(bad))
  return _result(c, PASS, _say(c, "pass", n=0, total=total, list=""), [], agreed, total=total, failing=0)

def _clusters(vals: list, within: float) -> list:
  out: list = []
  for v in sorted(vals):
    if out and v - out[-1][-1] <= within:
      out[-1].append(v)
    else:
      out.append([v])
  return out

def _values_agree(c: dict, evidence: dict, ledger: list) -> dict:
  cmp_ = c["compares"]
  within = float(cmp_["within"])
  sides = []
  for key in ("left", "right"):
    field = cmp_[key]["field"]
    rows = [r for r in _rows(evidence, cmp_[key]) if (r.get("attrs") or {}).get(field) is not None]
    sides.append((rows, field))
    
  if not sides[0][0] or not sides[1][0]:
    return _result(c, NOT_CHECKABLE, "one side has no values to compare")
  vals = [sorted({round(float(r["attrs"][f]), 3) for r in rows}) for rows, f in sides]
  odd_left = [v for v in vals[0] if not any(abs(v - w) <= within for w in vals[1])]
  odd_right = [w for w in vals[1] if not any(abs(v - w) <= within for v in vals[0])]
  total = len(_clusters(vals[0] + vals[1], within))
  odd = len(odd_left) + len(odd_right)
  (rl, fl), (rr, fr) = sides
  items = [r["id"] for r in rl if round(float(r["attrs"][fl]), 3) in odd_left] + [r["id"] for r in rr if round(float(r["attrs"][fr]), 3) in odd_right]
  agreed = [r["id"] for rows, f in sides for r in rows if r["id"] not in items]
  if odd / max(total, 1) > c["tolerance"]:
    return _result(c, FAIL, _say(c, "fail", n=odd, total=total, list=_list([f"{v:g}" for v in odd_left + odd_right])), items, agreed, total=total, failing=odd)
  return _result(c, PASS, _say(c, "pass", n=0, total=total, list=""), [], agreed + items, total=total, failing=odd)

def convert(value, unit, to: str) -> float | None:
  table = SCK.units().get(to) or {}
  u = str(unit or to).lower()
  return None if u not in table else float(value) * table[u]

def _sum_family(evidence: dict, families: list, to: str) -> tuple:
  total, skipped = 0.0, 0
  for ln in evidence.get("lines") or []:
    if ln["family"] in families:
      v = convert(ln["value"], ln.get("unit"), to)
      if v is None:
        skipped += 1
      else:
        total += v
  return total, skipped

def _billing_elements(ledger: list, families: list) -> list:
  bills = {i.id: {q.line for q in i.billing.PRIVATE_QS} for i in CAT.items()}
  return sorted({e["element"] for e in ledger if bills.get(e["element"], set()) & set(families)})

def _ratio_band(c: dict, evidence: dict, ledger: list) -> dict:
  cmp_ = c["compares"]
  lo, hi = cmp_["band"]
  top, _a = _sum_family(evidence, [cmp_["top"]["family"]], cmp_["top"]["to"])
  bottom, _b = _sum_family(evidence, cmp_["bottom"]["families"], cmp_["bottom"]["to"])
  elements = _billing_elements(ledger, [cmp_["top"]["family"], *cmp_["bottom"]["families"]])
  if top <= 0 or bottom <= 0:
    return _result(c, NOT_CHECKABLE, "the calculation run gave no steel or no concrete in a unit that converts", elements=elements)
  ratio = top / bottom
  ok = lo <= ratio <= hi
  return _result(c, PASS if ok else FAIL, _say(c, "pass" if ok else "fail", ratio=ratio, lo=lo, hi=hi), [], [], elements=elements, ratio=round(ratio, 2), total=1, failing=0 if ok else 1)

def _totals_agree(c: dict, evidence: dict, ledger: list) -> dict:
  cmp_ = c["compares"]
  left, _a = _sum_family(evidence, [cmp_["left"]["family"]], cmp_["left"]["to"])
  right = evidence.get(cmp_["right"]["evidence"])
  elements = _billing_elements(ledger, [cmp_["left"]["family"]])
  if not left or not right:
    return _result(c, NOT_CHECKABLE, "one of the two steel totals is missing", elements=elements)
  off = abs(left - float(right)) / float(right) * 100.0
  if off <= c["tolerance"] * 100.0:
    return _result(c, PASS, _say(c, "pass", left=left, right=float(right), pct=c["tolerance"] * 100.0), [], [], elements=elements, total=1, failing=0)
  return _result(c, FAIL, _say(c, "fail", left=left, right=float(right), off=off), [], [], elements=elements, total=1, failing=1)

KIND_RUN = {"marks_in": _marks_in, "marks_agree": _marks_agree, "area_fill": _area_fill, "values_agree": _values_agree, "ratio_band": _ratio_band, "totals_agree": _totals_agree}

def run(ledger: list, evidence: dict, checks: list | None = None, only: tuple | None = None) -> list:
  out = []
  for c in SCK.checks() if checks is None else checks:
    kind = c["compares"]["kind"]
    if only is not None and kind not in only:
      continue
    why = _needs(c, evidence)
    out.append(_result(c, NOT_CHECKABLE, f"cannot run: {why}") if why else KIND_RUN[kind](c, evidence, ledger))
  return out

def summary(results: list) -> dict:
  by = {r: 0 for r in RESULTS}
  for x in results:
    by[x["result"]] += 1
  return by

def kinds_without_code() -> list:
  return sorted(set(SCK.KINDS) - set(KIND_RUN))

def current(ledger: list, evidence: dict, stored: list | None) -> list:
  checks = SCK.checks()
  kinds = {c["id"]: c["compares"]["kind"] for c in checks}
  keep = {r["check"]: r for r in stored or [] if kinds.get(r["check"]) in SCK.READ_KINDS}
  fresh = {r["check"]: r for r in run(ledger, evidence, [c for c in checks if c["id"] not in keep and kinds[c["id"]] in SCK.READ_KINDS])}
  fresh.update({r["check"]: r for r in run(ledger, evidence, only=SCK.LEDGER_KINDS)})
  return [({**keep, **fresh})[c["id"]] for c in checks]
