from __future__ import annotations
import functools
import os
import yaml

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site_inputs.yaml")
PREFIX = "site."
NUMBER, CHOICE = "NUMBER", "CHOICE"
SHAPES = (NUMBER, CHOICE)
RANGE, OPTION, NOT_BILLED = "RANGE", "OPTION", "NOT_BILLED"
FIELDS = ("id", "label", "asks", "shape", "fallback", "proportional", "waits", "read")

class SiteInputError(Exception):
  pass

@functools.lru_cache(maxsize=1)
def _raw() -> dict:
  with open(PATH, encoding="utf-8") as fh:
    data = yaml.safe_load(fh)
  if not isinstance(data, dict) or not isinstance(data.get("site_inputs"), list):
    raise SiteInputError("site_inputs.yaml must hold a list of site_inputs")
  return data

def all_inputs() -> list:
  return list(_raw()["site_inputs"])

def ids() -> list:
  return [s["id"] for s in all_inputs()]

def get(sid: str) -> dict | None:
  return next((s for s in all_inputs() if s["id"] == sid), None)

def key_of(sid: str) -> str:
  return PREFIX + sid

def id_of(key: str) -> str:
  return str(key)[len(PREFIX):]

def is_key(key: str) -> bool:
  return str(key).startswith(PREFIX) and get(id_of(key)) is not None

def waiting_on(item_id: str) -> list:
  return [s for s in all_inputs() if item_id in (s.get("waits") or [])]

def options_of(s: dict) -> list:
  fb = (s.get("fallback") or {})
  return [{"value": v, "label": v.replace("_", " ").capitalize(), "text": o["text"], "is_default": fb.get("kind") == OPTION and fb.get("typical") == v,
    "effect": "ENGINE" if o.get("params") else "RECORDED"} for v, o in (s.get("options") or {}).items()]

def default_of(s: dict, switched_on: bool = False) -> dict | None:
  fb = s.get("fallback")
  if not fb:
    return None
  if fb["kind"] == RANGE:
    return {"value": fb["typical"], "unit": s.get("unit"), "range": [fb["low"], fb["high"]], "rule": s["id"], "source": fb["source"], "switched_on": switched_on}
  if fb["kind"] == OPTION:
    return {"value": fb["typical"], "unit": None, "range": None, "rule": s["id"], "source": fb["source"], "switched_on": switched_on}
  return None

def question_fields(sid: str, switched_on: bool = False) -> dict:
  s = get(sid)
  if s is None:
    return {}
  return {"unit": s.get("unit"), "options": options_of(s) if s["shape"] == CHOICE else [], "default": default_of(s, switched_on)}

def check(sid: str, value) -> str | None:
  s = get(sid)
  if s is None:
    return "That is not a site input."
  if s["shape"] == CHOICE:
    return None if str(value) in (s.get("options") or {}) else "That is not one of the options."
  try:
    v = float(value)
  except (TypeError, ValueError):
    return "Give a number."
  lo, hi = s["bounds"]
  if not lo <= v <= hi or v != v:
    return f"Give a number between {lo:g} and {hi:g} {s['unit']}."
  return None

def params_of(sid: str, value) -> dict:
  s = get(sid)
  if s is None or check(sid, value) is not None:
    return {}
  if s["shape"] == CHOICE:
    return {k: float(v) for k, v in ((s["options"][str(value)].get("params")) or {}).items()}
  return {p: float(value) * float(scale) for p, scale in (s.get("feeds") or {}).items()}

def derived_params(answers: dict | None) -> dict:
  out: dict = {}
  for key, a in (answers or {}).items():
    if not is_key(key):
      continue
    value = a.get("value") if isinstance(a, dict) else a
    out.update(params_of(id_of(key), value))
  return out

def fallback_assumption(sid: str, item_id: str, floor: str | None) -> dict | None:
  s = get(sid)
  fb = (s or {}).get("fallback")
  if not fb or fb["kind"] == NOT_BILLED:
    return None
  if fb["kind"] == RANGE:
    return {"item": item_id, "floor": floor, "input": sid.lower(), "rule": sid, "value": fb["typical"], "unit": s["unit"], "range": [fb["low"], fb["high"]], "source": fb["source"], "typical": True}
  return {"item": item_id, "floor": floor, "input": sid.lower(), "rule": sid, "value": fb["typical"], "unit": None, "range": None, "source": fb["source"], "typical": True}

def printed_value(sid: str, printed: dict | None):
  read = (get(sid) or {}).get("read")
  if not read or not printed:
    return None
  got = ((printed.get("spec") or printed).get(read["key"]) or {}).get(read["scope"])
  return None if not got else (got.get("value") if isinstance(got, dict) else got)

def problems(data: dict | None = None) -> list:
  from app.engine.catalogue import loader as CAT
  from app.engine.catalogue import param_keys as PK
  from app.engine.measure import derived as DV
  d = data or _raw()
  items = {i.id for i in CAT.items()}
  params = {**{n: (lo, hi) for n, (_d, lo, hi) in DV.PARAMS.items()}, **DV.ASKED_PARAMS, DV.NGL_PARAM: DV.NGL_RANGE}
  out, seen = [], set()
  for s in d["site_inputs"]:
    name = s.get("id", "?")
    out += [f"{name}: no {f}" for f in FIELDS if f not in s]
    if name in seen:
      out.append(f"{name}: repeated")
    seen.add(name)
    if s.get("shape") not in SHAPES:
      out.append(f"{name}: shape must be one of {', '.join(SHAPES)}")
      continue
    for it in s.get("waits") or []:
      if it not in items:
        out.append(f"{name}: waits on {it}, which is not a catalogue item")
    fb = s.get("fallback")

    if fb is not None:
      if fb.get("kind") not in (RANGE, OPTION, NOT_BILLED):
        out.append(f"{name}: fallback kind must be {RANGE}, {OPTION} or {NOT_BILLED}")
      if not fb.get("source"):
        out.append(f"{name}: a fallback names its source: the QS and the date")
    if s["shape"] == NUMBER:
      b = s.get("bounds")
      if not (isinstance(b, list) and len(b) == 2 and b[0] < b[1]) or not s.get("unit"):
        out.append(f"{name}: a number has a unit and bounds [low, high]")
        continue
      if fb and fb.get("kind") == RANGE:
        lo, ty, hi = fb.get("low"), fb.get("typical"), fb.get("high")
        if not all(isinstance(x, (int, float)) for x in (lo, ty, hi)) or not lo <= ty <= hi or not (b[0] <= lo and hi <= b[1]):
          out.append(f"{name}: the fallback range must be numbers with low <= typical <= high inside the bounds")
      elif fb and fb["kind"] == OPTION:
        out.append(f"{name}: a number has a range or NOT_BILLED fallback, not an option")
      for p, scale in (s.get("feeds") or {}).items():
        if p not in params:
          out.append(f"{name}: feeds {p}, which is not a calculation parameter")
        elif not isinstance(scale, (int, float)) or not (params[p][0] <= b[0] * scale <= params[p][1] and params[p][0] <= b[1] * scale <= params[p][1]):
          out.append(f"{name}: the bounds of the answer do not fit the range of {p}")
    else:
      opts = s.get("options") or {}
      if len(opts) < 2:
        out.append(f"{name}: a choice has at least two options")
      for v, o in opts.items():
        if not o.get("text"):
          out.append(f"{name} {v}: no text")
        for p, x in (o.get("params") or {}).items():
          if p not in params:
            out.append(f"{name} {v}: sets {p}, which is not a calculation parameter")
          elif not (params[p][0] <= float(x) <= params[p][1]):
            out.append(f"{name} {v}: {p} {x} is outside its range")
      if fb and fb["kind"] == OPTION and fb.get("typical") not in opts:
        out.append(f"{name}: the fallback {fb.get('typical')!r} is not one of the options")
      if fb and fb["kind"] == RANGE:
        out.append(f"{name}: a choice has an option or NOT_BILLED fallback, not a range")
        
    read = s.get("read")
    if read is not None:
      key = PK.get(read.get("key"))
      if key is None or key["status"] != "LIVE":
        out.append(f"{name}: read key {read.get('key')} is not a live parameter key")
      elif read.get("scope") not in key["scopes"]:
        out.append(f"{name}: scope {read.get('scope')!r} is not a scope of {read['key']}")
  return out

def main() -> int:
  bad = problems()
  print("\n".join(bad) if bad else f"{len(all_inputs())} site inputs, 0 problems; {sum(len(s.get('waits') or []) for s in all_inputs())} item waits")
  return 1 if bad else 0

if __name__ == "__main__":
  import sys
  sys.exit(main())
