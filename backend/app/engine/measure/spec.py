from __future__ import annotations
import re
from decimal import Decimal, ROUND_HALF_UP

CONCRETE = "CONCRETE"
MASONRY = "MASONRY"
THICKNESS_STEP_MM = 5
KEY_FIELDS = (("thickness_mm", "t"),)

_M_GRADE = re.compile(r"\bM\s?-?(10|15|20|25|30|35|40|45|50|55|60)\b", re.I)
_C_PAIR = re.compile(r"\bC\s?(\d{2})\s?/\s?(\d{2})\b", re.I)
_PSI = re.compile(r"\b(\d{3,4})\s?psi\b", re.I)
_NOMINAL_MIX = re.compile(r"(?<![\d:.])1\s?:\s?(\d(?:\.\d)?)\s?:\s?(\d(?:\.\d)?)(?![\d.]|\s?:)")

_MORTAR = re.compile(r"(?<![\d:.])1\s?:\s?(\d{1,2}(?:\.\d)?)(?![\d.]|\s?:)")

STRUCTURAL_CONCRETE_PREFIXES = (
  "COLUMN", "BEAM", "EDGE_BEAM", "GIRDER", "DIAPHRAGM", "LINTEL", "SILL", "KERB", "SLAB", "FOUNDATION", "FOOTING",
  "RAFT", "PILE", "GROUND_BEAM", "STAIR", "LANDING", "RAMP",
)

def _num(text: str) -> str:
  return format(Decimal(text).normalize(), "f")

def concrete_grade(text: str | None) -> str | None:
  if not text:
    return None
  m = _M_GRADE.search(text)
  if m:
    return f"M{m.group(1)}"
  m = _C_PAIR.search(text)
  if m:
    return f"C{m.group(1)}/{m.group(2)}"
  m = _PSI.search(text)
  if m:
    return f"{m.group(1)}psi"
  m = _NOMINAL_MIX.search(text)
  if m:
    return f"1:{_num(m.group(1))}:{_num(m.group(2))}"
  return None

def mortar_ratio(text: str | None) -> str | None:
  if not text:
    return None
  m = _MORTAR.search(text)
  return f"1:{_num(m.group(1))}" if m else None

def round_thickness(mm) -> int | None:
  if mm is None:
    return None
  value = Decimal(str(mm))
  if not value.is_finite() or value <= 0:
    return None
  step = Decimal(THICKNESS_STEP_MM)
  return int((value / step).quantize(Decimal(1), rounding=ROUND_HALF_UP) * step)

def _profile_thickness(profile) -> Decimal | None:
  if not isinstance(profile, dict) or profile.get("kind") != "RECT":
    return None
  try:
    dims = [Decimal(str(profile[k])) for k in ("x_dim", "y_dim")]
  except (KeyError, ArithmeticError, ValueError):
    return None
  dims = [d for d in dims if d.is_finite() and d > 0]
  return min(dims) if len(dims) == 2 else None

def is_wall(role: str | None) -> bool:
  return (role or "").upper().startswith("WALL")

def is_structural_concrete(role: str | None) -> bool:
  return (role or "").upper().startswith(STRUCTURAL_CONCRETE_PREFIXES)

def derive_spec(el) -> dict | None:
  role = (el.role or "").upper()
  text = getattr(el, "material_text", None)
  klass = el.material_class
  if klass == "STEEL":
    return None

  if is_wall(role) and klass != CONCRETE:
    spec: dict = {"kind": MASONRY}
    basis: dict = {}
    thickness = getattr(el, "thickness_mm", None)
    source = "element"
    if thickness is None or Decimal(str(thickness)) <= 0:
      thickness, source = _profile_thickness(el.profile), "profile"
    rounded = round_thickness(thickness)
    if rounded is not None:
      spec["thickness_mm"] = rounded
      basis["thickness_mm"] = source
    mortar = mortar_ratio(text)
    if mortar:
      spec["mortar"] = mortar
      basis["mortar"] = "material_text"
    if klass is None:
      basis["material"] = "assumed_masonry"
    spec["basis"] = basis
    return spec
  if (is_wall(role) and klass == CONCRETE) or is_structural_concrete(role):
    spec = {"kind": CONCRETE}
    grade = concrete_grade(text)
    
    if grade:
      spec["grade"] = grade
      spec["basis"] = {"grade": "material_text"}
    else:
      spec["basis"] = {}
    return spec
  return None

def spec_grade(spec: dict | None) -> str | None:
  if not spec:
    return None
  return spec.get("grade") or spec.get("mortar")

def spec_key(spec: dict | None) -> str | None:
  if not spec:
    return None
  parts = [f"{tag}{spec[name]}" for name, tag in KEY_FIELDS if spec.get(name) is not None]
  return "|".join(parts) or None

def describe_spec(spec: dict | None) -> str | None:
  if not spec:
    return None
  if spec.get("kind") == "DERIVED" and spec.get("recipe") == "PDF_LINTEL_STEEL":
    return "bars and rings printed for the lintel"
  if spec.get("kind") == "DERIVED" and spec.get("recipe") == "STRUCT_FORMWORK":
    p = spec.get("params") or {}
    cat = spec.get("category")
    if cat == "SLAB":
      return "soffit and edges" if p.get("slab_edge_formwork", 1) >= 0.5 else "soffit only"
    if cat == "TANK":
      return "walls inside and out and the top slab soffit" + (" and the base soffit" if p.get("tank_base_formwork", 0) >= 0.5 else "")
    if cat in ("CHAJJA", "BALCONY_SLAB"):
      return "soffit and edges" if p.get("slab_edge_formwork", 1) >= 0.5 else "soffit only"
    return {"COLUMN": "all four faces", "FOOTING": "four sides", "LINTEL": "soffit and both sides", "BEAM": "soffit and both sides", "COPING": "both sides"}.get(cat or "", "worked out from the concrete read from the drawing")
  if spec.get("kind") == "DERIVED":
    p = spec.get("params") or {}
    bits: list[str] = []
    if p.get("working_space_mm") is not None:
      bits.append(f"{p['working_space_mm']:g} mm working space")
    if p.get("pcc_projection_mm") is not None:
      bits.append(f"PCC projects {p['pcc_projection_mm']:g} mm")
    if p.get("pcc_thickness_mm") is not None:
      bits.append(f"PCC {p['pcc_thickness_mm']:g} mm thick")
    return ", ".join(bits) or "worked out from the foundation"
  parts: list[str] = []
  if spec.get("thickness_mm") is not None:
    parts.append(f"{spec['thickness_mm']} mm thick")
  if spec.get("mortar"):
    parts.append(f"mortar {spec['mortar']}")
  if spec.get("grade"):
    parts.append(f"mix {spec['grade']}")
  return ", ".join(parts) or None

def missing_spec_warnings(spec: dict | None, concrete_billed: bool) -> list[str]:
  if not spec:
    return []
  out: list[str] = []
  if spec.get("kind") == MASONRY and not concrete_billed:
    if spec.get("thickness_mm") is None:
      out.append("SPEC_THICKNESS_MISSING")
    if not spec.get("mortar"):
      out.append("SPEC_MORTAR_MISSING")
  elif concrete_billed and not spec.get("grade"):
    out.append("SPEC_MIX_MISSING")
  return out
