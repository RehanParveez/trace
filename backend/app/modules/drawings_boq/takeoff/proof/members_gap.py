from __future__ import annotations
import argparse
import os
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from collections import Counter
from app.modules.drawings_boq.takeoff.proof.reading import score as RS

CLASSES = ("COLUMN", "COLUMN_SCHEDULE_CELL", "FOOTING", "FOOTING_SECTION", "BEAM_SECTION", "PLINTH_BEAM", "RCC_WALL", "TANK", "STAIR", "SLAB_PANEL")
SPLITS = ("dev", "heldout")

def set_names(root: str = CIO.HERE) -> dict:
  out: dict = {}
  for case in sorted(os.listdir(root)):
    folder = os.path.join(root, case, "reading")
    if os.path.isdir(folder):
      for key in os.listdir(folder):
        out.setdefault(key, case)
  return out

def tally(baseline: dict, classes: tuple = CLASSES) -> dict:
  rows: dict = {}
  pages: dict = {}
  for oid, outcome in baseline["outcomes"].items():
    parts = oid.split(":")
    if len(parts) < 5 or parts[1] not in ("EL", "RD") or parts[3] not in classes:
      continue
    slot = rows.setdefault((parts[3], baseline["splits"].get(oid) or "dev", parts[0]), Counter())
    page = pages.setdefault((parts[3], baseline["splits"].get(oid) or "dev", parts[0], parts[2]), Counter())
    page["missed" if outcome in (RS.MISSED_S, RS.MISSED_R) else "invented" if outcome in (RS.INV_S, RS.INV_F) else "other"] += 1
    
    if outcome == RS.OK:
      slot["matched"] += 1
    elif outcome == RS.WRONG:
      slot["wrong_value"] += 1
    elif outcome in (RS.MISSED_S, RS.MISSED_R):
      slot["missed"] += 1
    elif outcome == RS.TRUE:
      slot["true"] += 1
    elif outcome in (RS.INV_S, RS.INV_F):
      slot["invented"] += 1
      
  for (cls, split, key, _page), c in pages.items():
    rows[(cls, split, key)]["same_page"] += min(c["missed"], c["invented"])
  return rows

def _line(label: str, c: Counter) -> str:
  truth = c["matched"] + c["wrong_value"] + c["missed"]
  reads = c["true"] + c["invented"]
  recall = f"{c['matched'] + c['wrong_value']} of {truth}" if truth else "no truth"
  precision = f"{round(100 * c['true'] / reads, 1)}%" if reads else "no reads"
  return f"{label:<36} truth {truth:>3}  found {recall:<10}  of those wrong value {c['wrong_value']:>2}  reads {reads:>3}  true {c['true']:>3}  invented {c['invented']:>3}  precision {precision}  missed and invented on one page {c['same_page']:>2}"

def report(baseline: dict, names: dict, by_set: bool = False) -> list:
  rows = tally(baseline)
  out = []
  
  for cls in CLASSES:
    for split in SPLITS:
      mine = {k: v for k, v in rows.items() if k[0] == cls and k[1] == split}
      if not mine:
        continue
    
      total: Counter = Counter()
      for v in mine.values():
        total.update(v)
      out.append(_line(f"{cls} {split}", total))
      if by_set:
        for (_c, _s, key), v in sorted(mine.items(), key=lambda kv: kv[0][2]):
          out.append(_line(f"    {names.get(key, key)}", v))
  return out

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Structural member classes in the reading baseline: found, missed, true and invented, by split.")
  ap.add_argument("--by-set", action="store_true", help="one line for each set under each class")
  args = ap.parse_args(argv)
  base = RS.load_baseline()
  
  if base is None:
    print("no reading baseline found")
    return 1
  for line in report(base, set_names(), args.by_set):
    print(line)
  return 0

if __name__ == "__main__":
  raise SystemExit(main())
