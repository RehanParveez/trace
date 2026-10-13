from __future__ import annotations
from decimal import Decimal
import re
from app.engine.measure.models import CalculationContext, LedgerEntry, ModelElement
from dataclasses import dataclass, field, replace
from app.engine.measure.spec import CONCRETE, MASONRY, concrete_grade, missing_spec_warnings, mortar_ratio, round_thickness, spec_key
from app.engine.measure.units import q6

FINISH = "FINISH"
INSULATION = "INSULATION"
WATERPROOF = "WATERPROOF"
METAL = "METAL"
AIR = "AIR"
TIMBER = "TIMBER"
EARTH = "EARTH"
UNKNOWN = "UNKNOWN"

LAYER_MAPPING_PREFIX = "LAYER:"

CODE_FINISH_EXCLUDED = "LAYER_FINISH_EXCLUDED"
CODE_UNPRICED = "LAYER_UNPRICED"
CODE_MISMATCH = "LAYER_THICKNESS_MISMATCH"
CODE_NOT_SPLIT = "LAYER_NOT_SPLIT"
LAYER_CODES = (CODE_FINISH_EXCLUDED, CODE_UNPRICED, CODE_MISMATCH, CODE_NOT_SPLIT)

MISMATCH_ABS_MM = Decimal("5")
MISMATCH_REL = Decimal("0.02")

_FAMILY_PATTERNS = (
  (FINISH, re.compile(
    r"plaster|render|stucco|skim|putty|paint|distemper|whitewash|\btiles?\b|tiling|marble|granite|mosaic|terrazzo|screed|gypsum|"
    r"cladding|veneer|wall\s?paper|\bfinish", re.I)),
  (INSULATION, re.compile(
    r"insulat|rock\s?wool|mineral\s?wool|glass\s?wool|polystyrene|\beps\b|\bxps\b|polyurethane|\bpir\b|foam|thermal", re.I)),
  (WATERPROOF, re.compile(r"water\s?proof|membrane|bitumen|\bdpc\b|\bdpm\b|damp|\bfelt\b|vapou?r\s?barrier|tanking", re.I)),
  (MASONRY, re.compile(r"\b(bricks?|brickwork|blocks?|blockwork|masonry|cmu|aac|rubble|ashlar|mortar)\b", re.I)),
  (CONCRETE, re.compile(
    r"\b(concrete|rcc|pcc|in[\s_-]?situ|cast[\s_-]?in[\s_-]?(?:situ|place))\b|\bm\s?(?:15|20|25|30|35|40|45|50)\b", re.I)),
  (METAL, re.compile(r"deck|steel|alumin|galvani[sz]ed|\bgi\b|\biron\b|\bzinc\b|\bcopper\b|\bmetal\b", re.I)),
  (AIR, re.compile(r"\bair\b|cavity|\bvoid\b|\bgap\b", re.I)),
  (TIMBER, re.compile(r"wood|timber|plywood|\bmdf\b|\bply\b|bamboo", re.I)),
  (EARTH, re.compile(r"\bsoil\b|\bearth\b|\bsand\b|gravel|aggregate|hardcore|\bfill\b|soling", re.I)),
)

FAMILY_LABELS = {
  FINISH: "finish", INSULATION: "insulation", WATERPROOF: "waterproofing", MASONRY: "masonry", CONCRETE: "concrete",
  METAL: "metal", AIR: "air gap", TIMBER: "timber", EARTH: "earth or fill", UNKNOWN: "unknown material",
}

def layer_family(layer: dict) -> str:
  text = " ".join(str(layer.get(k) or "") for k in ("material", "name")).strip()
  if not text:
    return UNKNOWN
  for family, pattern in _FAMILY_PATTERNS:
    if pattern.search(text):
      return family
  return UNKNOWN

def _thickness(layer: dict) -> Decimal | None:
  try:
    value = Decimal(str(layer.get("thickness_mm")))
  except Exception:
    return None
  return value if value.is_finite() and value > 0 else None

def usable_layers(el: ModelElement | None) -> list[dict]:
  if el is None:
    return []
  out = []
  for layer in getattr(el, "layers", None) or ():
    t = _thickness(layer) if isinstance(layer, dict) else None
    if t is not None:
      out.append({**layer, "thickness_mm": t, "family": layer_family(layer)})
  return out

def _layer_label(layer: dict) -> str:
  return str(layer.get("material") or layer.get("name") or "layer")

def _group_spec(family: str, thickness: Decimal, layers: list, el: ModelElement) -> dict | None:
  names = " ".join(_layer_label(l) for l in layers)
  text = getattr(el, "material_text", None)
  rounded = round_thickness(thickness)
  if family == MASONRY:
    spec: dict = {"kind": MASONRY, "basis": {}}
    if rounded is not None:
      spec["thickness_mm"] = rounded
      spec["basis"]["thickness_mm"] = "layer"
    mortar = mortar_ratio(names)
    source = "layer_material"
    if not mortar:
      mortar, source = mortar_ratio(text), "material_text"
      
    if mortar:
      spec["mortar"] = mortar
      spec["basis"]["mortar"] = source
    return spec
  if family == CONCRETE:
    grade = concrete_grade(names)
    source = "layer_material"
    
    if not grade:
      grade, source = concrete_grade(text), "material_text"
    spec = {"kind": CONCRETE, "basis": {}}
    if grade:
      spec["grade"] = grade
      spec["basis"]["grade"] = source
    return spec
  spec = {"kind": "LAYER", "family": family, "basis": {}}
  if rounded is not None:
    spec["thickness_mm"] = rounded
    spec["basis"]["thickness_mm"] = "layer"
  return spec

def layer_mapping_codes(ctx: CalculationContext) -> dict:
  return {m.ifc_type[len(LAYER_MAPPING_PREFIX):].upper(): m.work_item_code
    for m in ctx.mappings if m.ifc_type.startswith(LAYER_MAPPING_PREFIX) and m.work_item_code}

@dataclass(frozen=True)
class LayerResult:
  ledger: list
  replaced: list = field(default_factory=list)
  added: list = field(default_factory=list)
  stats: dict = field(default_factory=dict)

def _host_family(row: LedgerEntry) -> str | None:
  kind = (row.spec or {}).get("kind")
  return kind if kind in (MASONRY, CONCRETE) else None

def _destination(family: str, host_code: str, host_family: str | None, wall_code: str | None, concrete_code: str | None,
  codes: dict):
  if family == FINISH:
    return ("FINISH", None)
  if host_family is not None and family == host_family:
    return ("BILL", host_code)
  if family == CONCRETE and concrete_code:
    return ("BILL", concrete_code)
  if family == MASONRY and wall_code:
    return ("BILL", wall_code)
  code = codes.get(family)
  if code:
    return ("BILL", code)
  return ("UNPRICED", family)

def split_layers(ctx: CalculationContext, elements: list, solids: list, ledger: list) -> LayerResult:
  by_element = {e.id: e for e in elements}
  by_solid = {s.id: s for s in solids}
  by_ifc = {m.ifc_type: m for m in ctx.mappings}
  concrete_code = None
  for t in ("IfcSlab", "IfcColumn", "IfcBeam", "IfcFooting"):
    m = by_ifc.get(t)
    if m is not None and m.work_item_code:
      concrete_code = m.work_item_code
      break
  wall = by_ifc.get("IfcWall") or by_ifc.get("IfcWallStandardCase")
  wall_code = wall.work_item_code if wall is not None else None
  codes = layer_mapping_codes(ctx)

  out: list = []
  replaced: list = []
  added: list = []
  counts = {"rows_split": 0, "rows_merged": 0, "rows_not_split": 0, "rows_mismatch": 0}
  finish_m3 = Decimal("0")
  unpriced_m3 = Decimal("0")
  unpriced_by_family: dict = {}

  for row in ledger:
    el = by_element.get(row.element_id)
    solid = by_solid.get(row.solid_id)
    layers = usable_layers(el)
    if (row.source_kind != "MODEL" or row.formula_code != "SOLID_NET_VOLUME" or solid is None or len(layers) < 2
        or row.spec is None):
      out.append(row)
      continue

    total = sum((l["thickness_mm"] for l in layers), Decimal("0"))
    host_family = _host_family(row)
    groups: dict = {}
    for layer in layers:
      kind, code = _destination(layer["family"], row.work_item_code, host_family, wall_code, concrete_code, codes)
      g = groups.setdefault((kind, code), {"kind": kind, "code": code, "family": layer["family"],
        "thickness": Decimal("0"), "layers": []})
      g["thickness"] += layer["thickness_mm"]
      g["layers"].append(layer)
    ordered = list(groups.values())
    amounts = [q6(row.quantity * g["thickness"] / total) for g in ordered]
    biggest = max(range(len(amounts)), key=lambda i: (amounts[i], -i))
    amounts[biggest] = q6(amounts[biggest] + (row.quantity - sum(amounts, Decimal("0"))))

    billed = [(g, a) for g, a in zip(ordered, amounts) if g["kind"] == "BILL" and a > 0]
    if not billed:
      kept = replace(row, warnings=tuple(dict.fromkeys((*row.warnings, CODE_NOT_SPLIT))))
      out.append(kept)
      replaced.append((row.solid_id, row.work_item_code))
      added.append(kept)
      counts["rows_not_split"] += 1
      continue

    declared = getattr(el, "thickness_mm", None)
    mismatch = False
    if declared is not None and Decimal(str(declared)) > 0:
      d = Decimal(str(declared))
      mismatch = abs(total - d) > max(MISMATCH_ABS_MM, MISMATCH_REL * d)
    row_excluded = Decimal("0")
    extra: list = []
    if mismatch:
      extra.append(CODE_MISMATCH)
      counts["rows_mismatch"] += 1
    for g, amount in zip(ordered, amounts):
      if g["kind"] == "FINISH":
        row_excluded += amount
        finish_m3 += amount
        if CODE_FINISH_EXCLUDED not in extra:
          extra.append(CODE_FINISH_EXCLUDED)
      elif g["kind"] == "UNPRICED":
        row_excluded += amount
        unpriced_m3 += amount
        unpriced_by_family[g["code"]] = unpriced_by_family.get(g["code"], Decimal("0")) + amount
        if CODE_UNPRICED not in extra:
          extra.append(CODE_UNPRICED)

    summary = [{"material": _layer_label(l), "family": l["family"], "thickness_mm": str(l["thickness_mm"])} for l in layers]
    for g, amount in billed:
      spec = _group_spec(g["family"], g["thickness"], g["layers"], el)
      trace = dict(row.trace)
      inputs = dict(trace.get("inputs") or {})
      inputs["layer_split"] = {
        "of_m3": str(row.quantity), "total_thickness_mm": str(total),
        "declared_thickness_mm": str(declared) if declared is not None else None,
        "excluded_m3": str(row_excluded), "layers": summary, "family": g["family"],
        "billed_thickness_mm": str(g["thickness"]),
        "share": str((g["thickness"] / total).quantize(Decimal("0.000001"))),
      }
      inputs["spec"] = spec
      trace["inputs"] = inputs
      trace["steps"] = [
        {"op": "layer_share", "family": g["family"], "thickness_mm": str(g["thickness"]), "of_thickness_mm": str(total),
         "of_m3": str(row.quantity), "m3": str(amount)},
        {"op": "net_volume", "m3": str(amount)},
      ]
      trace["net"] = {"m3": str(amount)}
      warnings = [w for w in row.warnings if not w.startswith("SPEC_")]
      warnings.extend(missing_spec_warnings(spec if spec.get("kind") in (MASONRY, CONCRETE) else None,
        bool(concrete_code) and g["code"] == concrete_code))
      warnings.extend(extra)
      piece = replace(row, work_item_code=g["code"], quantity=amount, material_grade=spec.get("grade") or spec.get("mortar"),
        spec=spec, spec_key=spec_key(spec), trace=trace, warnings=tuple(dict.fromkeys(warnings)))
      out.append(piece)
      added.append(piece)
    replaced.append((row.solid_id, row.work_item_code))
    counts["rows_split" if len(ordered) > 1 else "rows_merged"] += 1

  out.sort(key=lambda r: (r.work_item_code, str(r.level_id), str(r.element_id), r.work_stage or ""))
  stats = {"enabled": True, **counts, "finish_excluded_m3": str(q6(finish_m3)), "unpriced_m3": str(q6(unpriced_m3)),
    "unpriced_by_family": {k: str(q6(v)) for k, v in sorted(unpriced_by_family.items())}}
  return LayerResult(ledger=out, replaced=replaced, added=added, stats=stats)

def layer_excluded_by_solid(ledger: list) -> dict:
  found: dict = {}
  for r in ledger:
    ls = ((r.trace or {}).get("inputs") or {}).get("layer_split")
    if r.formula_code == "SOLID_NET_VOLUME" and ls:
      found[r.solid_id] = Decimal(ls.get("excluded_m3") or "0")
  return found

def layer_check(ledger: list) -> list:
  failures: list = []
  per_solid: dict = {}
  for r in ledger:
    ls = ((r.trace or {}).get("inputs") or {}).get("layer_split")
    if r.formula_code != "SOLID_NET_VOLUME" or not ls:
      continue
    entry = per_solid.setdefault(r.solid_id, {"of": Decimal(ls["of_m3"]), "excluded": Decimal(ls.get("excluded_m3") or "0"),
      "sum": Decimal("0")})
    entry["sum"] += r.quantity
  for solid_id, entry in per_solid.items():
    if entry["sum"] + entry["excluded"] != entry["of"]:
      failures.append(f"layer split does not add back on solid {solid_id}: {entry['sum'] + entry['excluded']} != {entry['of']}")
  return failures
