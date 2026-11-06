from __future__ import annotations
import re
from collections import Counter
from app.modules.drawings_boq.takeoff.profile import title_zone as TZ

POINTS = ("units", "bar_notation", "schedule_layout", "walls", "labels", "title_block", "sheet_arrangement", "scale", "legend", "section_titles")
VALUES = {
  "units": ("FT_IN", "MM"), "bar_notation": ("HASH", "MM", "T"), "schedule_layout": ("MARK_ROWS", "MARK_COLUMNS", "DRAWN_SECTIONS"), "walls": ("HATCHED", "LINES", "FILLED"),
  "labels": ("TEXT", "OUTLINED"), "title_block": ("BOTTOM_STRIP", "RIGHT_STRIP"), "sheet_arrangement": ("SEPARATE", "COMBINED"), "scale": ("PRINTED_TRUE", "PRINTED_FALSE", "NONE"),
  "legend": ("PRESENT", "ABSENT"), "section_titles": ("LETTER_PAIR", "NUMBER_PAIR", "X_SECTION", "DETAIL_NUMBER")}
MIN_UNIT_TOKENS = 5
MIN_BAR_TOKENS = 5
MIN_HEADER_WORDS = 3
MIN_BLOCK_BOXES = 2
PDF_SHIFT = 1000
MIN_SECTION_TITLES = 2
WALL_HATCH_MIN = 200
WALL_FILL_MIN = 40
PLAN_PATHS = 800
OUTLINED_MAX_WORDS = 20
OUTLINED_MIN_PATHS = 2000
LEGEND_PAGES_FOR_ABSENT = 5
SCALE_RATIO = re.compile(r"^\d\s*:\s*\d{2,4}$|^\d+/\d+\"?=1'", re.I)
DISCIPLINE_PAGES = 2
CHECKED_SCALE = ("MEASURED", "LABELS", "SETTLED", "OUTLINE")
EVIDENCE_CAP = 6
ARCH_DISCIPLINES = ("ARCHITECTURAL",)

def _entry(value, confidence: float, evidence: list, **more) -> dict:
  return {"value": value, "confidence": round(float(confidence), 3), "evidence": evidence[:EVIDENCE_CAP], **more}

def _share(counts: dict) -> tuple:
  total = sum(counts.values())
  if not total:
    return None, 0.0
  key = max(counts, key=lambda k: counts[k])
  return key, counts[key] / total

def units(pages: list) -> dict:
  ft = sum(p["ft_in"] for p in pages)
  mm = sum(p["mm"] for p in pages)
  notes = Counter(p["dimension_note"] for p in pages if p.get("dimension_note"))
  ev = [{"page": p["page"], "ft_in": p["ft_in"], "mm": p["mm"]} for p in pages if p["ft_in"] or p["mm"]]
  
  for note, n in notes.items():
    ev.append({"note": f"ALL DIMENSIONS IN {note}", "pages": n})
    if note.startswith(("FEET", "FT", "INCH")):
      ft += 5 * n
    else:
      mm += 5 * n
  if ft + mm < MIN_UNIT_TOKENS:
    return _entry(None, 0.0, ev, counts={"ft_in": ft, "mm": mm})
  value, share = _share({"FT_IN": ft, "MM": mm})
  return _entry(value, share, ev, counts={"ft_in": ft, "mm": mm})

def bar_notation(pages: list) -> dict:
  counts = {"HASH": sum(p["bar_hash"] for p in pages), "MM": sum(p["bar_mm"] for p in pages), "T": sum(p["bar_t"] for p in pages)}
  ev = [{"page": p["page"], "hash": p["bar_hash"], "mm": p["bar_mm"], "t": p["bar_t"]} for p in pages if p["bar_hash"] or p["bar_mm"] or p["bar_t"]]
  if sum(counts.values()) < MIN_BAR_TOKENS:
    return _entry(None, 0.0, ev, counts=counts)
  value, share = _share(counts)
  return _entry(value, share, ev, counts=counts)

def schedule_layout(pages: list) -> dict:
  votes: Counter = Counter()
  ev: list = []
  
  for p in pages:
    s = p["schedule"]
    if s["header_words"] < MIN_HEADER_WORDS:
      continue
    across, down = s["across"], s["down"]
    if max(across, down) < 4:
      continue
    kind = "MARK_COLUMNS" if across > down else "MARK_ROWS"
    votes[kind] += 1
    ev.append({"page": p["page"], "layout": kind, "marks": s["across_marks"] if kind == "MARK_COLUMNS" else s["down_marks"]})
    
  if votes:
    value, share = _share(dict(votes))
    return _entry(value, share, ev, counts=dict(votes))
  drawn = sum(sum(p["sections"][k] for k in ("LETTER_PAIR", "NUMBER_PAIR", "X_SECTION")) for p in pages)
  if drawn >= MIN_SECTION_TITLES:
    return _entry("DRAWN_SECTIONS", min(1.0, drawn / 6.0), [{"section_titles": drawn}], counts={"section_titles": drawn})
  return _entry(None, 0.0, [], counts={})

def walls(pages: list, register: list | None = None) -> dict:
  if not register:
    return _entry(None, 0.0, [], reason="no register")
  arch = {r["page"] for r in register if r.get("role") == "PLAN" and r.get("discipline") in ARCH_DISCIPLINES}
  plans = [p for p in pages if p["page"] in arch and p["paths"]["paths"] >= PLAN_PATHS]
  hatch = sum(p["paths"]["hatch"] for p in plans)
  fills = sum(p["paths"]["wall_fills"] for p in plans)
  ev = [{"page": p["page"], "hatch": p["paths"]["hatch"], "wall_fills": p["paths"]["wall_fills"]} for p in plans if p["paths"]["hatch"] or p["paths"]["wall_fills"]]
  counts = {"plan_pages": len(plans), "hatch": hatch, "wall_fills": fills}
  
  if not plans:
    return _entry(None, 0.0, ev, counts=counts, reason="no architectural plan")
  if hatch >= WALL_HATCH_MIN and hatch >= fills:
    return _entry("HATCHED", hatch / max(hatch + fills, 1), ev, counts=counts)
  if fills >= WALL_FILL_MIN and fills > hatch:
    return _entry("FILLED", fills / max(hatch + fills, 1), ev, counts=counts)
  return _entry("LINES", 0.5, ev, counts=counts)

def labels(pages: list) -> dict:
  text = [p for p in pages if p["words"] >= OUTLINED_MAX_WORDS]
  outlined = [p for p in pages if p["words"] < OUTLINED_MAX_WORDS and p["paths"]["paths"] >= OUTLINED_MIN_PATHS]
  counts = {"TEXT": len(text), "OUTLINED": len(outlined)}
  ev = [{"page": p["page"], "words": p["words"], "paths": p["paths"]["paths"]} for p in outlined]
  if not text and not outlined:
    return _entry(None, 0.0, ev, counts=counts)
  value, share = _share(counts)
  return _entry(value, share, ev, counts=counts)

def title_block(pages: list) -> dict:
  groups: dict = {}
  for p in pages:
    groups.setdefault(p["page"] // PDF_SHIFT, []).append(p["zone"])
  keep: list = []
  for _g, zones in sorted(groups.items()):
    keep.extend(b for b in TZ.learn(zones) if b["side"] != "OTHER")
  side, share = TZ.side_of(keep)
  if not side or len(keep) < MIN_BLOCK_BOXES:
    return _entry(None, 0.0, [], boxes=[], pages=len(pages))
  return _entry(f"{side}_STRIP", share, [{"box": b["box"], "pages": f"{b['pages']} of {b['of']}", "text": b["top_text"], "constant": b["constant"]} for b in keep[:EVIDENCE_CAP]], boxes=keep, pages=len(pages))

def sheet_arrangement(pages: list, register: list | None) -> dict:
  if not register:
    return _entry(None, 0.0, [], reason="no register")
  count = Counter(r.get("discipline") for r in register if r.get("discipline"))
  big = sorted(d for d, n in count.items() if n >= DISCIPLINE_PAGES)
  ev = [{"discipline": d, "pages": n} for d, n in sorted(count.items())]
  if not count:
    return _entry(None, 0.0, ev, reason="no discipline read")
  return _entry("COMBINED" if len(big) >= 2 else "SEPARATE", 1.0 if len(big) != 1 or len(count) == 1 else 0.7, ev)

def scale(pages: list, register: list | None) -> dict:
  ratio_pages = [p["page"] for p in pages if p.get("scale_ratio_tokens")]
  if len(ratio_pages) < 2:
    return _entry("NONE", 0.8 if len(pages) >= 3 else 0.4, [{"pages_with_a_printed_ratio": len(ratio_pages)}])
  if not register:
    return _entry(None, 0.0, [{"pages_with_a_printed_ratio": len(ratio_pages)}], reason="printed, not checked: no register")
  basis = Counter(r.get("scale_basis") for r in register if r.get("page") in ratio_pages)
  checked = sum(n for b, n in basis.items() if b in CHECKED_SCALE)
  total = sum(basis.values())
  
  value = "PRINTED_TRUE" if total and checked / total >= 0.5 else None
  return _entry(value, checked / total if total else 0.0, [{"pages_with_a_printed_ratio": len(ratio_pages), "basis": dict(basis)}], reason=None if value else "a printed scale the reader could not check")

def legend(pages: list) -> dict:
  hit = [p for p in pages if p["legend"]]
  if hit:
    return _entry("PRESENT", 1.0, [{"page": p["page"], "text": p["legend_text"]} for p in hit])
  return _entry("ABSENT", 0.9 if len(pages) >= LEGEND_PAGES_FOR_ABSENT else 0.5, [{"pages": len(pages)}])

def section_titles(pages: list) -> dict:
  counts = {k: sum(p["sections"][k] for p in pages) for k in VALUES["section_titles"]}
  if sum(counts.values()) < MIN_SECTION_TITLES:
    return _entry(None, 0.0, [], counts=counts)
  value, share = _share(counts)
  return _entry(value, share, [{"form": k, "titles": n} for k, n in counts.items() if n], counts=counts)

def build(pages: list, register: list | None = None) -> dict:
  return {"points": {"units": units(pages), "bar_notation": bar_notation(pages), "schedule_layout": schedule_layout(pages), "walls": walls(pages, register), "labels": labels(pages),
    "title_block": title_block(pages), "sheet_arrangement": sheet_arrangement(pages, register), "scale": scale(pages, register), "legend": legend(pages), "section_titles": section_titles(pages)},
    "pages": len(pages)}

def values_of(profile: dict) -> dict:
  return {k: v["value"] for k, v in profile["points"].items()}
