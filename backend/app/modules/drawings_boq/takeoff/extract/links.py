from __future__ import annotations

LINKED, CHOICE, PARTLY, NOT_LINKED = "LINKED", "CHOICE", "PARTLY", "NOT_LINKED"
GROUPS = ("BEAM", "PLINTH_BEAM", "FOOTING_STRIP", "FOOTING_PAD", "NECK_COLUMN", "COLUMN", "TANK")
STRIP_ITEMS = ("TRENCH", "PCC_STRIP", "TERMITE_STRIP", "BRICK_STEP", "RCC_STRIP")
MAX_ITEMS = 500

def _codes(row) -> set:
  return {n.get("code") for n in (row.notes or []) if isinstance(n, dict)} if hasattr(row, "notes") else set()

def group_of(row) -> str | None:
  f = row.facts or {}
  
  if row.category == "BEAM":
    return "PLINTH_BEAM" if f.get("beam_role") == "PLINTH" or str(row.tag or "").upper().startswith(("PLINTH", "PB", "GB")) else "BEAM"
  if row.category == "FOOTING":
    return "FOOTING_PAD"
  if row.category == "COLUMN":
    return "NECK_COLUMN" if f.get("neck_of") else "COLUMN"
  if row.category == "WALL" and f.get("foundation_item") in STRIP_ITEMS:
    return "FOOTING_STRIP"
  if row.category == "SITE" and f.get("tank_kind"):
    return "TANK"
  return None

def _missing(row) -> list:
  return list(row.missing or [])

def link_of(row) -> dict:
  """-> {"status", "detail", "how", "needs", "reason"}."""
  g, f, p = group_of(row), row.facts or {}, row.params or {}
  miss = _missing(row)
  codes = _codes(row)
  
  if g in ("BEAM", "PLINTH_BEAM"):
    if f.get("section_mark") and p.get("depth_mm"):
      how = "MARK" if "BEAM_SECTION_FROM_MARK" in codes else "CHOSEN" if f.get("section_chosen") or (f.get("conflict") or {}).get("kind") == "BEAM_SECTION" else "ASSUMED" if f.get("section_assumed") else "ONLY_SECTION"
      return {"status": LINKED, "detail": f["section_mark"], "how": how, "needs": [], "reason": None}
    if f.get("section_options"):
      return {"status": CHOICE, "detail": ", ".join(o.get("mark") for o in f["section_options"] if o.get("mark")), "how": None, "needs": ["depth_mm"],
        "reason": "SECTIONS_LISTED_NOT_TIED_TO_WALLS"}
      
    if p.get("depth_mm"):
      return {"status": LINKED, "detail": None, "how": "TYPED", "needs": [], "reason": None}
    return {"status": NOT_LINKED, "detail": None, "how": None, "needs": ["depth_mm"], "reason": "NO_SECTION_PRINTED_FOR_THIS_BEAM"}
  if g == "FOOTING_STRIP":
    if f.get("footing_section"):
      return {"status": LINKED, "detail": (f["footing_section"] or {}).get("caption"), "how": "SECTION", "needs": [], "reason": None}
    return {"status": NOT_LINKED, "detail": None, "how": None, "needs": miss, "reason": "NO_USABLE_FOOTING_SECTION_FOR_THIS_WALL"}
  if g == "FOOTING_PAD":
    sized = bool(f.get("size_detail_mm") or "SIZE_FROM_DETAIL" in codes or "SIZE_FROM_SCHEDULE" in codes)
    if "depth_mm" in miss:
      return {"status": PARTLY if sized else NOT_LINKED, "detail": f.get("tag") if sized else None, "how": "DETAIL" if sized else None, "needs": ["depth_mm"],
        "reason": "FOOTING_DEPTH_NOT_PRINTED_AS_A_NUMBER"}
    return {"status": LINKED, "detail": f.get("tag"), "how": "DETAIL" if sized else "TYPED", "needs": [], "reason": None}

  if g == "NECK_COLUMN":
    if "height_mm" in miss:
      return {"status": NOT_LINKED, "detail": f.get("neck_of"), "how": None, "needs": ["height_mm"], "reason": "NECK_HEIGHT_FOLLOWS_FOOTING_DEPTH"}
    return {"status": LINKED, "detail": f.get("neck_of"), "how": "FOOTING", "needs": [], "reason": None}
  if g == "COLUMN":
    if f.get("size_detail_mm") or codes & {"SIZE_FROM_COLUMN_DETAIL", "SIZE_FROM_DETAIL", "SIZE_FROM_SCHEDULE"}:
      return {"status": LINKED, "detail": f.get("tag"), "how": "DETAIL", "needs": [], "reason": None}
    return {"status": NOT_LINKED if miss else LINKED, "detail": None, "how": None if miss else "PLAN", "needs": miss, "reason": "NO_DETAIL_FOUND_FOR_THIS_MARK" if miss else None}

  if g == "TANK":
    n_pics = len(f.get("tank_drawings") or [])
    sizes = [k for k in ("length_mm", "width_mm", "height_mm", "thickness_mm") if p.get(k)]
    if miss:
      return {"status": PARTLY if sizes else NOT_LINKED, "detail": f"{n_pics} drawing(s) listed" if n_pics else None, "how": "PRINTED_SIZE" if sizes else None,
        "needs": miss, "reason": "TANK_DRAWINGS_NOT_USED_FOR_SIZES"}
    return {"status": LINKED, "detail": f"{n_pics} drawing(s) listed" if n_pics else None, "how": "PRINTED_SIZE", "needs": [], "reason": None}
  return {"status": NOT_LINKED, "detail": None, "how": None, "needs": miss, "reason": "UNKNOWN"}

def report(rows: list) -> dict:
  tally = {g: {"group": g, "total": 0, LINKED: 0, CHOICE: 0, PARTLY: 0, NOT_LINKED: 0} for g in GROUPS}
  
  items: list = []
  for r in rows:
    if r.decision == "REJECTED":
      continue
    g = group_of(r)
    if g is None:
      continue
  
    lk = link_of(r)
    tally[g]["total"] += 1
    tally[g][lk["status"]] += 1
    items.append({"id": str(r.id), "group": g, "tag": r.tag, "label": r.label, "floor": (r.facts or {}).get("floor") or (r.facts or {}).get("level_hint"), "decision": r.decision, **lk})
  order = {NOT_LINKED: 0, CHOICE: 1, PARTLY: 2, LINKED: 3}
  items.sort(key=lambda i: (order[i["status"]], GROUPS.index(i["group"]), str(i["tag"] or "")))
  out_groups = [{"group": g["group"], "total": g["total"], "linked": g[LINKED], "choice": g[CHOICE], "partly": g[PARTLY], "not_linked": g[NOT_LINKED]} for g in tally.values() if g["total"]]
  return {"groups": out_groups, "items": items[:MAX_ITEMS], "truncated": len(items) > MAX_ITEMS, "open": sum(1 for i in items if i["status"] != LINKED)}
