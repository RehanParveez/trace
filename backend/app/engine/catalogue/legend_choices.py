"""The meanings a model may give a legend symbol: one entry for each kind of electrical point the reading has a work item for, read from legend_choices.yaml."""
from __future__ import annotations
import os
import yaml
import functools

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "legend_choices.yaml")
FIELDS = ("key", "about")

class LegendChoiceError(Exception):
  """Raised when the legend choices file is wrong or missing."""

@functools.lru_cache(maxsize=1)
def _raw() -> dict:
  """Reads the yaml file once."""
  with open(PATH, encoding="utf-8") as fh:
    data = yaml.safe_load(fh)
  if not isinstance(data, dict) or not isinstance(data.get("choices"), list):
    raise LegendChoiceError("legend_choices.yaml must hold a list of choices")
  return data

def problems(data: dict | None = None) -> list:
  """Lists what is wrong with the file: a missing field, a repeated key, a key that is not an electrical kind of the reading, or an electrical kind that has no choice."""
  from app.modules.drawings_boq.takeoff.extract import electrical_rules as ER
  data = data or _raw()
  out, seen = [], set()
  for e in data["choices"]:
    name = e.get("key", "?")
    out += [f"{name}: no {f}" for f in FIELDS if f not in e]
    out += [f"{name}: repeated"] if name in seen else []
    seen.add(name)
    out += [f"{name}: is not an electrical kind of the reading"] if name not in ER.GROUPS or name == ER.OTHER else []
  out += [f"{g}: has no choice" for g in ER.GROUPS if g != ER.OTHER and g not in seen]
  return out

def choices() -> tuple:
  """Gives every choice, as read."""
  bad = problems()
  if bad:
    raise LegendChoiceError("; ".join(bad[:5]))
  return tuple(_raw()["choices"])

def keys() -> tuple:
  """Gives the key of every choice."""
  return tuple(e["key"] for e in choices())

def discipline() -> str:
  """Gives the discipline the choices are for."""
  return str(_raw()["discipline"])
