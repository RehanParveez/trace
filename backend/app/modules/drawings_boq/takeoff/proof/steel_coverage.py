from __future__ import annotations
from app.engine.measure.member_steel import BAR_ROLES, clean_steel

KINDS = ("BEAM", "LINTEL", "COLUMN", "FOOTING", "SLAB", "CHAJJA", "BALCONY_SLAB", "RCC_WALL", "STAIR", "TANK", "PARAPET")
NO_SECTION_JOINED, SECTION_HAS_NO_BARS, BARS_UNREADABLE = "NO_SECTION_JOINED", "SECTION_HAS_NO_BARS", "BARS_UNREADABLE"
MAIN_BARS_NOT_READ = "MAIN_BARS_NOT_READ"

REASON_TEXT = {
  NO_SECTION_JOINED: "no section, schedule row or note was joined to the member",
  SECTION_HAS_NO_BARS: "a section was joined to the member but no bars were read from it",
  BARS_UNREADABLE: "bars are printed with the member (a note, a string, a panel) but could not be tied to it",
  MAIN_BARS_NOT_READ: "rings were read but no main bars: the member is counted from its rings alone",
}

LINTEL_ROW_AS_PRINTED, SECTION_ASSUMED, SHORT_NECK_ANCHORAGE = "LINTEL_ROW_AS_PRINTED", "SECTION_ASSUMED", "SHORT_NECK_ANCHORAGE"
MATCHES_SECTION, DIFFERS_FROM_SECTION, NO_SECTION_TO_COMPARE = "MATCHES_SECTION", "DIFFERS_FROM_SECTION", "NO_SECTION_TO_COMPARE"

VERDICT_TEXT = {
  MAIN_BARS_NOT_READ: "only the rings were read; the main bars of the section are not in the reading (reader gap), so the figure is a lower bound",
  LINTEL_ROW_AS_PRINTED: "the bars are the lintel row or detail as printed; the usual band is the beam band and does not describe a lintel: band flagged, bars kept",
  SECTION_ASSUMED: "the bars belong to the principal section, taken because no section is tied to this member by mark: bars flagged, band kept",
  SHORT_NECK_ANCHORAGE: "a short neck column: the anchorage added at both ends is large against its height: bars as printed, band flagged",
  MATCHES_SECTION: "the bars equal the section joined by mark; the member sits outside the band with its printed bars: band flagged for review",
  DIFFERS_FROM_SECTION: "the bars differ from the section joined by mark: the reader or the join is wrong, to be fixed",
  NO_SECTION_TO_COMPARE: "no section is joined to compare with: flagged for review",
}

def _main(steel: dict | None) -> bool:
  return any(steel.get(r) for r in BAR_ROLES) if steel else False

def _steel(c: dict) -> dict | None:
  return clean_steel((c.get("params") or {}).get("steel")) or None

def reason(c: dict) -> str | None:
  steel = _steel(c)
  if _main(steel):
    return None
  f = c.get("facts") or {}
  if steel:
    return MAIN_BARS_NOT_READ
  panel = f.get("panel_steel") or {}
  
  if f.get("steel_text") or f.get("steel_source") or (panel.get("strings") or 0) > 0:
    return BARS_UNREADABLE
  if f.get("section_mark") or f.get("section_options"):
    return SECTION_HAS_NO_BARS
  return NO_SECTION_JOINED

def verdict(row: dict, c: dict | None) -> str:
  src = ((row.get("trace") or {}).get("inputs") or {}).get("steel_source") or {}
  steel = clean_steel(src.get("steel")) or None
  
  if not _main(steel):
    return MAIN_BARS_NOT_READ
  cat = src.get("category")
  f = (c or {}).get("facts") or {}
  if cat == "LINTEL":
    return LINTEL_ROW_AS_PRINTED
  if f.get("section_assumed"):
    return SECTION_ASSUMED
  if f.get("neck_of") or (f.get("foundation_piece") or {}).get("role") == "NECK":
    return SHORT_NECK_ANCHORAGE
  mark = f.get("section_mark")
  
  sec = [o for o in f.get("section_options") or [] if mark and o.get("mark") == mark and o.get("steel")]
  if sec:
    same = all(clean_steel(sec[0]["steel"]).get(r) == steel.get(r) for r in BAR_ROLES)
    return MATCHES_SECTION if same else DIFFERS_FROM_SECTION
  return NO_SECTION_TO_COMPARE

def _find(cands: list, src: dict) -> dict | None:
  size = [round(float(x)) for x in src.get("size_mm") or []]
  for c in cands:
    p = c.get("params") or {}
    if c.get("category") == src.get("category") and c.get("tag") == src.get("tag") and size == [round(float(p.get(k) or 0)) for k in ("length_mm", "width_mm", "depth_mm")]:
      return c
  for c in cands:
    if c.get("category") == src.get("category") and c.get("tag") == src.get("tag"):
      return c
  return None

def coverage(cands: list, ledger: list) -> dict:
  accepted = [c for c in cands if c.get("decision") == "ACCEPTED" and c.get("category") in KINDS]
  kinds: dict = {}
  
  for c in accepted:
    k = kinds.setdefault(c["category"], {"members": 0, "printed": 0, "rings_only": 0, "band": 0, "reasons": {}})
    n = int(c.get("count") or 1)
    k["members"] += n
    why = reason(c)
    if why is None:
      k["printed"] += n
      continue
    if why == MAIN_BARS_NOT_READ:
      k["rings_only"] += n
    else:
      k["band"] += n
    k["reasons"][why] = k["reasons"].get(why, 0) + n
    
  rows = [r for r in ledger if (r.get("work_item_code") or "") == "STL-REBAR"]
  kg_printed = kg_band = waste = kg_main = 0.0
  
  for r in rows:
    q = float(r.get("quantity") or 0.0)
    pct = float(((r.get("spec") or {}).get("params") or {}).get("steel_wastage_pct") or 0.0)
    waste += q - q / (1 + pct / 100.0)
    if "STEEL_ESTIMATED" in (r.get("warnings") or ()):
      kg_band += q
    else:
      kg_printed += q
      if _main(clean_steel((((r.get("trace") or {}).get("inputs") or {}).get("steel_source") or {}).get("steel")) or None):
        kg_main += q
  total = kg_printed + kg_band
  outside: list = []
  
  for r in rows:
    if "STEEL_OUTSIDE_BAND" not in (r.get("warnings") or ()):
      continue
    src = ((r.get("trace") or {}).get("inputs") or {}).get("steel_source") or {}
    conc = float(src.get("concrete_m3") or 0.0)
    outside.append({"category": src.get("category"), "tag": src.get("tag"), "kg_per_m3": round(float(src.get("bare_kg") or 0.0) / conc, 1) if conc else None, "verdict": verdict(r, _find(accepted, src))})
  by_verdict: dict = {}
  for o in outside:
    slot = by_verdict.setdefault(o["verdict"], {"rows": 0, "categories": {}})
    slot["rows"] += 1
    slot["categories"][o["category"]] = slot["categories"].get(o["category"], 0) + 1
    
  return {"kinds": {k: kinds[k] for k in KINDS if k in kinds}, "members": sum(v["members"] for v in kinds.values()), "printed": sum(v["printed"] for v in kinds.values()),
    "printed_kg": round(kg_printed, 1), "band_kg": round(kg_band, 1), "printed_share_pct": round(100.0 * kg_printed / total, 1) if total else None,
    "main_bars_kg": round(kg_main, 1), "main_bars_share_pct": round(100.0 * kg_main / total, 1) if total else None,
    "waste_kg": round(waste, 1), "waste_pct": sorted({float(((r.get("spec") or {}).get("params") or {}).get("steel_wastage_pct") or 0.0) for r in rows}),
    "unexplained": sum(v["members"] - v["printed"] - sum(v["reasons"].values()) for v in kinds.values()),
    "outside_band": {"rows": len(outside), "by_verdict": dict(sorted(by_verdict.items())), "unresolved": sum(1 for o in outside if o["verdict"] == DIFFERS_FROM_SECTION)}}

def lines(cov: dict) -> list:
  out = [f"**Steel coverage** (not part of the hash): {cov['printed']} of {cov['members']} accepted members have main bars read from the drawing; {cov['printed_kg']:,} kg of the {cov['printed_kg'] + cov['band_kg']:,.1f} kg "
    f"({cov['printed_share_pct']}%) come from printed bars and {cov['band_kg']:,} kg from the usual band; {cov['main_bars_kg']:,} kg ({cov['main_bars_share_pct']}%) are from members whose main bars were read, the rest of the printed kg being rings alone. Waste is inside every row; its own line is {cov['waste_kg']:,} kg at {', '.join(f'{p:g}' for p in cov['waste_pct'])} % (rule steel_wastage_pct).", "",
    "| Kind | Members | Main bars read | Rings only | On the band | Why no main bars |", "|---|---|---|---|---|---|"]
  for kind, v in cov["kinds"].items():
    out.append(f"| {kind} | {v['members']} | {v['printed']} | {v['rings_only']} | {v['band']} | " + ("; ".join(f"{k} {n}" for k, n in sorted(v["reasons"].items())) or "") + " |")
    
  ob = cov["outside_band"]
  if ob["rows"]:
    out += ["", f"Outside the usual band: {ob['rows']} steel rows, {ob['unresolved']} unresolved (bars differ from their section). " + "; ".join(
      f"{k} {v['rows']} ({', '.join(f'{c} {n}' for c, n in sorted(v['categories'].items()))})" for k, v in ob["by_verdict"].items()) + "."]
  return out + [""]
