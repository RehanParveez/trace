from __future__ import annotations
LENGTH_BASES = ("CENTRE", "OUTER", "CLEAR")

def _num(v, name: str) -> float:
  if isinstance(v, bool) or not isinstance(v, (int, float)):
    raise ValueError(f"{name} must be a number.")
  return float(v)

def _pos(v, name: str) -> float:
  x = _num(v, name)
  if x < 0.0:
    raise ValueError(f"{name} cannot be negative.")
  return x

def _table(v, name: str, fields: tuple) -> list:
  if not isinstance(v, list) or not v:
    raise ValueError(f"{name} must be a list of rows.")
  out = []
  for row in v:
    if not isinstance(row, dict) or set(row) != set(fields):
      raise ValueError(f"Each row of {name} must have exactly: {', '.join(fields)}.")
    out.append({f: _pos(row[f], f"{name}.{f}") for f in fields})
  return out

def strip(params: dict, inputs: dict) -> dict:
  basis = params["length_basis"]
  length = _pos(inputs[{"CENTRE": "centre_mm", "OUTER": "outer_mm", "CLEAR": "clear_mm"}[basis]], "length")
  return {"length_mm": length, "volume_m3": params["width_mm"] * params["depth_mm"] * length / 1e9}

def steps(params: dict, inputs: dict) -> dict:
  area_mm2 = sum(r["width_mm"] * r["height_mm"] for r in params["table"])
  length = _pos(inputs["length_mm"], "length_mm")
  return {"section_m2": area_mm2 / 1e6, "volume_m3": area_mm2 * length / 1e9}

def frame(params: dict, inputs: dict) -> dict:
  width, height = _pos(inputs["opening_width_mm"], "opening_width_mm"), _pos(inputs["opening_height_mm"], "opening_height_mm")
  band = next((r for r in sorted(params["section_by_width"], key=lambda r: r["max_width_mm"]) if width <= r["max_width_mm"]), None)
  last = max(params["section_by_width"], key=lambda r: r["max_width_mm"])
  band = band or last
  return {"length_mm": width + 2.0 * height + params["add_mm"], "section_mm": [band["width_mm"], band["depth_mm"]]}

def web_below_slab(params: dict, inputs: dict) -> dict:
  depth, slab = _pos(inputs["beam_depth_mm"], "beam_depth_mm"), _pos(inputs["slab_mm"], "slab_mm")
  includes = bool(inputs.get("includes_slab", True))
  return {"web_mm": max(0.0, depth - slab) if includes else depth}

def roof_area(params: dict, inputs: dict) -> dict:
  area = _pos(inputs["covered_m2"], "covered_m2") + (_pos(inputs.get("projection_m2", 0.0), "projection_m2") if params["include_projection"] else 0.0) - _pos(inputs.get("standing_m2", 0.0), "standing_m2")
  return {"area_m2": max(0.0, area)}

FORMULAS = {
  "strip": (strip, {"width_mm": _pos, "depth_mm": _pos, "length_basis": None}, ("one of centre_mm, outer_mm, clear_mm",)),
  "steps": (steps, {"table": None}, ("length_mm",)),
  "frame": (frame, {"add_mm": _pos, "section_by_width": None}, ("opening_width_mm", "opening_height_mm")),
  "web_below_slab": (web_below_slab, {}, ("beam_depth_mm", "slab_mm", "includes_slab")),
  "roof_area": (roof_area, {"include_projection": None}, ("covered_m2", "projection_m2", "standing_m2")),
}

def checked(spec) -> dict:
  if not isinstance(spec, dict) or set(spec) - {"formula", "params"} or "formula" not in spec:
    raise ValueError('A formula rule is {"formula": <name>, "params": {...}}.')
  name = spec["formula"]
  if name not in FORMULAS:
    raise ValueError(f"Unknown formula '{name}'. The library has: {', '.join(sorted(FORMULAS))}.")
  declared = FORMULAS[name][1]
  params = spec.get("params") or {}
  if not isinstance(params, dict) or set(params) != set(declared):
    raise ValueError(f"The formula {name} takes the params: {', '.join(declared) or 'none'}.")

  out: dict = {}
  for p, check in declared.items():
    v = params[p]
    if name == "strip" and p == "length_basis":
      if v not in LENGTH_BASES:
        raise ValueError(f"length_basis must be one of {', '.join(LENGTH_BASES)}.")
      out[p] = v
      
    elif name == "steps":
      out[p] = _table(v, "table", ("width_mm", "height_mm"))
    elif name == "frame" and p == "section_by_width":
      out[p] = _table(v, "section_by_width", ("max_width_mm", "width_mm", "depth_mm"))
    elif name == "roof_area":
      if not isinstance(v, bool):
        raise ValueError("include_projection must be true or false.")
      out[p] = v
    else:
      out[p] = check(v, p)
  return {"formula": name, "params": out}

def is_formula(value) -> bool:
  return isinstance(value, dict) and "formula" in value

def evaluate(spec: dict, inputs: dict) -> dict:
  spec = checked(spec)
  return FORMULAS[spec["formula"]][0](spec["params"], inputs)

PREFIX = "formula."

def run(name: str, defaults: dict, inputs: dict, scope: dict | None = None) -> tuple:
  from app.engine.measure import rulebook as RB
  rv = RB.resolve(PREFIX + name, scope)
  params, rule_id, version, source = defaults, None, None, "CODE"
  if rv.rule_id is not None and is_formula(rv.value) and rv.value.get("formula") == name:
    params, rule_id, version, source = checked(rv.value)["params"], rv.rule_id, rv.version, "RULE"
  spec = checked({"formula": name, "params": params})
  applied = {"formula": name, "source": source, "rule_id": rule_id, "version": version, "params": spec["params"]}
  return FORMULAS[name][0](spec["params"], inputs), applied
