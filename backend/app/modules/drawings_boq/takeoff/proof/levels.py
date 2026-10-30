from __future__ import annotations
import statistics

LIMIT_PCT = 5.0
WIDE_PCT = 10.0
QS_TOLERANCE = 1e-6      

def corrected_expected(expected: list, corrections: list) -> tuple:
  by_key = {e["key"]: e for e in expected}
  out = {k: dict(e) for k, e in by_key.items()}
  applied, pending, problems = [], [], []
  
  for c in corrections:
    e = by_key.get(c["line"])
    if e is None:
      problems.append(f"{c['line']}: no such expected line")
      continue
    if e["qs"] is None or abs(e["qs"] - c["qs_figure"]) > QS_TOLERANCE * max(1.0, abs(e["qs"])):
      problems.append(f"{c['line']}: the correction starts from {c['qs_figure']:g} but expected.yaml has {e['qs']}")
      continue
  
    rec = {"line": c["line"], "qs_figure": c["qs_figure"], "corrected": c["corrected"], "reason": c["reason"]}
    if c["signed"]:
      out[c["line"]]["qs"] = c["corrected"]
      applied.append(rec)
    else:
      pending.append(rec)
  return [out[e["key"]] for e in expected], applied, pending, problems

def _row(l: dict) -> dict:
  return {k: l.get(k) for k in ("key", "unit", "trace", "qs", "diff_pct_qs", "status", "class")}

def level_view(lines: list) -> dict:
  judged = [l for l in lines if l.get("qs") is not None]
  both = [l for l in judged if l.get("trace") is not None and l.get("diff_pct_qs") is not None]
  errs = [abs(l["diff_pct_qs"]) for l in both]
  within_5 = sum(1 for e in errs if e <= LIMIT_PCT)
  
  return {"lines": [_row(l) for l in judged], "summary": {"with_qs": len(judged), "with_trace": len(both), "no_trace": len(judged) - len(both), "within_5": within_5,
    "within_10": sum(1 for e in errs if e <= WIDE_PCT), "share_within_5_pct": round(100.0 * within_5 / len(judged), 1) if judged else None,
    "median_abs_error_pct": round(statistics.median(errs), 2) if errs else None}}

def over_limit(lines: list, limit: float = LIMIT_PCT) -> list:
  return [l["key"] for l in lines if l.get("qs") is not None and (l.get("trace") is None or l.get("diff_pct_qs") is None or abs(l["diff_pct_qs"]) > limit)]

def residual_check(lines: list, residuals: list, limit: float = LIMIT_PCT) -> dict:
  over = over_limit(lines, limit)
  listed = {r["line"] for r in residuals}
  return {"limit_pct": limit, "over": len(over), "entries": len(residuals), "missing": sorted(k for k in over if k not in listed), "stale": sorted(k for k in listed if k not in set(over))}

def rules_view(ledger: list) -> dict:
  ids: dict = {}
  
  for r in ledger:
    for x in (((r.get("trace") or {}).get("inputs") or {}).get("rules") or []):
      ids[str(x.get("id"))] = ids.get(str(x.get("id")), 0) + 1
  case_file = sorted(k for k in ids if not k.startswith("seed:"))
  seed = sorted(k for k in ids if k.startswith("seed:"))
  return {"case_file": case_file, "seed_unconfirmed": seed}

def facts_passed(facts: list) -> list:
  return sorted({str(f["text"]) for f in facts if f.get("status") == "PASS"})

def facts_regressions(facts: list, passed: list) -> list:
  now = {str(f["text"]): f.get("status") for f in facts}
  return sorted(t for t in passed if now.get(t) != "PASS")

def build(accept_all: list, decided: list, ruled: list, *, decisions: list, decision_log: dict | None, corrections: list, applied: list, pending: list, correction_problems: list,
  ledger: list, residuals: list) -> dict:
  return {"accept_all": level_view(accept_all), "decided": level_view(decided), "ruled": level_view(ruled),
    "decisions": {"entries": len(decisions), "answered_by": {b: sum(1 for d in decisions if d["answered_by"] == b) for b in ("DRAWING", "QS") if any(d["answered_by"] == b for d in decisions)},
      "applied": list((decision_log or {}).get("applied") or []), "unmatched": list((decision_log or {}).get("unmatched") or [])},
    "corrections": {"entries": len(corrections), "signed": len(applied), "unsigned": len(pending), "applied": applied, "pending": pending, "problems": correction_problems},
    "rules": rules_view(ledger), "residuals": residual_check(ruled, residuals)}

def _pct(v) -> str:
  return "" if v is None else f"{v:+.1f}%"

def _n(v) -> str:
  return "" if v is None else f"{v:,.1f}"

def render(lv: dict) -> list:
  a, d, r = lv["accept_all"], lv["decided"], lv["ruled"]
  out = ["## Three levels", "",
    "`accept_all`: everything the readings give is accepted. `decided`: the answers in decisions.yaml applied first. `ruled`: decided, against the QS figures with his signed corrections. Differences are against the QS figure of that level.", "",
    "| Line | Unit | QS (ruled) | accept_all | diff | decided | diff | ruled | diff |", "|---|---|---|---|---|---|---|---|---|"]
  da = {l["key"]: l for l in a["lines"]}
  dd = {l["key"]: l for l in d["lines"]}
  
  for l in r["lines"]:
    x, y = da.get(l["key"]) or {}, dd.get(l["key"]) or {}
    out.append(f"| {l['key']} | {l['unit']} | {_n(l['qs'])} | {_n(x.get('trace'))} | {_pct(x.get('diff_pct_qs'))} | {_n(y.get('trace'))} | {_pct(y.get('diff_pct_qs'))} | {_n(l['trace'])} | {_pct(l['diff_pct_qs'])} |")
  for name, v in (("accept_all", a), ("decided", d), ("ruled", r)):
    s = v["summary"]
    out.append(f"| **{name}** | | {s['with_qs']} lines | within 5%: {s['within_5']} | within 10%: {s['within_10']} | no Trace number: {s['no_trace']} | median error {s['median_abs_error_pct'] if s['median_abs_error_pct'] is not None else '-'}% | {s['share_within_5_pct'] if s['share_within_5_pct'] is not None else '-'}% within 5% | |")
  dc, cr, ru, rs = lv["decisions"], lv["corrections"], lv["rules"], lv["residuals"]
  out += ["", f"**Decisions** (decisions.yaml): {dc['entries']} answered" + (f" ({', '.join(f'{k} {n}' for k, n in dc['answered_by'].items())})" if dc["answered_by"] else "") + f"; applied to {sum(x['rows'] for x in dc['applied'])} rows"
    + (f"; **not matched: {', '.join(x['id'] for x in dc['unmatched'])}**" if dc["unmatched"] else "") + ".",
    f"**QS corrections** (qs_corrections.yaml): {cr['entries']} listed, {cr['signed']} signed and applied, {cr['unsigned']} unsigned and not applied" + (f"; **problems: {'; '.join(cr['problems'])}**" if cr["problems"] else "") + ".",
    f"**Rules the ruled level rests on**: {len(ru['case_file'])} from the case's rule file, {len(ru['seed_unconfirmed'])} seed rules, UNCONFIRMED until the QS confirms them" + (f" ({', '.join(x[5:] for x in ru['seed_unconfirmed'])})" if ru["seed_unconfirmed"] else "") + ".",
    f"**Residuals** (residuals.yaml): {rs['over']} lines over {rs['limit_pct']:g}% at the ruled level, {rs['entries']} entries; no entry for: {', '.join(rs['missing']) or 'none'}; stale: {', '.join(rs['stale']) or 'none'}.", ""]
  return out
