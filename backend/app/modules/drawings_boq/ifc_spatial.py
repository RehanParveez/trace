from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
import math
import re
import ifcopenshell.util.element
import ifcopenshell.util.placement
from app.modules.drawings_boq.ifc_reader import _Scales, _clean, _dec, _extruded_geometry, _flatten_qtos, _issue, _json_safe, _level_by_elevation, _num

_CATEGORY_KEYWORDS = [
  ("TOILET", ("toilet", "wc", "water closet", "lavatory", "powder room", "powder-room", "powder")),
  ("BATHROOM", ("bathroom", "bath room", "bath", "washroom", "wash room", "shower room", "shower")),
  ("KITCHEN", ("kitchen", "pantry kitchen", "kitchenette", "pantry")),
  ("BEDROOM", ("bedroom", "bed room", "master bedroom", "master bed", "guest bedroom", "guest bed", "children bedroom", "child bedroom", "kids bedroom",
    "kids room", "bed")),
  
  ("DRESSING", ("dressing room", "dressing", "walk-in closet", "walk in closet", "walk-in wardrobe", "walk in wardrobe", "wardrobe room", "closet")),
  ("LIVING", ("living room", "living", "lounge", "tv lounge", "tv room", "tv lounge room", "family lounge", "family room", "drawing room", "drawing",
    "sitting room", "sitting", "formal lounge", "formal living")),
  
  ("DINING", ("dining room", "dining", "dining area", "breakfast area", "breakfast room")),
  ("CORRIDOR", ("corridor", "passage", "passageway", "hallway", "hall", "lobby", "foyer", "entrance hall", "circulation", "circulation area", "vestibule")),
  ("STAIR", ("stair", "stairs", "staircase", "stairway", "stair hall", "stair lobby", "stairwell", "stair well")),
  ("LIFT", ("lift", "elevator", "lift lobby", "elevator lobby", "lift machine room", "elevator machine room")),
  ("STORE", ("store", "storage", "store room", "storehouse", "storage room", "general store", "material store", "utility store", "linen store", "janitor store",
    "janitor closet", "cleaner store")),
  
  ("GARAGE", ("garage", "enclosed garage", "covered garage", "car garage", "private garage")),
  ("PARKING", ("parking", "car parking", "car park", "parking area", "parking bay", "parking space", "covered parking", "open parking", "vehicle parking",
    "motorcycle parking", "bike parking")),
  
  ("BALCONY", ("balcony", "balconies", "cantilever balcony", "projecting balcony")),
  ("TERRACE", ("terrace", "roof terrace", "terrace area", "terrace garden", "terrace floor")),
  ("ROOF", ("roof", "roof space", "roof area", "roof level", "roof deck", "roof deck area")),
  
  ("PORCH", ("porch", "verandah", "veranda", "front porch", "rear porch", "covered porch", "covered verandah", "covered veranda")),
  ("COURTYARD", ("courtyard", "court yard", "inner courtyard", "internal courtyard", "central courtyard", "open courtyard", "chowk", "angan", "aangan")),
  ("LAUNDRY", ("laundry", "laundry room", "laundry area", "washing area", "wash area", "utility room", "utility area", "utility")),
  
  ("SERVANT_QUARTER", ("servant room", "servant quarter", "servant quarters", "servant bedroom", "maid room", "maid quarter", "maid quarters",
    "domestic staff room", "domestic staff quarter")),
  ("DRIVER_QUARTER", ("driver room", "driver quarter", "driver quarters", "driver accommodation")),
  ("GUARD_ROOM", ("guard room", "security room", "security guard room", "watchman room", "watchman quarter", "guard house")),
  ("OFFICE", ("office", "office room", "workroom", "study", "study room", "home office", "work office", "meeting room", "conference room")),
  ("PRAYER", ("prayer room", "prayer", "namaz room", "salah room", "musalla", "mosque", "masjid")),
  ("LIBRARY", ("library", "book room", "reading room", "study library")),
  ("PLAYROOM", ("playroom", "play room", "kids playroom", "children playroom", "games room", "game room")),
  
  ("RECREATION", ("recreation room", "recreation", "entertainment room", "entertainment", "media room", "cinema room", "home theater", "home theatre",
    "game room", "games room")),
  ("GYM", ("gym", "gymnasium", "fitness room", "fitness area", "exercise room", "workout room")),
  ("DRESSING", ("dressing room", "dressing", "walk-in closet", "walk in closet", "walk-in wardrobe", "walk in wardrobe", "wardrobe room", "closet")),
  ("NURSERY", ("nursery", "baby room", "infant room", "nursery room")),
  
  ("MUMTY", ("mumty", "mumti", "mumtee", "stair mumty", "mumty room", "mumti room")),
  ("SHAFT", ("shaft", "service shaft", "utility shaft", "mep shaft", "mep shaft", "vertical shaft", "services shaft", "service riser", "riser")),
  ("DUCT", ("duct", "service duct", "mep duct", "utility duct", "ventilation duct", "air duct")),
  ("MECHANICAL", ("mechanical room", "mechanical", "plant room", "equipment room", "hvac room", "hvac plant", "chiller room", "boiler room", "pump room", "mechanical plant")),
  ("ELECTRICAL", ("electrical room", "electrical", "electric room", "transformer room", "switch room", "switchgear room", "substation", "generator room", "genset room", "electrical plant")),
  ("PLUMBING", ("plumbing room", "plumbing", "plumbing plant", "water pump room", "water tank room", "water treatment room")),
  ("FIRE_CONTROL", ("fire control room", "fire fighting room", "fire pump room", "fire pump", "fire command room", "fire control")),
  ("REFUSE", ("refuse room", "garbage room", "waste room", "bin room", "trash room", "waste storage")),
  ("COLD_STORAGE", ("cold room", "cold storage", "freezer room", "freezer", "refrigeration room")),
  ("BASEMENT", ("basement", "basement level", "basement floor")),
  
  ("ATTIC", ("attic", "attic room", "loft", "loft space")),
  ("PLANT", ("plant room", "plant area", "service plant", "plant space")),
  ("RECEPTION", ("reception", "reception area", "reception room", "front desk")),
  ("WAITING", ("waiting room", "waiting area", "waiting lounge")),
  ("CLASSROOM", ("classroom", "class room", "lecture room", "teaching room", "training room")),
  ("LABORATORY", ("laboratory", "laboratory room", "lab room", "lab")),
  ("RETAIL", ("retail", "retail unit", "shop", "shop unit", "showroom", "storefront")),
  ("RESTAURANT", ("restaurant", "dining hall", "cafe", "café", "cafeteria", "canteen")),
  ("WAREHOUSE", ("warehouse", "warehousing", "warehouse space", "distribution area")),
  ("WORKSHOP", ("workshop", "work shop", "fabrication shop", "maintenance workshop", "maintenance room")),
  ("LOADING", ("loading area", "loading bay", "loading dock", "loading dock area", "unloading area", "service bay")),
  ("SERVICE", ("service room", "service area", "service space", "back of house", "boh", "staff room", "staff area")),
  ("OPEN_AREA", ("open area", "open space", "open terrace", "open yard", "yard", "garden", "landscape area")),
  ("BALCONY", ("balcony", "balconies", "cantilever balcony", "projecting balcony")),
]

_EXTERNAL = {"BALCONY", "TERRACE", "PORCH", "COURTYARD", "ROOF", "OPEN_AREA"}

@dataclass
class ReadSpace:
  global_id: str
  name: str | None
  long_name: str | None
  number: str | None
  category: str
  usage_text: str | None
  is_external: bool
  level_global_id: str | None
  net_floor_area_mm2: Decimal | None
  gross_floor_area_mm2: Decimal | None
  perimeter_mm: Decimal | None
  height_mm: Decimal | None
  elevation_base_mm: Decimal | None
  geometry_kind: str
  footprint: dict | None
  properties: dict
  status: str
  issues: list = field(default_factory=list)

@dataclass
class ReadBoundary:
  space_global_id: str
  element_global_id: str
  kind: str
  side: str

@dataclass
class ReadRelation:
  from_global_id: str
  to_global_id: str
  relation: str

@dataclass
class SpatialReadResult:
  spaces: list = field(default_factory=list)
  boundaries: list = field(default_factory=list)
  relations: list = field(default_factory=list)
  issues: list = field(default_factory=list)

def classify_space(*texts) -> str:
  haystack = " " + " ".join(str(t).lower() for t in texts if t) + " "
  haystack = re.sub(r"[\s_\-:.,/]+", " ", haystack)
  for category, keywords in _CATEGORY_KEYWORDS:
    for kw in keywords:
      if re.search(rf"(?<![a-z]){re.escape(kw)}", haystack):
        return category
  return "UNKNOWN"

def _pick(flat: dict, names) -> float | None:
  for name in names:
    value = _num(flat.get(name))
    if value is not None and value > 0:
      return value
  return None

def _space_storey(space) -> str | None:
  node = space
  for _ in range(6):
    try:
      parent = ifcopenshell.util.element.get_container(node) or ifcopenshell.util.element.get_aggregate(node)
    except Exception:
      return None
    if parent is None:
      return None
    if parent.is_a("IfcBuildingStorey"):
      return parent.GlobalId
    node = parent
  return None

def _perimeter(points) -> float:
  n = len(points)
  return sum(math.dist(points[i], points[(i + 1) % n]) for i in range(n))

def _read_space(space, scales: _Scales, levels) -> ReadSpace:
  psets = ifcopenshell.util.element.get_psets(space, psets_only=True) or {}
  qtos = ifcopenshell.util.element.get_psets(space, qtos_only=True) or {}
  flat = _flatten_qtos(qtos)
  issues: list = []

  net = _pick(flat, ("NetFloorArea", "NetArea"))
  gross = _pick(flat, ("GrossFloorArea", "GrossArea"))
  net_mm2 = net * scales.area_m2 * 1_000_000.0 if net else None
  gross_mm2 = gross * scales.area_m2 * 1_000_000.0 if gross else None
  per = _pick(flat, ("NetPerimeter", "GrossPerimeter"))
  perimeter_mm = per * scales.mm_per_unit if per else None
  hgt = _pick(flat, ("FinishCeilingHeight", "Height", "NetHeight"))
  height_mm = hgt * scales.mm_per_unit if hgt else None

  geometry = None
  try:
    geometry = _extruded_geometry(space, "SPACE", scales)
  except Exception:
    geometry = None
  if geometry is not None and not (geometry.placement or {}).get("vertical"):
    geometry = None

  footprint = None
  base_mm = None
  if geometry is not None:
    pl = geometry.placement
    footprint = {"plan_mm": pl["plan_mm"], "z_min_mm": pl["z_min_mm"], "z_max_mm": pl["z_max_mm"]}
    base_mm = pl["z_min_mm"]
    if net_mm2 is None and geometry.profile_area_mm2:
      net_mm2 = geometry.profile_area_mm2
      issues.append(_issue("AREA_FROM_GEOMETRY", "info", "No Qto floor area; area taken from the space footprint."))
    if perimeter_mm is None and len(pl["plan_mm"]) >= 3:
      perimeter_mm = _perimeter(pl["plan_mm"])
    if height_mm is None:
      height_mm = geometry.depth_mm
  elif space.ObjectPlacement is not None:
    try:
      base_mm = float(ifcopenshell.util.placement.get_local_placement(space.ObjectPlacement)[2][3]) * scales.mm_per_unit
    except Exception:
      base_mm = None

  if net_mm2 is None and gross_mm2 is None:
    issues.append(_issue("SPACE_AREA_MISSING", "warning", "Space has no usable floor area."))
  kind = "EXTRUDED_PROFILE" if geometry is not None else ("QTO_ONLY" if (net_mm2 or gross_mm2) else "UNSUPPORTED")

  name = _clean(getattr(space, "Name", None))
  long_name = _clean(getattr(space, "LongName", None))
  object_type = _clean(getattr(space, "ObjectType", None))
  category = classify_space(name, long_name, object_type)
  common = psets.get("Pset_SpaceCommon") or {}
  external = category in _EXTERNAL or common.get("IsExternal") is True or \
    str(getattr(space, "PredefinedType", "") or "").upper() == "EXTERNAL"

  level = _space_storey(space) or _level_by_elevation(levels, base_mm)
  status = "WARNING" if any(i["severity"] == "warning" for i in issues) else "VALID"
  return ReadSpace(
    global_id=space.GlobalId, name=name, long_name=long_name, number=name, category=category,
    usage_text=object_type, is_external=bool(external), level_global_id=level,
    net_floor_area_mm2=_dec(net_mm2), gross_floor_area_mm2=_dec(gross_mm2), perimeter_mm=_dec(perimeter_mm),
    height_mm=_dec(height_mm), elevation_base_mm=_dec(base_mm), geometry_kind=kind, footprint=footprint,
    properties=_json_safe({**psets, **qtos}), status=status, issues=issues,
  )

def read_spatial(model, scales: _Scales, levels, known_gids: set[str]) -> SpatialReadResult:
  result = SpatialReadResult()
  by_step = {}
  for space in sorted(model.by_type("IfcSpace"), key=lambda s: s.id()):
    try:
      rs = _read_space(space, scales, levels)
    except Exception as exc:
      result.issues.append(
        _issue(
          "SPACE_READ_FAILED",
          "warning",
          f"IfcSpace {getattr(space, 'GlobalId', '<unknown>')} could not be read: "
          f"{type(exc).__name__}: {exc}",
        )
      )
      continue

    result.spaces.append(rs)
    by_step[space.id()] = rs.global_id

  seen = set()
  for rel in model.by_type("IfcRelSpaceBoundary"):
    try:
      space, element = rel.RelatingSpace, rel.RelatedBuildingElement
      if space is None or element is None:
        continue
      sg, eg = by_step.get(space.id()), getattr(element, "GlobalId", None)
      if sg is None or eg not in known_gids or (sg, eg) in seen:
        continue
      seen.add((sg, eg))
      physical = str(getattr(rel, "PhysicalOrVirtualBoundary", "") or "").upper()
      side = str(getattr(rel, "InternalOrExternalBoundary", "") or "").upper()
      result.boundaries.append(ReadBoundary(
        sg, eg, "VIRTUAL" if physical == "VIRTUAL" else "PHYSICAL",
        "INTERNAL" if side == "INTERNAL" else "EXTERNAL" if side.startswith("EXTERNAL") else "UNDEFINED"))
    except Exception:
      continue

  host_of_opening = {}
  for rel in model.by_type("IfcRelVoidsElement"):
    try:
      host_of_opening[rel.RelatedOpeningElement.id()] = rel.RelatingBuildingElement
    except Exception:
      continue
  pairs = set()
  
  for rel in model.by_type("IfcRelFillsElement"):
    try:
      host = host_of_opening.get(rel.RelatingOpeningElement.id())
      filler = rel.RelatedBuildingElement
      if host is None or filler is None:
        continue
      a, b = getattr(filler, "GlobalId", None), getattr(host, "GlobalId", None)
      if a in known_gids and b in known_gids and a != b and (a, b, "HOSTED_IN") not in pairs:
        pairs.add((a, b, "HOSTED_IN"))
    except Exception:
      continue
  
  for rel in model.by_type("IfcRelConnectsPathElements"):
    try:
      a, b = rel.RelatingElement.GlobalId, rel.RelatedElement.GlobalId
      a, b = sorted((a, b))
      if a in known_gids and b in known_gids and a != b:
        pairs.add((a, b, "CONNECTS"))
    except Exception:
      continue
  result.relations = [ReadRelation(a, b, r) for a, b, r in sorted(pairs)]
  return result