from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
import math
from app.modules.drawings_boq.takeoff.reading_score.labels import Unit, NEGATIVE, POSITIVE, label_unit

SCORE_VERSION = 1
INF = float("inf")

@dataclass(frozen=True)
class MatchRule:
  position_tol_pt: float = 18.0     
  positions: bool = True            
  size_tol_pct: float = 5.0         
  size_tol_mm: float = 10.0         
  regression_tol: float = 0.02      
  gate_min_units: int = 5           
  max_listed: int = 60              

  def as_dict(self) -> dict:
    return {"position_tol_pt": self.position_tol_pt, "positions": self.positions, "size_tol_pct": self.size_tol_pct, "size_tol_mm": self.size_tol_mm,
      "regression_tol": self.regression_tol, "gate_min_units": self.gate_min_units, "max_listed": self.max_listed}

  @staticmethod
  def from_dict(d: dict | None) -> "MatchRule":
    base = MatchRule()
    
    d = d or {}
    def num(key: str, lo: float, hi: float) -> float:
      v = d.get(key, getattr(base, key))
      try:
        f = float(v)
      except (TypeError, ValueError):
        raise ValueError(f"{key} must be a number.")
      if not (lo <= f <= hi) or not math.isfinite(f):
        raise ValueError(f"{key} must be between {lo:g} and {hi:g}.")
      return f
    return MatchRule(position_tol_pt=num("position_tol_pt", 0, 500), positions=bool(d.get("positions", base.positions)), size_tol_pct=num("size_tol_pct", 0, 100),
      size_tol_mm=num("size_tol_mm", 0, 500), regression_tol=num("regression_tol", 0, 0.5), gate_min_units=int(num("gate_min_units", 1, 10000)),
      max_listed=int(num("max_listed", 0, 1000)))

def rule_hash(rule: MatchRule) -> str:
  return hashlib.sha1(json.dumps(rule.as_dict(), sort_keys=True).encode()).hexdigest()[:20]

def _dist(a: Unit, b: Unit) -> float | None:
  if a.x is None or a.y is None or b.x is None or b.y is None:
    return None
  return math.hypot(a.x - b.x, a.y - b.y)

def pair_units(labels: list, reads: list, rule: MatchRule) -> tuple:
  pairs: list = []
  used_l: set = set()
  used_r: set = set()
  by_l: dict = {}
  by_r: dict = {}
  
  for i, u in enumerate(labels):
    if u.mark:
      by_l.setdefault(u.mark, []).append(i)
  for i, u in enumerate(reads):
    if u.mark:
      by_r.setdefault(u.mark, []).append(i)
  for mark in sorted(by_l):
    rs = by_r.get(mark)
    if not rs:
      continue
  
    options = []
    for li in by_l[mark]:
      for ri in rs:
        d = _dist(labels[li], reads[ri]) if rule.positions else None
        options.append((INF if d is None else d, li, ri))
    options.sort()
    for _, li, ri in options:
      if li not in used_l and ri not in used_r:
        used_l.add(li)
        used_r.add(ri)
        pairs.append((li, ri))
        
  if rule.positions:
    options = []
    for li, l in enumerate(labels):
      if li in used_l or l.x is None:
        continue
    
      for ri, r in enumerate(reads):
        if ri in used_r or r.x is None or (l.mark and r.mark):
          continue
        d = _dist(l, r)
        if d is not None and d <= rule.position_tol_pt:
          options.append((d, li, ri))
    options.sort()
    for _, li, ri in options:
      if li not in used_l and ri not in used_r:
        used_l.add(li)
        used_r.add(ri)
        pairs.append((li, ri))
  return sorted(pairs), used_l, used_r

def size_verdict(label: Unit, read: Unit, rule: MatchRule) -> str | None:
  want, got = label.size(), read.size()
  if not want:
    return None
  common = [k for k in want if k in got]
  if not common:
    return "UNREAD"
  for k in common:
    if abs(want[k] - got[k]) > max(rule.size_tol_mm, rule.size_tol_pct / 100.0 * want[k]):
      return "WRONG"
  return "OK"

def ratios(tp: int, fp: int, fn: int) -> dict:
  p = tp / (tp + fp) if (tp + fp) else None
  r = tp / (tp + fn) if (tp + fn) else None
  f1 = (2 * p * r / (p + r)) if (p is not None and r is not None and (p + r) > 0) else None
  return {"precision": None if p is None else round(p, 4), "recall": None if r is None else round(r, 4), "f1": None if f1 is None else round(f1, 4)}

def _where(u: Unit) -> dict:
  return {"family": u.family, "mark": u.text, "x": None if u.x is None else round(u.x, 1), "y": None if u.y is None else round(u.y, 1)}

def score_sheet(labels: list, reads: list, rule: MatchRule) -> dict:
  pos = [label_unit(l, i) for i, l in enumerate(labels) if l["polarity"] == POSITIVE]
  neg = [label_unit(l, i) for i, l in enumerate(labels) if l["polarity"] == NEGATIVE]
  complete = bool(labels) and all(bool(l.get("complete")) for l in labels)
  fams = sorted({u.family for u in [*pos, *neg, *reads]})
  rows, misses, wrong = [], [], []
  
  for fam in fams:
    P = [u for u in pos if u.family == fam]
    N = [u for u in neg if u.family == fam]
    R = [u for u in reads if u.family == fam]
    unjudged = 0
    
    if not rule.positions:
      unjudged = sum(1 for u in P if not u.mark) + sum(1 for u in N if not u.mark)
      P, N, R = [u for u in P if u.mark], [u for u in N if u.mark], [u for u in R if u.mark]
    pairs, used_l, used_r = pair_units(P, R, rule)
    left = [r for i, r in enumerate(R) if i not in used_r]
    npairs, _, nused = pair_units(N, left, rule)
    extras = [r for i, r in enumerate(left) if i not in nused]
    confirmed = [left[ri] for _, ri in npairs]
    size = {"checked": 0, "ok": 0, "wrong": 0, "unread": 0}
    
    for li, ri in pairs:
      v = size_verdict(P[li], R[ri], rule)
      if v is not None:
        size["checked"] += 1
        size[v.lower()] += 1
        
    tp, fn = len(pairs), len(P) - len(pairs)
    fp = len(confirmed) + (len(extras) if complete else 0)
    rows.append({"family": fam, "labels": len(P), "found": len(R), "tp": tp, "fp": fp, "fn": fn, "wrong_confirmed": len(confirmed), "unlabelled": 0 if complete else len(extras),
      "unjudged": unjudged, "size": size, **ratios(tp, fp, fn)})
    misses += [{**_where(u), "why": "NOT_FOUND"} for i, u in enumerate(P) if i not in used_l]
    wrong += [{**_where(u), "why": "REJECTED_BY_PERSON"} for u in confirmed]
    if complete:
      wrong += [{**_where(u), "why": "NOT_ON_SHEET"} for u in extras]
  return {"basis": "COMPLETE" if complete else "NEGATIVES_ONLY", "families": rows, "misses": misses[:rule.max_listed], "wrong": wrong[:rule.max_listed],
    "misses_cut": max(0, len(misses) - rule.max_listed), "wrong_cut": max(0, len(wrong) - rule.max_listed)}

def totals_of(rows: list) -> dict:
  tp, fp, fn = sum(r["tp"] for r in rows), sum(r["fp"] for r in rows), sum(r["fn"] for r in rows)
  size = {k: sum(r["size"][k] for r in rows) for k in ("checked", "ok", "wrong", "unread")}
  judged = size["ok"] + size["wrong"]
  return {"labels": sum(r["labels"] for r in rows), "found": sum(r["found"] for r in rows), "tp": tp, "fp": fp, "fn": fn,
    "wrong_confirmed": sum(r["wrong_confirmed"] for r in rows), "unlabelled": sum(r["unlabelled"] for r in rows), "unjudged": sum(r.get("unjudged", 0) for r in rows),
    "size": {**size, "match_rate": round(size["ok"] / judged, 4) if judged else None}, **ratios(tp, fp, fn)}

def by_family(sheets: list) -> list:
  acc: dict = {}
  for sh in sheets:
    for r in sh["families"]:
      a = acc.setdefault(r["family"], {"family": r["family"], "labels": 0, "found": 0, "tp": 0, "fp": 0, "fn": 0, "wrong_confirmed": 0, "unlabelled": 0, "unjudged": 0,
        "size": {"checked": 0, "ok": 0, "wrong": 0, "unread": 0}, "upper_bound": False, "sheets": 0})
      for k in ("labels", "found", "tp", "fp", "fn", "wrong_confirmed", "unlabelled", "unjudged"):
        a[k] += r[k]
      for k in a["size"]:
        a["size"][k] += r["size"][k]
      a["sheets"] += 1
      a["upper_bound"] = a["upper_bound"] or sh["basis"] != "COMPLETE"
      
  out = []
  for a in sorted(acc.values(), key=lambda x: x["family"]):
    judged = a["size"]["ok"] + a["size"]["wrong"]
    a["size"]["match_rate"] = round(a["size"]["ok"] / judged, 4) if judged else None
    out.append({**a, **ratios(a["tp"], a["fp"], a["fn"])})
  return out

def assemble(sheets: list, could_not_judge: list, rule: MatchRule, *, mode: str, extract_version, analysis_version, partial: bool, label_summary: dict) -> dict:
  fams = by_family(sheets)
  return {"score_version": SCORE_VERSION, "mode": mode, "extract_version": extract_version, "analysis_version": analysis_version, "partial": partial, "rule": rule.as_dict(),
    "totals": totals_of(fams), "families": fams, "sheets": sheets, "could_not_judge": could_not_judge, "label_summary": label_summary}

def _headline(row: dict | None) -> float | None:
  if not row:
    return None
  return row["f1"] if row.get("f1") is not None else row.get("recall")

def regression_reasons(now: dict, best: dict, rule: MatchRule) -> list:
  if now.get("partial") or best.get("partial"):
    return []
  out = []
  
  b, n = _headline(best["totals"]), _headline(now["totals"])
  if b is not None and (n is None or n < b - rule.regression_tol):
    out.append({"scope": "ALL", "best": b, "now": n})
  old = {f["family"]: f for f in best["families"]}
  for f in now["families"]:
    o = old.get(f["family"])
    if o is None or f["labels"] < rule.gate_min_units:
      continue
    bo, no = _headline(o), _headline(f)
    if bo is not None and (no is None or no < bo - rule.regression_tol):
      out.append({"scope": f["family"], "best": bo, "now": no})
  return out

def best_of(results: list) -> dict | None:
  best = None
  for rid, res in results:
    if res.get("partial"):
      continue
    h = _headline(res["totals"])
    
    if h is None:
      continue
    if best is None or h > best[0]:
      best = (h, rid, res)
  return None if best is None else {"id": best[1], "result": best[2]}

def _key(sheet: dict, item: dict) -> tuple:
  return (sheet["page_no"], item["family"], item["mark"] or "", None if item["x"] is None else round(item["x"]), None if item["y"] is None else round(item["y"]))

def compare(a: dict, b: dict) -> dict:
  fa = {f["family"]: f for f in a["families"]}
  fb = {f["family"]: f for f in b["families"]}
  rows = []
  
  for fam in sorted(set(fa) | set(fb)):
    x, y = fa.get(fam), fb.get(fam)
    def d(key):
      if x is None or y is None or x.get(key) is None or y.get(key) is None:
        return None
      return round(y[key] - x[key], 4)
    rows.append({"family": fam, "a": x, "b": y, "d_precision": d("precision"), "d_recall": d("recall"), "d_f1": d("f1")})
    
  def misses(res: dict) -> dict:
    return {_key(s, m): m for s in res["sheets"] for m in s["misses"]}
  ma, mb = misses(a), misses(b)
  tot = lambda k: None if a["totals"].get(k) is None or b["totals"].get(k) is None else round(b["totals"][k] - a["totals"][k], 4)
  return {"families": rows, "d_totals": {"precision": tot("precision"), "recall": tot("recall"), "f1": tot("f1")},
    "lost": [{"page_no": k[0], **v} for k, v in mb.items() if k not in ma][:200], "gained": [{"page_no": k[0], **v} for k, v in ma.items() if k not in mb][:200],
    "same_rule": a.get("rule") == b.get("rule"), "same_mode": a.get("mode") == b.get("mode")}
