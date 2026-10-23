from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import foundation as FD
from app.modules.drawings_boq.takeoff.extract import finishes as FN
from app.modules.drawings_boq.takeoff.extract import spec_facts as SF
from app.modules.drawings_boq.takeoff.extract import config as C

ITEM_OF = {"pcc": FD.FLOOR_PCC, "brick ballast": FD.FLOOR_BALLAST, "sand filling": FD.FLOOR_SAND_FILL}
TEXT = {FD.FLOOR_PCC: ("Plain concrete bed under the floor", "FLOOR-PCC"), FD.FLOOR_BALLAST: ("Brick ballast under the floor", "FLOOR-BALLAST"),
  FD.FLOOR_SAND_FILL: ("Sand filling under the floor", "FLOOR-SAND-FILL")}

def candidates(rooms: list, spec: dict | None, ctx: dict, level_hint: str | None, lv_spec, cls, finish) -> tuple:
  layers = (spec or {}).get("layers") or {}
  ambiguous = [a for a in ((spec or {}).get("layers_ambiguous") or []) if a["layer"] in ITEM_OF]
  stats = {"made": [], "left_out": [], "ambiguous": [a["layer"] for a in ambiguous]}
  
  notes: list = []
  total, used, pts = FN.room_total(rooms)
  if used == 0:
    return [], notes, stats
  out: list = []
  for name, item in ITEM_OF.items():
    lay = layers.get(name)
    if not lay:
      continue
  
    text, tag = TEXT[item]
    mix = lay.get("mix")
    facts = {"derived_from": "ROOMS", "room_count": used, "area_m2": round(total, 3), "layer": name, "thickness_mm": lay["value_mm"], "mix": mix,
      "spec_pages": lay.get("pages") or [], "spec_count": lay.get("count"), "spec_others": lay.get("others") or [], "spec_text": lay.get("text")}
    if item == FD.FLOOR_PCC and mix:
      facts["spec_grade"] = {"grade": mix, "what": "plain concrete bed", "pages": lay.get("pages") or []}
    label = f"{text} · {total:.2f} m² × {lay['value_mm'] / 25.4:g} in" + (f" ({mix})" if mix else "") + (f" · {lv_spec[0]}" if lv_spec else "")
    item_notes = [C.note("FLOOR_LAYER_FROM_SPEC", layer=name, thickness_mm=lay["value_mm"], pages=lay.get("pages") or [])]
    if lay.get("others"):
      item_notes.append(C.note("SPEC_VALUE_PRINTED_TWO_WAYS", layer=name, chosen_mm=lay["value_mm"], others=lay["others"]))
    out.append(FD._make(cls, ctx, finish, (item, level_hint or ""), item, label, tag, [FD._centre(pts)],
      {"length_mm": round(total * 1000.0, 1), "width_mm": 1000.0, "depth_mm": float(lay["value_mm"])}, [], item_notes, facts, 0.6))
    stats["made"].append(name)
    
  stats["left_out"] = sorted(n for n in layers if n not in ITEM_OF)
  if stats["left_out"]:
    notes.append(C.note("FLOOR_LAYERS_LEFT_OUT", layers=stats["left_out"]))
  if ambiguous:
    notes.append(C.note("FLOOR_LAYERS_AMBIGUOUS", layers=ambiguous))
  return out, notes, stats
