from __future__ import annotations
import functools
import os
import yaml

SOURCES = ("drawing", "choice", "site", "qs", "standard", "seed", "user")
DRAWN = ("drawing", "user")
LABELS = {
  "user": "user", "element": "user", "drawing": "drawing", "material_text": "drawing", "printed": "drawing", "label": "drawing", "claim": "drawing", "detected": "drawing",
  "project": "choice", "choice": "choice", "decision": "choice", "answer": "choice", "site": "site", "convention": "qs", "qs": "qs", "company": "qs",
  "standard": "standard", "default": "seed", "assumed_masonry": "seed", "proposed": "seed", "seed": "seed",
}
CAP = 12
RECIPE_SPECS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "catalogue", "recipe_specs.yaml")

def normalise(label) -> tuple:
  key = str(label or "").strip().lower()
  if key in LABELS:
    return LABELS[key], True
  return "seed", False

def from_spec(spec) -> list:
  if not isinstance(spec, dict):
    return []
  basis = spec.get("basis")
  if not isinstance(basis, dict):
    return []
  params = spec.get("params") if isinstance(spec.get("params"), dict) else {}
  out = []
  for name, label in basis.items():
    if name == "steps" or isinstance(label, (dict, list)):
      continue
    value = params.get(name, spec.get(name))
    out.append({"param": str(name), "value": value if isinstance(value, (int, float, str, bool)) or value is None else str(value), "source": normalise(label)[0]})
  return out

def merge(groups: list) -> list:
  seen, out = set(), []
  for g in groups:
    for i in g or []:
      k = (i["param"], i["source"], str(i.get("value")))
      if k not in seen:
        seen.add(k)
        out.append(dict(i))
  return out[:CAP]

def assumed(inputs: list | None) -> bool:
  return any(i.get("source") not in DRAWN for i in inputs or [])

def unknown_labels(spec) -> list:
  if not isinstance(spec, dict) or not isinstance(spec.get("basis"), dict):
    return []
  return sorted({str(v) for k, v in spec["basis"].items() if k != "steps" and not isinstance(v, (dict, list)) and not normalise(v)[1]})

@functools.lru_cache(maxsize=1)
def _specs() -> dict:
  with open(RECIPE_SPECS, encoding="utf-8") as fh:
    return {s["item"]: s for s in (yaml.safe_load(fh) or {}).get("specs") or []}

def recipe_inputs(line: dict, by_family: dict) -> list:
  spec = _specs().get(line.get("item")) or {}
  base = [by_family.get(f) or [] for f in spec.get("base") or []]
  return merge(base + [[{"param": f"recipe:{line.get('recipe') or spec.get('recipe') or '?'}", "value": None, "source": "seed"}]])
