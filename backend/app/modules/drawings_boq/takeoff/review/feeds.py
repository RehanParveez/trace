from __future__ import annotations
import os
import functools
import yaml
from app.engine.catalogue import loader as CAT
from app.engine.catalogue import note_keys as NK
from app.engine.catalogue import schedule_kinds as SK
from app.modules.drawings_boq.takeoff.extract import electrical_rules as ER

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feeds.yaml")

@functools.lru_cache(maxsize=1)
def _raw() -> dict:
  with open(PATH, encoding="utf-8") as fh:
    return yaml.safe_load(fh)

def note_items(key: str) -> list:
  return list(_raw()["notes"].get(str(key).upper()) or [])

def schedule_items(kind: str) -> list:
  return list(_raw()["schedules"].get(str(kind).upper()) or [])

def legend_items(kind: str) -> list:
  return list(CAT.lines().get(ER.SEED_ITEM.get(str(kind).upper()), []))

def problems() -> list:
  data = _raw()
  have = {i.id for i in CAT.items()}
  out = []
  for section, known in (("notes", {e["key"] for e in NK.keys()}), ("schedules", {e["key"] for e in SK.kinds()})):
    out += [f"{section}: {k} is not a known key" for k in data[section] if k not in known]
    out += [f"{section}: {k} is not listed" for k in sorted(known) if k not in data[section]]
    out += [f"{section}.{k}: {i} is not a catalogue item" for k, ids in data[section].items() for i in ids if i not in have]
  return out
