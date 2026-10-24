from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import foundation as FD
from app.modules.drawings_boq.takeoff.extract import finishes as FN
from app.modules.drawings_boq.takeoff.extract import spec_facts as SF
from app.modules.drawings_boq.takeoff.extract import config as C

FLOOR_CS_BED = "FLOOR_CS_BED"
FLOOR_BRICK_TILES = "FLOOR_BRICK_TILES"
FLOOR_MUD_PLASTER = "FLOOR_MUD_PLASTER"
FLOOR_COMPACTED_MUD = "FLOOR_COMPACTED_MUD"
ROOF_PCC = "ROOF_PCC"
ROOF_BALLAST = "ROOF_BALLAST"
ROOF_SCREED = "ROOF_SCREED"
ROOF_MEMBRANE = "ROOF_MEMBRANE"
ROOF_POLYTHENE = "ROOF_POLYTHENE"
ITEMS = (FLOOR_CS_BED, FLOOR_BRICK_TILES, FLOOR_MUD_PLASTER, FLOOR_COMPACTED_MUD, ROOF_PCC, ROOF_BALLAST, ROOF_SCREED, ROOF_MEMBRANE, ROOF_POLYTHENE)
WORK_ITEM = {FLOOR_CS_BED: "FLR-CS-BED", FLOOR_BRICK_TILES: "FLR-BRICK-TILES", FLOOR_MUD_PLASTER: "FLR-MUD-PLASTER", FLOOR_COMPACTED_MUD: "FLR-COMPACTED-MUD",
  ROOF_PCC: "CON-PCC", ROOF_BALLAST: "FIN-ROOF-COBA", ROOF_SCREED: "FIN-ROOF-SCREED", ROOF_MEMBRANE: "FIN-ROOF-MEMBRANE", ROOF_POLYTHENE: "FIN-POLYTHENE"}
MODE = {FLOOR_CS_BED: "COUNT_X_AREA", FLOOR_BRICK_TILES: "COUNT_X_AREA", FLOOR_MUD_PLASTER: "COUNT_X_AREA", FLOOR_COMPACTED_MUD: "COUNT_X_VOLUME",
  ROOF_PCC: "COUNT_X_VOLUME", ROOF_BALLAST: "COUNT_X_VOLUME", ROOF_SCREED: "COUNT_X_AREA", ROOF_MEMBRANE: "COUNT_X_AREA", ROOF_POLYTHENE: "COUNT_X_AREA"}
ITEM_OF = {"pcc": FD.FLOOR_PCC, "brick ballast": FD.FLOOR_BALLAST, "sand filling": FD.FLOOR_SAND_FILL, "cement sand bed": FLOOR_CS_BED, "brick tiles": FLOOR_BRICK_TILES,
  "mud plaster": FLOOR_MUD_PLASTER, "compacted mud": FLOOR_COMPACTED_MUD}
TEXT = {FD.FLOOR_PCC: ("Plain concrete bed under the floor", "FLOOR-PCC"), FD.FLOOR_BALLAST: ("Brick ballast under the floor", "FLOOR-BALLAST"),
  FD.FLOOR_SAND_FILL: ("Sand filling under the floor", "FLOOR-SAND-FILL"), FLOOR_CS_BED: ("Cement-sand bed under the floor finish", "FLOOR-CS-BED"),
  FLOOR_BRICK_TILES: ("Brick tiles", "FLOOR-BRICK-TILES"), FLOOR_MUD_PLASTER: ("Mud plaster", "FLOOR-MUD-PLASTER"), FLOOR_COMPACTED_MUD: ("Compacted mud layer", "FLOOR-COMPACTED-MUD")}
ROOF_ITEM = {"pcc": ROOF_PCC, "brick ballast": ROOF_BALLAST, "cement sand bed": ROOF_SCREED, "brick tiles": FLOOR_BRICK_TILES, "mud plaster": FLOOR_MUD_PLASTER}
ROOF_TEXT = {ROOF_PCC: ("Plain concrete bed on the roof", "ROOF-PCC"), ROOF_BALLAST: ("Brick ballast on the roof", "ROOF-BALLAST"), ROOF_SCREED: ("Cement-sand bed on the roof", "ROOF-SCREED"),
  FLOOR_BRICK_TILES: ("Brick tiles on the roof", "ROOF-BRICK-TILES"), FLOOR_MUD_PLASTER: ("Mud plaster on the roof", "ROOF-MUD-PLASTER"),
  ROOF_MEMBRANE: ("Waterproofing on the roof", "ROOF-MEMBRANE"), ROOF_POLYTHENE: ("Polythene sheet on the roof", "ROOF-POLYTHENE")}
ROOF_WATERPROOF = {"waterproofing coat": (ROOF_MEMBRANE, "coat"), "polythene sheet": (ROOF_POLYTHENE, "layer")}
MIX_WHAT = {FD.FLOOR_PCC: "plain concrete bed", ROOF_PCC: "plain concrete bed", FLOOR_CS_BED: "cement-sand bed", ROOF_SCREED: "cement-sand bed"}

def mode_of(item: str) -> str:
  return MODE.get(item) or FD.MODE[item]

def _params(item: str, area_m2: float, thickness_mm: float) -> dict:
  """A bed, a fill or a ballast is a volume (area times its thickness); tiles, plaster and a bed that is priced by the area are an area, and the thickness stays in the label and the facts."""
  out = {"length_mm": round(area_m2 * 1000.0, 1), "width_mm": 1000.0}
  if mode_of(item) == "COUNT_X_VOLUME":
    out["depth_mm"] = float(thickness_mm)
  return out

def _layer(cls, ctx: dict, finish, key_parts: tuple, item: str, label: str, tag: str, points: list, params: dict, notes: list, facts: dict, base: float):
  if item in FD.MODE:
    return FD._make(cls, ctx, finish, key_parts, item, label, tag, points, params, [], notes, facts, base)
  cand = cls(key=FD._key_of(key_parts), category="WALL", kind="COUNT", quantity_mode=MODE[item], label=label, tag=tag, geometry={"points": points},
    params={**params, "dims_basis": "SPECIFIED"}, missing=[], work_item=WORK_ITEM[item], status="VALID", confidence=0.0, facts={**facts, "foundation_item": item}, notes=notes,
    source="VECTOR_SNAP", count=1)
  return finish(cand, ctx, base)

def candidates(rooms: list, spec: dict | None, ctx: dict, level_hint: str | None, lv_spec, cls, finish) -> tuple:
  head = SF.floor_set(spec, level_hint)
  under = head["heading"] if head else None
  layers = head["layers"] if head else (spec or {}).get("layers") or {}
  ambiguous = [a for a in ((head["layers_ambiguous"] if head else (spec or {}).get("layers_ambiguous")) or []) if a["layer"] in ITEM_OF]
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
      "spec_pages": lay.get("pages") or [], "spec_count": lay.get("count"), "spec_others": lay.get("others") or [], "spec_text": lay.get("text"), "spec_heading": under}
    
    if mix and item in MIX_WHAT:
      facts["spec_grade"] = {"grade": mix, "what": MIX_WHAT[item], "pages": lay.get("pages") or []}
    label = f"{text} · {total:.2f} m² × {lay['value_mm'] / 25.4:g} in" + (f" ({mix})" if mix else "") + (f" · {lv_spec[0]}" if lv_spec else "")
    item_notes = [C.note("FLOOR_LAYER_UNDER_HEADING", layer=name, thickness_mm=lay["value_mm"], heading=under, pages=lay.get("pages") or []) if under
                  
      else C.note("FLOOR_LAYER_FROM_SPEC", layer=name, thickness_mm=lay["value_mm"], pages=lay.get("pages") or [])]
    if lay.get("others"):
      item_notes.append(C.note("SPEC_VALUE_PRINTED_TWO_WAYS", layer=name, chosen_mm=lay["value_mm"], others=lay["others"]))
    out.append(_layer(cls, ctx, finish, (item, level_hint or ""), item, label, tag, [FD._centre(pts)], _params(item, total, lay["value_mm"]), item_notes, facts, 0.6))
    stats["made"].append(name)
    
  stats["left_out"] = sorted(n for n in layers if n not in ITEM_OF)
  if stats["left_out"]:
    notes.append(C.note("FLOOR_LAYERS_LEFT_OUT", layers=stats["left_out"]))
  if ambiguous:
    notes.append(C.note("FLOOR_LAYERS_AMBIGUOUS", layers=ambiguous))
  return out, notes, stats

def roof_heading(facts: dict) -> str:
  """The roof heading of the specification block that belongs to a roof item: the main roof under a roof plan is the terrace, the roof of the roof plan is the roof."""
  if facts.get("roof_role") == "MAIN_ROOF":
    return "TERRACE"
  return "ROOF" if facts.get("roof_floor") == "ROOF" else "TERRACE"

def _roof_item(cls, ctx: dict, finish, roof, head: dict, name: str, item: str, text: str, tag: str, thickness_mm: float | None, mix: str | None, lay: dict, area: float) -> object:
  f = roof.facts or {}
  facts = {"derived_from": "SLAB", "slab_key": f.get("slab_key"), "roof_key": roof.key, "roof_floor": f.get("roof_floor"), "area_m2": round(area, 3), "layer": name, "layer_of": "ROOF",
    "thickness_mm": thickness_mm, "mix": mix, "spec_pages": lay.get("pages") or [], "spec_count": lay.get("count"), "spec_heading": head["heading"]}
  if mix and item in MIX_WHAT:
    facts["spec_grade"] = {"grade": mix, "what": MIX_WHAT[item], "pages": lay.get("pages") or []}
  label = f"{text} · {area:.2f} m²" + (f" × {thickness_mm / 25.4:g} in" if thickness_mm else "") + (f" ({mix})" if mix else "")
  note = C.note("ROOF_LAYER_UNDER_HEADING", layer=name, thickness_mm=thickness_mm, heading=head["heading"], pages=lay.get("pages") or [])
  pts = list((roof.geometry or {}).get("points") or [[0.0, 0.0]])[:1]
  return _layer(cls, ctx, finish, (item, "ROOF-LAYER", roof.key, name), item, label, tag, pts, _params(item, area, thickness_mm or 0.0), [note], facts, 0.6)

def roof_candidates(roofs: list, spec_facts: dict | None, ctx: dict, cls, finish) -> tuple:
  """The layers printed under a roof heading, as items over the area of each roof item: the bed, the ballast, the tiles, the plaster, the polythene and the coats."""
  sets = {s["key"]: s for s in SF.roof_sets(spec_facts)}
  stats: dict = {"made": [], "left_out": [], "not_tied": [], "unused": []}
  out: list = []
  notes: list = []
  used: set = set()
  for roof in roofs:
    f = roof.facts or {}
    area = float(f.get("area_m2") or 0.0)
    
    if f.get("roof_part") == "PROJECTION" or area <= 0.0 or not sets:
      continue
    head = sets.get(roof_heading(f))
    if head is None and len(sets) == 1:
      head = next(iter(sets.values()))
    if head is None:
      stats["not_tied"].append(roof.key)
      notes.append(C.note("ROOF_LAYERS_NOT_TIED", floor=f.get("roof_floor"), headings=[s["heading"] for s in sets.values()]))
      continue
    
    used.add(head["key"])
    for lay in head["layers"]:
      item = ROOF_ITEM.get(lay["layer"])
      if item is None:
        stats["left_out"].append(lay["layer"])
        continue
      text, tag = ROOF_TEXT[item]
      out.append(_roof_item(cls, ctx, finish, roof, head, lay["layer"], item, text, tag, lay["value_mm"], lay.get("mix"), lay, area))
      stats["made"].append(lay["layer"])
    for wp in head["waterproof"]:
      pair = ROOF_WATERPROOF.get(wp.get("material"))
      if pair is None or not wp.get("layers"):
        continue

      item, unit = pair
      text, tag = ROOF_TEXT[item]
      row = _roof_item(cls, ctx, finish, roof, head, wp["material"], item, f"{text} ({wp['layers']} {unit}{'s' if wp['layers'] != 1 else ''})", tag, None, None, wp, area)
      row.facts["layers"] = int(wp["layers"])
      row.facts["layer_unit"] = unit
      out.append(row)
      stats["made"].append(wp["material"])

    if head["ambiguous"]:
      notes.append(C.note("FLOOR_LAYERS_AMBIGUOUS", layers=head["ambiguous"]))
  stats["unused"] = sorted(k for k in sets if k not in used)
  if stats["unused"] and used:
    notes.append(C.note("ROOF_LAYERS_NOT_USED", headings=[sets[k]["heading"] for k in stats["unused"]]))
  if stats["left_out"]:
    notes.append(C.note("FLOOR_LAYERS_LEFT_OUT", layers=sorted(set(stats["left_out"]))))
  return out, notes, stats
