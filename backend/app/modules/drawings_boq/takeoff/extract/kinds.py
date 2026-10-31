from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import foundation as FD
from app.modules.drawings_boq.takeoff.extract import finishes as FN
from app.modules.drawings_boq.takeoff.extract import site_items as SI
from app.modules.drawings_boq.takeoff.extract import floor_layers as FLL
from app.modules.drawings_boq.takeoff.extract import boundary as BDY
from app.modules.drawings_boq.takeoff.extract import staging as STG
from app.modules.drawings_boq.takeoff.extract import drainage as DR
from app.modules.drawings_boq.takeoff.extract import electrical as EL
from app.modules.drawings_boq.takeoff.extract import outdoor as OD
from app.modules.drawings_boq.takeoff.extract import config as C

ITEM_KINDS = tuple(dict.fromkeys((*FD.ITEMS, *FN.ITEMS, *FLL.ITEMS, *BDY.ITEMS, *STG.ITEMS, *DR.ITEMS, *EL.ITEMS, *SI.SITE_KINDS, *OD.ITEMS)))
KINDS = (*C.CATEGORIES, *ITEM_KINDS)
DEFAULT_CODE = {**FD.WORK_ITEM, **FN.WORK_ITEM, **FLL.WORK_ITEM, **BDY.WORK_ITEM, **STG.WORK_ITEM, **DR.WORK_ITEM, **EL.WORK_ITEM, **SI.WORK_ITEM, **OD.WORK_ITEM}

def kind_of(cand) -> str:
  """The category of the item, or the name of the piece of work for the items that are not drawn on the plan."""

  facts = getattr(cand, "facts", None) or {}
  item = facts.get("site_kind") if cand.category == "SITE" else facts.get("foundation_item")
  return item if item in ITEM_KINDS else cand.category

BEAM_ROLES = {"PLINTH": "PLINTH_BEAM", "ROOF": "ROOF_BEAM", "BAND": "TIE_BAND"}
FACE_ROLES = {"PLASTER_INSIDE": "FACE_IN", "PAINT_INSIDE": "FACE_IN", "PLASTER_OUTSIDE": "FACE_OUT", "PAINT_OUTSIDE": "FACE_OUT"}

def role_of(cand) -> str:
  f = getattr(cand, "facts", None) or {}
  item, cat = f.get("foundation_item"), cand.category
  if cat == "FOOTING":
    return "FOOTING"
  if cat == "COLUMN":
    return "NECK" if f.get("neck_of") is not None or f.get("neck_assumed") is not None else "COLUMN"
  if cat == "BEAM":
    return BEAM_ROLES.get(f.get("beam_role"), "")
  if cat == "LINTEL":
    return "LINTEL"
  if item == "RCC_STRIP":
    return "PLINTH_BEAM"
  return FACE_ROLES.get(item, "")

def default_code(cand) -> str | None:
  """The work item the reader proposes for the kind of this item (the code stored on a sheet read before the code existed is out of date)."""
  """The work item the reader proposes for the kind of this item (the code stored on a sheet read before the code existed is out of date)."""
  return getattr(cand, "suggested_work_item", None) or DEFAULT_CODE.get(kind_of(cand)) or (C.SUGGESTIONS.get(cand.category) or (None,))[0]

def code_for(cand, given: dict) -> str | None:
  """The work item for an item: the one the person chose for its kind, otherwise the proposed one."""
  return (given or {}).get(kind_of(cand)) or default_code(cand)

def drop_unknown_codes(found: list, catalog: dict) -> int:
  """A proposed work item that is not in this catalog is taken off the item, and the item says so; the person chooses one when accepting."""
  n = 0
  for c in found:
    if c.work_item and c.work_item not in catalog:
      c.work_item = None
      n += 1
      if not any(x.get("code") == "NO_WORK_ITEM" for x in c.notes):
        c.notes.append(C.note("NO_WORK_ITEM"))
  return n
