from __future__ import annotations
import os
import yaml
from app.engine.catalogue import confidence as CFG
from app.modules.drawings_boq.takeoff.completeness import ledger as LG
from app.modules.drawings_boq.takeoff.flow import marks as MK

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "accuracy.yaml"), encoding="utf-8") as _fh:
  DATA = yaml.safe_load(_fh)
LIMITS = DATA["limits"]
TEXT = DATA["text"]
UNBANDED = "Not banded"
BY_MONEY, BY_COUNT = "MONEY", "COUNT"

def _f(v) -> float:
  return float(v or 0.0)

def priced(lines: list) -> bool:
  return any(ln.get("amount") is not None for ln in lines)

def not_read_names(entries: list) -> list:
  by: dict = {}
  for e in entries:
    if e["state"] == LG.NOT_READ:
      by.setdefault(e["section"], {})[e["name"]] = True
  cap = LIMITS["not_read_names_per_section"]
  return [{"section": sec, "items": sorted(names)[:cap], "more": max(0, len(names) - cap)} for sec, names in sorted(by.items())]

def coverage_block(entries: list) -> dict:
  rows = MK.coverage(entries)
  total = {s: sum(r[s] for r in rows) for s in MK.COUNTED}
  all_items = sum(total.values())
  not_read = [r["section"] for r in rows if r[LG.NOT_READ]]
  return {"sections": rows, "total": {**total, "total": all_items, "with_quantity_pct": round((total[LG.MEASURED] + total[LG.ASSUMED]) / all_items * 100.0, 1) if all_items else 0.0},
    "not_read_sections": not_read, "not_read_items": not_read_names(entries), "note": TEXT["not_read"].format(n=total[LG.NOT_READ], s=len(not_read)) if total[LG.NOT_READ] else None}

def money_block(lines: list) -> dict:
  have = [ln for ln in lines if ln.get("amount") is not None]
  if not have:
    return {"priced": False, "basis": BY_COUNT, "lines": len(lines), "priced_lines": 0, "unpriced_lines": len(lines), "total": None, "measured": None, "assumed": None, "assumed_pct": None,
      "note": TEXT["no_rates"], "assumed_lines": sum(1 for ln in lines if _f(ln.get("assumed_share")) > 0), "measured_lines": sum(1 for ln in lines if not _f(ln.get("assumed_share")))}
  total = sum(_f(ln["amount"]) for ln in have)
  assumed = sum(_f(ln.get("assumed_amount")) for ln in have)
  measured = sum(_f(ln.get("measured_amount")) for ln in have)
  return {"priced": True, "basis": BY_MONEY, "lines": len(lines), "priced_lines": len(have), "unpriced_lines": len(lines) - len(have), "total": round(total, 2), "measured": round(measured, 2),
    "assumed": round(assumed, 2), "assumed_pct": round(assumed / total * 100.0, 1) if total else 0.0, "note": None, "assumed_lines": None, "measured_lines": None}

def confidence_block(lines: list, conf: dict) -> dict:
  cal = CFG.doc().get("calibrated") or {}
  if not conf.get("shown"):
    show = CFG.doc().get("show_when") or {}
    why = TEXT["confidence_not_shown"].format(right=round((cal.get("high_items") or 0) * (cal.get("high_right_out_of_sample") or 0)), items=cal.get("high_items") or 0, need=show.get("min_items", "?"),
      pct=round((show.get("high_right") or 0) * 100)) if cal else TEXT["confidence_not_shown_uncalibrated"]
    return {"shown": False, "why": why, "bands": [], "basis": None, "calibrated": cal or None}
  
  by_money = priced(lines)
  bands = []
  total = sum(_f(ln.get("amount")) for ln in lines) if by_money else len(lines)
  for b in (CFG.HIGH, CFG.MEDIUM, CFG.LOW, UNBANDED):
    got = [ln for ln in lines if (ln.get("band") or UNBANDED) == b]
    amount = sum(_f(ln.get("amount")) for ln in got) if by_money else len(got)
    bands.append({"band": b, "lines": len(got), "amount": round(amount, 2) if by_money else None, "pct": round(amount / total * 100.0, 1) if total else 0.0})
  return {"shown": True, "why": None, "bands": bands, "basis": BY_MONEY if by_money else BY_COUNT, "calibrated": cal or None}

def questions_block(rows: list) -> dict:
  open_rows = [r for r in rows if r.get("state") == MK.OPEN]
  ranked = sorted(open_rows, key=lambda r: (r.get("effect_rs") is None, -_f(r.get("effect_rs")), str(r.get("key"))))
  shown = ranked[:LIMITS["open_questions"]]
  return {"open": len(open_rows), "money": round(sum(_f(r.get("effect_rs")) for r in open_rows), 2) if any(r.get("effect_rs") is not None for r in open_rows) else None,
    "unvalued": sum(1 for r in open_rows if r.get("effect_rs") is None),
    "rows": [{"key": r["key"], "item": r.get("item"), "prompt": r.get("prompt"), "page": r.get("page"), "effect_rs": r.get("effect_rs"), "touches": len(r.get("touches") or []), "crop_url": r.get("crop_url")} for r in shown],
    "more": max(0, len(open_rows) - len(shown))}

def assumptions_block(entries: list) -> dict:
  rows = MK.assumptions(entries)
  shown = rows[:LIMITS["assumptions"]]
  return {"count": len(rows), "more": max(0, len(rows) - len(shown)), "rows": [{"input": a["input"], "value": a.get("value"), "unit": a.get("unit"), "range": a.get("range"), "source": a.get("source"), "items": len(a["items"]), "floors": a["floors"]} for a in shown]}

def rank_key(ln: dict, shown: bool, by_money: bool) -> tuple:
  low = 1 if shown and ln.get("band") == CFG.LOW else 0
  if by_money:
    basis = _f(ln.get("amount")) if shown else _f(ln.get("assumed_amount"))
    return (-low, -basis, -_f(ln.get("amount")), str(ln.get("code")))
  return (-low, -_f(ln.get("assumed_share")), -int(ln.get("open_rows") or 0), str(ln.get("code")))

def check_first_block(lines: list, rows: list, conf: dict) -> dict:
  shown, by_money = bool(conf.get("shown")), priced(lines)
  if shown:
    pool = [ln for ln in lines if ln.get("band") == CFG.LOW]
    ranked_by = "LOW_CONFIDENCE_MONEY" if by_money else "LOW_CONFIDENCE_COUNT"
    text = TEXT["ranked_money_low"]
  else:
    pool = [ln for ln in lines if _f(ln.get("assumed_share")) > 0 or int(ln.get("open_rows") or 0) > 0]
    ranked_by = "ASSUMED_MONEY" if by_money else "ASSUMED_NO_RATES"
    text = TEXT["ranked_money_assumed"] if by_money else TEXT["ranked_no_rates"]
  pool = sorted(pool, key=lambda ln: rank_key(ln, shown, by_money))[:LIMITS["check_first"]]
  by_element: dict = {}
  
  for r in rows:
    if r.get("state") != MK.OPEN:
      continue
    for el in r.get("touches") or []:
      by_element.setdefault(el, []).append(r)
      
  out = []
  for ln in pool:
    touching = sorted({id(r): r for el in ln.get("elements") or [] for r in by_element.get(el, [])}.values(), key=lambda r: (-_f(r.get("effect_rs")), str(r.get("key"))))
    pages = sorted({p for r in touching for p in (r.get("pages") or [])})
    crop = next((r["crop_url"] for r in touching if r.get("crop_url")), None)
    out.append({"code": ln.get("code"), "description": ln.get("description"), "floor": ln.get("floor"), "unit": ln.get("unit"), "qty": ln.get("qty"), "amount": ln.get("amount"),
      "band": ln.get("band") if shown else None, "why": ln.get("band_why") if shown else None, "assumed_amount": ln.get("assumed_amount"), "assumed_share": ln.get("assumed_share"),
      "open_rows": ln.get("open_rows") or 0, "pages": pages, "crop_url": crop})
  return {"ranked_by": ranked_by, "text": text, "lines": out, "pool": len(pool)}

def build(*, project: dict, lines: list, entries: list, rows: list, conf: dict, track: dict, generated: str | None = None, profile: str | None = None) -> dict:
  return {"title": TEXT["title"], "intro": TEXT["intro"], "project": project, "generated": generated, "profile": profile, "coverage": coverage_block(entries), "money": money_block(lines),
    "confidence": confidence_block(lines, conf), "questions": questions_block(rows), "assumptions": assumptions_block(entries), "check_first": check_first_block(lines, rows, conf),
    "track_record": track, "footer": TEXT["footer"]}

def flow_lines(body_lines: list, marks: list) -> list:
  out = []
  for ln, m in zip(body_lines, marks):
    amount = ln.get("amount")
    if amount:
      share = _f(m.get("assumed_amount")) / float(amount)
    else:
      share = {"MEASURED": 0.0, "ASSUMED": 1.0}.get(m.get("state"), 0.5)
    out.append({"code": ln.get("code"), "description": ln.get("description"), "floor": ln.get("floor"), "unit": ln.get("unit"), "qty": ln.get("qty"), "amount": amount,
      "measured_amount": m.get("measured_amount"), "assumed_amount": m.get("assumed_amount"), "assumed_share": round(share, 4), "band": m.get("band"), "band_why": m.get("band_why"),
      "elements": m.get("elements") or [], "open_rows": m.get("open_rows") or 0})
  return out
