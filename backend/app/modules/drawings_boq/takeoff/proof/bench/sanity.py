from __future__ import annotations
import functools
import json
import os
import yaml
from app.engine.measure import materials as MAT
from app.modules.drawings_boq.takeoff.proof.bench import money as MN

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "sanity_ratios.yaml")
NEEDS = ("steel_kg", "concrete_cft", "bricks", "cement_bags", "grey_cost", "finishing_cost")
IN, BELOW, ABOVE, NO_RANGE, NO_FIGURE = "IN_RANGE", "BELOW", "ABOVE", "NO_RANGE", "NO_FIGURE"
STEEL_ITEMS, BRICK_ITEMS, COVER_ITEM = ("RF-01", "RF-02"), ("MS-01", "MS-02", "MS-03", "MS-04", "MS-05", "MS-06"), "PL-03"

@functools.lru_cache(maxsize=1)
def _raw() -> dict:
  with open(PATH, encoding="utf-8") as fh:
    return yaml.safe_load(fh)

def problems(data: dict | None = None) -> list:
  d = data or _raw()
  out, seen = [], set()
  if not (d.get("covered_area") or {}).get("families"):
    out.append("covered_area names at least one line family")
  for g in ("grey", "finishing"):
    if not (d.get("cost_groups") or {}).get(g):
      out.append(f"cost_groups.{g} names catalogue prefixes")
  for r in d.get("ratios") or []:
    rid = r.get("id", "?")
    out += [f"{rid}: no {f}" for f in ("id", "name", "unit", "needs", "range", "source") if f not in r]
    if rid in seen:
      out.append(f"{rid}: repeated")
    seen.add(rid)
    if r.get("needs") not in NEEDS:
      out.append(f"{rid}: needs must be one of {', '.join(NEEDS)}")
    rng = r.get("range")
    if rng is not None:
      if not (isinstance(rng, list) and len(rng) == 2 and 0 <= rng[0] < rng[1]):
        out.append(f"{rid}: a range is [low, high] with low below high")
      if not r.get("source"):
        out.append(f"{rid}: a range names its source: the QS and the date")
  return out

def covered(lines: list) -> tuple:
  for fam in _raw()["covered_area"]["families"]:
    v = sum(float(ln["value"]) for ln in lines if ln.get("family") == fam and (ln.get("unit") or "sft") == "sft" and ln.get("value") is not None)
    if v > 0:
      return v, fam
  return None, None

def _sum(items: list, elements: tuple, unit: str) -> float | None:
  got = [MN.to_rate_unit(float(it["quantity"]), it.get("unit"), unit) for it in items if it["element"] in elements and it.get("unit")]
  got = [g for g in got if g is not None]
  return sum(got) if got else None

def workbook_figures(answers_doc: dict | None, rates: dict) -> dict:
  items = [it for it in (answers_doc or {}).get("items") or [] if it.get("confirmed")]
  out: dict = {k: None for k in NEEDS}
  if not items:
    return {**out, "covered": None}
  steel = [v for v in (_sum(items, (e,), "kg") for e in STEEL_ITEMS) if v is not None]
  out["steel_kg"] = steel[0] if steel else None
  out["concrete_cft"] = _sum(items, tuple(sorted({it["element"] for it in items if str(it["element"]).startswith("RC-")})), "cft")
  brick = _sum(items, BRICK_ITEMS, "cft")
  out["bricks"] = None if brick is None else brick * float(MAT.constant(MAT.BRICKS_PER_CFT)["value"])
  out["covered"] = _sum(items, (COVER_ITEM,), "sft")
  out.update(_cost(items, rates))
  return out

def _cost(items: list, rates: dict) -> dict:
  by = MN.money_of_items(items, rates)["by_element"]
  groups = _raw()["cost_groups"]
  out = {}
  for key, name in (("grey_cost", "grey"), ("finishing_cost", "finishing")):
    got = [v for el, v in by.items() if str(el).split("-")[0] in groups[name]]
    out[key] = sum(got) if got else None
  return out

def trace_figures(lines: list, sched: dict, rows: list, rates: dict) -> dict:
  tot = sched["totals"]
  area, fam = covered(lines)
  items = [{"element": r["element"], "quantity": r["trace_qty"], "unit": r["unit"]} for r in rows if r.get("trace_qty") is not None and r["floor"] == "ALL"]
  have = {i["element"] for i in items}
  items += [{"element": r["element"], "quantity": r["trace_qty"], "unit": r["unit"]} for r in rows if r.get("trace_qty") is not None and r["floor"] != "ALL" and r["element"] not in have]
  out = {"steel_kg": tot.get("steel (kg)"), "concrete_cft": tot.get("concrete wet (cft)"), "bricks": tot.get("bricks (nos)"), "cement_bags": tot.get("cement (bags)"), "covered": area, "covered_family": fam}
  out.update(_cost(items, rates) if rates.get("per_item_unit") else {"grey_cost": None, "finishing_cost": None})
  return out

def _flag(v, rng) -> str:
  if v is None:
    return NO_FIGURE
  if not rng:
    return NO_RANGE
  return BELOW if v < rng[0] else ABOVE if v > rng[1] else IN

def of_case(lines: list, sched: dict, answers_doc: dict | None, rows: list, rates: dict) -> dict:
  mine, book = trace_figures(lines, sched, rows, rates), workbook_figures(answers_doc, rates)
  out = []
  for r in _raw()["ratios"]:
    a, b = mine.get(r["needs"]), book.get(r["needs"])
    t = None if a is None or not mine["covered"] else a / mine["covered"]
    w = None if b is None or not book.get("covered") else b / book["covered"]
    out.append({"id": r["id"], "name": r["name"], "unit": r["unit"], "trace": None if t is None else round(t, 4), "workbook": None if w is None else round(w, 4), "range": r["range"],
      "trace_flag": _flag(t, r["range"]), "workbook_flag": _flag(w, r["range"]), "range_source": r["source"]})
  return {"covered_sft": None if mine["covered"] is None else round(mine["covered"], 1), "covered_from": mine["covered_family"], "workbook_covered_sft": None if not book.get("covered") else round(book["covered"], 1), "ratios": out}

def lines_for(cases: list, fmt, table) -> list:
  L = ["## Sanity ratios (G8 to G13)", "",
    "Each ratio is a quantity per square foot of covered area. Trace's figure is the material schedule of the product run (QS defaults taken where a choice card has one, so cement and sand rest on a default) over the ceiling plaster area, or the floor finish area when a set has no ceiling plaster, named in the second column. "
    "The workbook figure is the same ratio from the QS workbook's confirmed items over its ceiling plaster area. A ratio with no range is shown as two labelled points and flagged nowhere; the QS gives the ranges in sitting 3. A set outside a range is flagged, never corrected.", ""]
  body = []
  for c in cases:
    s = c.get("sanity")
    if not s:
      continue
    for r in s["ratios"]:
      rng = "-" if not r["range"] else f"{r['range'][0]:g} to {r['range'][1]:g}"
      body.append([c["name"], f"{fmt(s['covered_sft'])} ({s['covered_from'] or '-'})", f"{r['id']} {r['name']}", r["unit"], "-" if r["trace"] is None else f"{r['trace']:g}", "-" if r["workbook"] is None else f"{r['workbook']:g}", rng,
        r["trace_flag"] if r["range"] else "no range yet"])
      
  L += table(["Set", "Covered sft (from)", "Ratio", "Unit", "Trace", "Workbook", "Range", "Trace against range"], body) if body else ["No set has a schedule."]
  L += ["", "Material schedule totals of the product run, per set (the schedule of each set is in `materials/<set>.json` beside this report, every line with its inputs and constants):", ""]
  rows = []
  for c in cases:
    m = c.get("materials")
    if not m:
      continue
    t = m["totals"]
    rows.append([c["name"], fmt(t.get("bricks (nos)")), fmt(t.get("cement (bags)")), fmt(t.get("sand (cft)")), fmt(t.get("crush (cft)")), fmt(t.get("steel (kg)")), fmt(t.get("concrete wet (cft)")), len(m["unresolved"])])
  L += table(["Set", "Bricks", "Cement bags", "Sand cft", "Crush cft", "Steel kg", "Concrete cft (wet)", "Lines not computed"], rows) if rows else []
  return L + [""]

def write_schedules(out_dir: str, cases: list) -> int:
  folder = os.path.join(out_dir, "materials")
  os.makedirs(folder, exist_ok=True)
  n = 0
  for c in cases:
    if c.get("materials"):
      with open(os.path.join(folder, f"{c['name']}.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(c["materials"], fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
      n += 1
  return n

def write_sanity(out_dir: str, cases: list) -> int:
  """sanity.json beside bench.md: the sanity ratios of each set, which the K result report reads."""
  got = {c["name"]: c["sanity"] for c in cases if c.get("sanity")}
  with open(os.path.join(out_dir, "sanity.json"), "w", encoding="utf-8", newline="\n") as fh:
    json.dump(got, fh, indent=1, sort_keys=True, ensure_ascii=False)
    fh.write("\n")
  return len(got)
