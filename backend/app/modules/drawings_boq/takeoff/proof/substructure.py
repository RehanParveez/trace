from __future__ import annotations
import argparse
import json
import os
import pathlib
from app.modules.drawings_boq.takeoff.prep import closure_facts as CF
from app.engine.measure import readings as RD
from app.modules.drawings_boq.takeoff.extract import foundation_runs as FR

MM_FOOT = 304.8
MM_INCH = 25.4

def foundation_docs(read: list) -> list:
  """(page_no, runs document) for every sheet where the foundation layout plan was read as a wall plan."""
  return [(sh["page_no"], (sh.get("meta") or {}).get("foundation_runs")) for sh in read if ((sh.get("meta") or {}).get("foundation_runs") or {}).get("read") == "OK"]

def pits(read: list, page: int) -> list:
  out: list = []
  for sh in read:
    if sh["page_no"] != page:
      continue
    for c in sh["candidates"]:
      p = c.params or {}
      if c.category == "FOOTING" and p.get("length_mm") and p.get("width_mm"):
        out.append({"mark": c.tag, "l_mm": float(p["length_mm"]), "w_mm": float(p["width_mm"]), "count": int(c.count or 1)})
  return out

def _footing(read: list, mark: str) -> dict | None:
  return CF.wall_footing(read, mark)

def run_figures(run: dict, rec: dict) -> dict:
  steps = rec["steps"]
  step_area_in2 = sum(float(s["width_in"]) * float(s["height_in"]) for s in steps)
  steps_h_in = sum(float(s["height_in"]) for s in steps)
  depth_in = float(rec["depth_below_ngl_in"])
  shaft_in = max(depth_in - steps_h_in - float(rec["pcc_in"]) - float(rec["sand_in"]), 0.0)
  return {"len_ft": run["length_mm"] / MM_FOOT, "trench_ft": float(rec["trench_width_in"]) / 12.0, "depth_ft": depth_in / 12.0, "pcc_ft": float(rec["pcc_in"]) / 12.0, "sand_ft": float(rec["sand_in"]) / 12.0,
    "step_area_ft2": step_area_in2 / 144.0, "shaft_ft": shaft_in / 12.0, "wall_ft": float(rec["wall_in"]) / 12.0, "dpc_ft": float(rec["dpc_in"] or 0.0) / 12.0}

def measure(read: list, page: int, doc: dict, plinth_mm: float | None) -> dict:
  pit_offset_mm = float(RD.convention("column_footing.pcc_offset_mm"))
  working_space_mm = float(RD.convention("excavation.working_space_mm"))
  natural_ground_mm = float(RD.convention("site.natural_ground_mm"))
  boundary_in_brick = RD.flag("boundary.footings_in_foundation_brick")
  recs = {m: _footing(read, m) for m in ("W1", "W2", "W3", "W4")}
  missing = sorted(m for m, r in recs.items() if r is None)
  groups = {FR.HOUSE: [], FR.HOUSE_ON_EDGE: [], FR.BOUNDARY: []}
  
  for r in doc["runs"]:
    if recs.get(r["mark"]) is not None:
      groups[r["kind"]].append(run_figures(r, recs[r["mark"]]))
  plinth_ft = max((plinth_mm or 0.0) - natural_ground_mm, 0.0) / MM_FOOT
  ws = working_space_mm / MM_FOOT

  def total(kinds, key):
    return sum(key(g) for k in kinds for g in groups[k])
  house = (FR.HOUSE, FR.HOUSE_ON_EDGE)
  every = (FR.HOUSE, FR.HOUSE_ON_EDGE, FR.BOUNDARY)
  pit_rows = pits(read, page)
  pit_exc = pit_pcc = pit_bed = 0.0
  
  for p in pit_rows:
    l, w = p["l_mm"] / MM_FOOT, p["w_mm"] / MM_FOOT
    pcc_l, pcc_w = l + 2.0 * pit_offset_mm / MM_FOOT, w + 2.0 * pit_offset_mm / MM_FOOT
    depth = (recs["W3"]["depth_below_ngl_in"] / 12.0) if recs.get("W3") else 0.0
    pcc = (recs["W3"]["pcc_in"] / 12.0) if recs.get("W3") else 0.0
    pit_exc += p["count"] * (pcc_l + ws) * (pcc_w + ws) * depth
    pit_pcc += p["count"] * pcc_l * pcc_w * pcc
    pit_bed += p["count"] * pcc_l * pcc_w
    
  sides = RD.choice("termite.scope") == "FLOOR_BEDS_AND_SIDES"
  side_sft = sum(g["len_ft"] * g["depth_ft"] * 2.0 for k in every for g in groups[k])
  for p in pit_rows:
    l, w = p["l_mm"] / MM_FOOT + 2.0 * pit_offset_mm / MM_FOOT, p["w_mm"] / MM_FOOT + 2.0 * pit_offset_mm / MM_FOOT
    side_sft += p["count"] * 2.0 * (l + w) * ((recs["W3"]["depth_below_ngl_in"] / 12.0) if recs.get("W3") else 0.0)
  def exc(g):
    return (g["trench_ft"] + ws) * g["len_ft"] * g["depth_ft"]
  def brick(g):
    return g["len_ft"] * (g["step_area_ft2"] + g["wall_ft"] * (g["shaft_ft"] + plinth_ft))
  out = {"page": page, "missing_footings": missing, "scale_mm_per_pt": doc["mm_per_pt"], "outline_ft": [round(v / MM_FOOT, 2) for v in doc["outline_mm"]], "assumed_runs": sum(1 for r in doc["runs"] if r["type_assumed"]),
    "length_ft": {k: round(sum(g["len_ft"] for g in v), 1) for k, v in groups.items()},
    "excavation_cft": {"house": round(total(house, exc), 1), "boundary": round(total((FR.BOUNDARY,), exc), 1), "pits": round(pit_exc, 1), "total": round(total(every, exc) + pit_exc, 1)},
    "pcc_cft": {"house": round(total(house, lambda g: g["len_ft"] * g["trench_ft"] * g["pcc_ft"]), 1), "boundary": round(total((FR.BOUNDARY,), lambda g: g["len_ft"] * g["trench_ft"] * g["pcc_ft"]), 1), "pits": round(pit_pcc, 1)},
    "sand_cft": round(total(every, lambda g: g["len_ft"] * g["trench_ft"] * g["sand_ft"]), 1),
    "termite_sides_sft": round(side_sft, 1), "termite_scope": RD.choice("termite.scope"),
    "termite_beds_sft": {"house": round(total(house, lambda g: g["len_ft"] * g["trench_ft"]), 1), "boundary": round(total((FR.BOUNDARY,), lambda g: g["len_ft"] * g["trench_ft"]), 1), "pits": round(pit_bed, 1)},
    "termite_trench_and_pit_sft": round(total(every, lambda g: g["len_ft"] * g["trench_ft"]) + pit_bed + (side_sft if sides else 0.0), 1),
    "brick_foundation_cft": {"house": round(total(house, brick), 1), "boundary": round(total((FR.BOUNDARY,), brick), 1), "counted_boundary": boundary_in_brick},
    "dpc_horizontal_sft": {"house": round(total(house, lambda g: g["len_ft"] * g["wall_ft"]), 1), "boundary": round(total((FR.BOUNDARY,), lambda g: g["len_ft"] * g["wall_ft"]), 1), "doors_deducted": False},
    "vertical_dpc_sft": round(sum(r["length_mm"] / MM_FOOT for r in doc["runs"] if r["kind"] in house and r["exterior"]) * plinth_ft, 1),
    "boundary_length_ft": round(sum(r["length_mm"] for r in doc["runs"] if r["kind"] == FR.BOUNDARY) / MM_FOOT, 1),
    "plinth_ft": round(plinth_ft, 2), "natural_ground_mm": natural_ground_mm, "flags": ["NSL_AS_PER_SITE", "PIT_OFFSET_STATED_NOT_READ"] + (["FOOTING_TYPE_ASSUMED"] if any(r["type_assumed"] for r in doc["runs"]) else [])}
  out["pits"] = [{**p, "l_ft": round(p["l_mm"] / MM_FOOT, 2), "w_ft": round(p["w_mm"] / MM_FOOT, 2)} for p in pit_rows]
  
  return out

def overlay(doc: dict, path: pathlib.Path) -> None:
  import matplotlib
  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  colors = {"W1": "#1d6fb8", "W2": "#d1495b", "W3": "#2e8b57", "W4": "#e08a00"}
  fig, ax = plt.subplots(figsize=(9, 12))
  
  seen: set = set()
  for r in doc["runs"]:
    style = "--" if r["type_assumed"] else "-"
    width = 5.0 if r["wall_in"] == 9.0 else 2.5
    label = r["mark"] + (" on plot line" if r["kind"] != FR.HOUSE else "")
    key = (r["mark"], r["kind"])
    ax.plot([r["p0"][0], r["p1"][0]], [r["p0"][1], r["p1"][1]], style, color=colors[r["mark"]], lw=width, solid_capstyle="butt", label=None if key in seen else label)
    seen.add(key)
    mx, my = (r["p0"][0] + r["p1"][0]) / 2.0, (r["p0"][1] + r["p1"][1]) / 2.0
    ax.text(mx, my, f"{r['length_mm'] / MM_FOOT:.1f}", fontsize=7, ha="center", va="center", bbox={"fc": "white", "ec": "none", "pad": 0.5})
    
  ax.set_aspect("equal")
  ax.legend(loc="lower center", fontsize=8, ncol=3)
  ax.set_title("Foundation plan runs by W type (feet; dashed = type assumed)")
  fig.savefig(path, dpi=110, bbox_inches="tight")
  plt.close(fig)

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Reads a case, takes the foundation layout plan as a wall plan and measures the substructure from it. Nothing here reaches the bill.")
  ap.add_argument("case")
  ap.add_argument("--cases-dir")
  ap.add_argument("--out", default="substructure_out")
  args = ap.parse_args(argv)
  from app.engine.measure import rulebook as RB
  from app.modules.drawings_boq.takeoff.run import reader as RDR
  from app.modules.drawings_boq.takeoff.proof import case_io as CIO
  
  spec = CIO.load_case(os.path.join(CIO.HERE, args.case))
  files, _ = CIO.find_files(spec, args.cases_dir or os.environ.get("TRACE_CASES_DIR"))
  rows, _b, _f = CIO.load_company_rules(spec)
  with RB.using_case(rows):
    res = RDR.read_set([(n, open(files[n], "rb").read()) for n in spec["pdfs"]])
  read = [r for _n, rws, _p in res for r in rws]
  docs = foundation_docs(read)
  if not docs:
    print("No foundation layout plan was read as a wall plan in this case.")
    return 1
  levels = CF.level_names(read)
  out = pathlib.Path(args.out)
  out.mkdir(parents=True, exist_ok=True)
  
  doc_all = {}
  for page, doc in docs:
    figures = measure(read, page, doc, levels.get("plinth_mm"))
    doc_all[str(page)] = figures
    overlay(doc, out / f"{args.case}_foundation_p{page}.png")
    print(json.dumps(figures, indent=1))
  (out / f"{args.case}_substructure.json").write_text(json.dumps(doc_all, indent=1), encoding="utf8")
  return 0

if __name__ == "__main__":
  raise SystemExit(main())
