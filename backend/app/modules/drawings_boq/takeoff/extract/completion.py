from __future__ import annotations
import hashlib
import re
from app.modules.drawings_boq.takeoff.extract import walls as W
from app.modules.drawings_boq.takeoff.extract import config as C

RCC_NOTE = re.compile(r"(?P<t>\d{1,2}(?:\.\d)?)\s*[\"”″']{0,2}\s*THICK\s+R\.?\s?C\.?\s?C\.?\s+WALLS?", re.I)

def rcc_notes(lines: list) -> list:
  """The notes of a sheet that name a concrete wall and its thickness, such as 9" Thick R.c.c Wall: [{"text", "thickness_in", "x", "y"}]."""
  out = []
  for ln in lines:
    m = RCC_NOTE.search(ln.text or "")
    if not m:
      continue
    x, y = ln.locate(0, len(ln.text))
    out.append({"text": ln.text.strip(), "thickness_in": float(m.group("t")), "x": round(x, 2), "y": round(y, 2)})
  return out

def _key(*parts) -> str:
  return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:16]

def candidates(ring: dict | None, notes: list, heights: dict, ctx: dict, imperial: bool, Candidate, finish, height_note) -> list:
  """One wall candidate per stretch of the ring that carries no solid strip. Nothing is listed when the sheet has no note that calls a wall concrete."""
  if not ring or not ring.get("pieces") or not notes:
    return []
  out = []
  
  h = (heights or {}).get("WALL")
  for piece in ring["pieces"]:
    std, use_t = W.snap_thickness(piece["t_mm"], imperial)
    cc_m = piece["length_mm"] / 1000.0
    params = {"thickness_mm": use_t, "dims_basis": "SPECIFIED" if h else "DRAWN"}
    missing = []
    cnotes = [C.note("RCC_WALL_COMPLETES_ENCLOSURE", side=piece["side"], drawn_share=ring["sides"].get(piece["side"]), note_count=len(notes))]
    if h:
      params["height_mm"] = h["mm"]
      cnotes.append(height_note(h))
      
    else:
      missing.append("height_mm")
    facts = {"thickness_mm": round(piece["t_mm"], 1), "thickness_standard_mm": std, "thickness_used_mm": use_t, "length_cc_m": round(cc_m, 3),
      "length_clear_m": round(cc_m, 3), "gaps_mm": [], "ends": ["FREE", "FREE"], "method": "CENTRE_LINE", "construction": "RCC", "gap_pts": [],
      "enclosure_completion": True, "ring_side": piece["side"], "ring_sides_drawn": ring["sides"],
      "rcc_notes": [{"text": n["text"], "thickness_in": n["thickness_in"]} for n in notes[:6]]}
    p0, p1 = piece["p0"], piece["p1"]
    cand = Candidate(key=_key("WALL", "RING", round(p0[0] / 2), round(p0[1] / 2), round(p1[0] / 2), round(p1[1] / 2)), category="WALL", kind="LENGTH",
      quantity_mode="LENGTH_X_HEIGHT_X_THICKNESS", label=f"RCC wall to close the basement ({piece['side']} side) {use_t:g} mm · {cc_m:.2f} m", tag=None,
      geometry={"points": [[round(p0[0], 4), round(p0[1], 4)], [round(p1[0], 4), round(p1[1], 4)]], "closed": False}, params=params, missing=missing,
      work_item="CON-RCC", status="VALID", confidence=0.0, facts=facts, notes=cnotes, source="VECTOR_SNAP", count=1)
    out.append(finish(cand, ctx, 0.5))
  return out
