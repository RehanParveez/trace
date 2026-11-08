from __future__ import annotations
import functools
import os
import yaml
from app.engine.catalogue import loader as CAT
from app.engine.catalogue import model as CM

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conventions_pk.yaml")
QS_CONVENTION, TRACE_SEED, STANDARD = "QS_CONVENTION", "TRACE_SEED", "STANDARD"
SOURCE_LABELS = {QS_CONVENTION: "QS convention v1, 2026", TRACE_SEED: "Trace seed, unsourced"}
SOURCE_KINDS = (QS_CONVENTION, TRACE_SEED, STANDARD)
UNITS = ("mm", "percent", "kg_per_m2")
EFFECTS = ("NOT_COUNTED", "COMPUTED", "NOT_BUILT", "RECORDED")
RECORDED = "RECORDED"
SWITCH_PREFIX = "convention."
ID_PREFIX = "PK_"
FIELDS = ("id", "name", "value", "unit", "range", "source", "scope", "engine_key", "fills")
TYPE_USE = {"HOUSE": "H", "PLAZA": "P"}

class ConventionError(Exception):
  pass

def _raw(path: str = PATH) -> dict:
  with open(path, encoding="utf-8") as fh:
    data = yaml.safe_load(fh)
  if not isinstance(data, dict) or not isinstance(data.get("conventions"), list):
    raise ConventionError("conventions_pk.yaml must hold a conventions list")
  return data

def raw_ids(path: str = PATH) -> list:
  return [str(c.get("id")) for c in _raw(path)["conventions"] if isinstance(c, dict)]

def _num(x) -> bool:
  return isinstance(x, (int, float)) and not isinstance(x, bool) and x == x

def problems(path: str = PATH) -> list:
  out: list = []
  data = _raw(path)
  items = {i.id: i for i in CAT.items()}
  named: dict = {}
  for item in items.values():
    for inp in item.inputs:
      if inp.default_rule and inp.default_rule.startswith(ID_PREFIX):
        named.setdefault(inp.default_rule, set()).add(f"{item.id}.{inp.name}")
        
  seen: set = set()
  for n, c in enumerate(data["conventions"], 1):
    cid = str(c.get("id") or f"entry {n}") if isinstance(c, dict) else f"entry {n}"
    if not isinstance(c, dict):
      out.append(f"{cid}: not a mapping")
      continue
    gone = [f for f in FIELDS if f not in c]
    if gone:
      out.append(f"{cid}: missing {', '.join(gone)}")
      continue
    if cid in seen:
      out.append(f"{cid}: id used twice")
    seen.add(cid)
    if not cid.startswith(ID_PREFIX):
      out.append(f"{cid}: a convention id starts with {ID_PREFIX}")
    rng = c["range"]
    
    if not (isinstance(rng, list) and len(rng) == 2 and all(_num(x) for x in rng) and rng[0] < rng[1]):
      out.append(f"{cid}: range must be two numbers, low then high")
    elif not _num(c["value"]) or not rng[0] <= c["value"] <= rng[1]:
      out.append(f"{cid}: value {c['value']} is not inside its range {rng[0]} to {rng[1]}")
    if c["unit"] not in UNITS:
      out.append(f"{cid}: unit {c['unit']} is not one of {', '.join(UNITS)}")
    src = c["source"] if isinstance(c["source"], dict) else {}
    kind = src.get("kind")
    
    if kind == "PROJECT":
      out.append(f"{cid}: a convention is a market fact from a QS, never a value read from one project")
    elif kind not in SOURCE_KINDS:
      out.append(f"{cid}: source kind must be one of {', '.join(SOURCE_KINDS)}")
    elif kind in SOURCE_LABELS and src.get("label") != SOURCE_LABELS[kind]:
      out.append(f"{cid}: a {kind} source is labelled {SOURCE_LABELS[kind]!r}")
    elif kind == STANDARD and not str(src.get("label") or "").startswith("Standard: "):
      out.append(f"{cid}: a STANDARD source is labelled 'Standard: ' and the standard")
    if not str(src.get("note") or "").strip():
      out.append(f"{cid}: the source needs a note saying where the value and the range come from")
    scope = c["scope"]
    if not (isinstance(scope, list) and scope and all(s in CM.USES for s in scope)):
      out.append(f"{cid}: scope must list H, P or both")
    fills = c["fills"] if isinstance(c["fills"], list) else []
    
    for ref in fills:
      item_id, _, input_name = str(ref).partition(".")
      if item_id not in items or input_name not in {i.name for i in items[item_id].inputs}:
        out.append(f"{cid}: fills {ref}, which is not an input of the catalogue")
    if set(map(str, fills)) != named.get(cid, set()):
      out.append(f"{cid}: fills {sorted(map(str, fills))} but the catalogue inputs that name it are {sorted(named.get(cid, set()))}")
  for cid in sorted(set(named) - seen):
    out.append(f"{cid}: named as a default rule by {', '.join(sorted(named[cid]))} and not in the conventions file")
  mseen: set = set()
  for m in data.get("methods") or []:
    mid = str(m.get("id") or "?")
    if mid in mseen:
      out.append(f"method {mid}: id used twice")
    mseen.add(mid)
    
    if m.get("item") not in items:
      out.append(f"method {mid}: item {m.get('item')} is not in the catalogue")
    elif m.get("input") and m["input"] not in {i.name for i in items[m["item"]].inputs}:
      out.append(f"method {mid}: input {m['input']} is not an input of {m['item']}")
    opts = m.get("options") or {}
    recorded = bool(opts) and all(isinstance(o, dict) and o.get("effect") == RECORDED for o in opts.values())
    if not opts or (m.get("default") not in opts and not (recorded and m.get("default") is None)):
      out.append(f"method {mid}: the default must be one of its options (a method whose every option is only recorded may have none)")
    for name, o in opts.items():
      if not isinstance(o, dict) or o.get("effect") not in EFFECTS or not str(o.get("text") or "").strip():
        out.append(f"method {mid}: option {name} needs a text and an effect from {', '.join(EFFECTS)}")
  return out

@functools.lru_cache(maxsize=1)
def _load() -> dict:
  bad = problems()
  if bad:
    raise ConventionError("; ".join(bad[:5]) + (f"; and {len(bad) - 5} more" if len(bad) > 5 else ""))
  return _raw()

def conventions() -> list:
  return list(_load()["conventions"])

def methods() -> list:
  return list(_load().get("methods") or [])

def ids() -> list:
  return [c["id"] for c in conventions()]

def get(cid: str) -> dict | None:
  return next((c for c in conventions() if c["id"] == cid), None)

def seed(cid: str) -> float:
  c = get(cid)
  if c is None:
    raise ConventionError(f"no convention {cid}")
  return float(c["value"])

def switch_key(cid: str) -> str:
  return SWITCH_PREFIX + cid

def method(mid: str) -> dict | None:
  return next((m for m in methods() if m["id"] == mid), None)

def method_choice(mid: str, decided: dict | None) -> tuple:
  m = method(mid)
  if m is None:
    raise ConventionError(f"no method {mid}")
  want = (decided or {}).get(mid)
  name, was = (want, True) if want in m["options"] else (m["default"], False)
  return name, (RECORDED if name is None else m["options"][name]["effect"]), was

def method_of_item(item_id: str) -> dict | None:
  return next((m for m in methods() if m["item"] == item_id), None)

def in_scope(cid: str, project_type: str | None) -> bool:
  c = get(cid)
  use = TYPE_USE.get(str(project_type or ""))
  return c is not None and (use is None or use in c["scope"])

def on_ids(held: dict | None) -> list:
  held = held or {}
  out = []
  
  for cid in ids():
    row = held.get(switch_key(cid))
    value = row.get("value") if isinstance(row, dict) else row
    if value is not None and not isinstance(value, str) and float(value) >= 0.5:
      out.append(cid)
  return out

def assumption(cid: str, item_id: str, input_name: str, floor: str | None) -> dict:
  c = get(cid)
  return {"item": item_id, "floor": floor, "input": input_name, "rule": cid, "value": c["value"], "unit": c["unit"], "range": list(c["range"]),
    "source": c["source"]["label"], "typical": True}
