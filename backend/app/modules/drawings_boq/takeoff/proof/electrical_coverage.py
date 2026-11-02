from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import electrical as EL

REASON_TEXT = {
  EL.NOT_COUNTABLE: "the legend picture has fewer than three drawn objects and no text tag, so there is nothing to match",
  EL.TAG_NOT_ON_PLAN: "the legend symbol is a text tag and the tag is not on the plan pages",
  EL.NO_PLAN_HIT: "the legend picture was searched on the plans and no run of drawn objects of the same sizes and layout was found",
}

def view(accs: list) -> dict | None:
  got = [e for a in accs for e in a.electrical]
  if not got:
    return None
  e = got[0]
  return {k: v for k, v in e.items() if k != "drawing_id"}

def lines(cov: dict) -> list:
  pages = cov["pages"]
  out = [f"**Electrical legend coverage** (not part of the hash): {cov['counted']} of {cov['legend_symbols']} legend rows are counted on the plan pages {', '.join(str(p) for p in pages)}; the other {cov['legend_symbols'] - cov['counted']} each carry a reason ("
    + ", ".join(f"{k} {n}" for k, n in sorted(cov["reasons"].items())) + ").", "",
    "| # | Legend row | Group | Drawn objects | Text tag | " + " | ".join(f"Page {p}" for p in pages) + " | Work item | Reason |", "|---|---|---|---|---|" + "---|" * len(pages) + "---|---|"]
  for r in cov["rows"]:
    out.append(f"| {r['index']} | {r['name']} | {r['kind']} | {r['objects']} | {r['token'] or ''} | " + " | ".join(str(r["plan_counts"].get(str(p), 0)) for p in pages) + f" | {r['work_item']} | {r['reason'] or ''} |")
  return out + [""]
