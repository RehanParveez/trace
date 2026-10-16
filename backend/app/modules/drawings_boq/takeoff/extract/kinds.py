from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import foundation as FD
from app.modules.drawings_boq.takeoff.extract import finishes as FN
from app.modules.drawings_boq.takeoff.extract import site_items as SI
from app.modules.drawings_boq.takeoff.extract import config as C

ITEM_KINDS = tuple(dict.fromkeys((*FD.ITEMS, *FN.ITEMS, *SI.SITE_KINDS)))
KINDS = (*C.CATEGORIES, *ITEM_KINDS)
DEFAULT_CODE = {**FD.WORK_ITEM, **FN.WORK_ITEM, **SI.WORK_ITEM}

def kind_of(cand) -> str:
  """The category of the item, or the name of the piece of work for the items that are not drawn on the plan."""
  facts = getattr(cand, "facts", None) or {}
  item = facts.get("site_kind") if cand.category == "SITE" else facts.get("foundation_item")
  return item if item in ITEM_KINDS else cand.category

def default_code(cand) -> str | None:
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
