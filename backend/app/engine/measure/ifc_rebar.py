from __future__ import annotations
from decimal import Decimal
from dataclasses import dataclass, field
from uuid import uuid5
from app.engine.measure.models import Rejected, LedgerEntry, Solid
import numpy as np
from app.engine.measure.rebar import REBAR_WORK_ITEM, estimate_band, pick_rule, role_family
from app.engine.measure.steel import STEEL_DENSITY_KG_M3, STEEL_MAPPING_CONFIDENCE, STEEL_UNCERTAIN_FACTOR
from app.engine.measure.units import q4, q6

ZERO, ONE = Decimal("0"), Decimal("1")
PI = Decimal("3.14159265358979323846")
MM3_PER_M3 = Decimal("1000000000")

FORMULA_IFC_BAR = "IFC_BAR_WEIGHT"
IFC_BAR_FORMULA_UNITS = {FORMULA_IFC_BAR: "kg"}
NO_DIAMETER, NO_LENGTH = "IFC_BAR_NO_DIAMETER", "IFC_BAR_NO_LENGTH"
GEOMETRY, DECLARED = "GEOMETRY", "DECLARED"

@dataclass(frozen=True)
class IfcBarResult:
  solids: list = field(default_factory=list)
  ledger: list = field(default_factory=list)
  rejected: list = field(default_factory=list)
  hosts: frozenset = frozenset()
  stats: dict = field(default_factory=dict)
  floors: dict = field(default_factory=dict)

def _dec(value) -> Decimal | None:
  try:
    number = Decimal(repr(float(value)))
  except Exception:
    return None
  return number if number > ZERO else None

def bar_weight_kg(dia_mm: Decimal, length_mm: Decimal) -> Decimal:
  """Area of the round section times the centre-line length times the density of steel: pi/4 x d^2 x L x 7850. The length is the total for every bar of that diameter."""
  return q6(PI * dia_mm * dia_mm / 4 * length_mm / MM3_PER_M3 * STEEL_DENSITY_KG_M3)

def _groups_of(rb: dict) -> tuple[str, list, dict]:
  drawn = rb.get("groups") or []
  flags = {"count_assumed": False}

  if drawn:
    groups = []
    for g in drawn:
      dia, length = _dec(g.get("dia_mm")), _dec(g.get("length_mm"))
      if dia is None or length is None:
        continue
      groups.append((q6(dia), int(g.get("bars") or 1), q6(length)))
    if groups:
      return GEOMETRY, groups, flags

  dia, length = _dec(rb.get("dia_mm")), _dec(rb.get("length_mm"))
  if dia is None:
    return DECLARED, [], {"missing": NO_DIAMETER}
  if length is None:
    return DECLARED, [], {"missing": NO_LENGTH}
  count = rb.get("count") or rb.get("disks")
  if not count:
    count = 1
    flags["count_assumed"] = True
  return DECLARED, [(q6(dia), int(count), q6(length * int(count)))], flags

HOST_TOLERANCE_MM = 1.0

def _box_of(rb: dict):
  box = (rb or {}).get("bbox_mm") or {}
  try:
    lo, hi = [float(v) for v in box["min"]], [float(v) for v in box["max"]]
  except (KeyError, TypeError, ValueError):
    return None
  return (lo, hi) if len(lo) == 3 and len(hi) == 3 else None

def host_candidates(elements: list) -> list:
  """The members a bar can sit in: anything with a volume and a box that is not itself a bar or a steel member, smallest box first."""
  out = []
  for e in elements:
    if e.role == "REBAR" or not e.bbox_min_mm or not e.bbox_max_mm or e.material_class == "STEEL":
      continue
    if e.volume_mm3 is None or e.volume_mm3 <= 0:
      continue
    out.append(e)

  def volume(e) -> float:
    return float(np.prod([float(h) - float(l) for l, h in zip(e.bbox_min_mm, e.bbox_max_mm)]))

  return sorted(out, key=lambda e: (volume(e), e.ifc_global_id or "", str(e.id)))

def assign_hosts(bars: list, candidates: list) -> dict:
  """{bar element id: (member, how)}. A bar sits in the smallest member box that holds the whole of its drawn bars; when no box does, in the smallest box that holds the centre of them. Both within 1 mm. The model's element ids are not used to choose."""
  if not candidates:
    return {}

  lo = np.array([[float(v) for v in e.bbox_min_mm] for e in candidates])
  hi = np.array([[float(v) for v in e.bbox_max_mm] for e in candidates])
  out: dict = {}
  for bar in bars:
    box = _box_of(bar.rebar)
    if box is None:
      continue

    blo, bhi = np.array(box[0]), np.array(box[1])
    whole = np.flatnonzero(np.all(lo <= blo + HOST_TOLERANCE_MM, axis=1) & np.all(hi >= bhi - HOST_TOLERANCE_MM, axis=1))
    how = "position_box"
    if whole.size == 0:
      centre = (blo + bhi) / 2.0
      whole = np.flatnonzero(np.all(lo - HOST_TOLERANCE_MM <= centre, axis=1) & np.all(hi + HOST_TOLERANCE_MM >= centre, axis=1))
      how = "position_centre"
    if whole.size:
      out[bar.id] = (candidates[int(whole[0])], how)
  return out

def host_verdict(host, kg: Decimal, m3: Decimal | None, rules: tuple, scheduled: frozenset) -> dict:
  """COVERED: the model's bars reach the low end of the steel band for this kind of member, so they stand for its steel and no estimate is added.
  PARTIAL: they fall short of it, so the member keeps its estimate and the model's bars are its floor. The other states leave the bars billed as they are: the member has a bar schedule (SCHEDULED), was not measured (NOT_MEASURED), or has no band to compare with (NO_BAND)."""
  family = role_family(host.role)
  out = {"state": "NO_BAND", "family": family, "kg_per_m3": None, "band_low": None, "m3": None}
  if family is not None and family in scheduled:
    out["state"] = "SCHEDULED"
    return out

  if not m3 or m3 <= ZERO:
    out["state"] = "NOT_MEASURED"
    return out
  out["m3"] = q6(m3)
  rule = pick_rule(rules, family, host.role, "ESTIMATE", allow_all=False) if family else None
  band = estimate_band(family, rule.extra_config) if rule is not None and host.material_class != "MASONRY" else None
  if band is None:
    return out

  per = q4(kg / m3)
  out.update({"kg_per_m3": per, "band_low": band["low"], "state": "COVERED" if per >= band["low"] else "PARTIAL"})
  return out

def measure_ifc_bars(ctx, elements: list, tolerance: float, member_solids=(), member_ledger=(), profile=None, rebar_inputs=None) -> IfcBarResult:
  """One steel row per bar element the model carries (IfcReinforcingBar), weighed from the bars it draws: every swept disk is one bar, grouped by diameter, weight = pi/4 x d^2 x total length x 7850. Where the model draws no bars, the declared diameter and length per bar are used. An element with no diameter or no length is listed as rejected with its own code, never given a guess."""
  bars = [e for e in elements if e.role == "REBAR"]
  read = [e for e in bars if getattr(e, "rebar", None)]
  by_gid = {e.ifc_global_id: e for e in elements if e.ifc_global_id}
  tol = Decimal(repr(float(tolerance)))
  solids: list = []
  ledger: list = []
  rejected: list = []
  hosts: set = set()
  total_kg = total_len = ZERO

  piece_count = 0
  by_dia: dict = {}
  by_family: dict = {}
  flags = {"no_host": 0, "length_from_geometry": 0, "diameter_derived": 0, "area_mismatch": 0, "count_assumed": 0, "length_mismatch": 0, "file_weight_mismatch": 0}
  file_bars = 0
  file_kg = same_bars_kg = ZERO
  cmp_bars = 0
  cmp_geo = cmp_decl = ZERO

  bar_kg: dict = {}
  for el in read:
    _, found, _ = _groups_of(el.rebar)
    if found:
      bar_kg[el.id] = (q6(sum((bar_weight_kg(d, t) for d, _, t in found), ZERO)), sum(n for _, n, _ in found))
  loose = [e for e in read if e.id in bar_kg and not (e.rebar.get("host_global_id") and e.rebar.get("host_global_id") in by_gid)]
  by_position = assign_hosts(loose, host_candidates(elements))

  placed: dict = {}
  for el in read:
    if el.id not in bar_kg:
      continue
    declared = by_gid.get(el.rebar.get("host_global_id")) if el.rebar.get("host_global_id") else None
    if declared is not None:
      placed[el.id] = (declared, "relation")
    elif el.id in by_position:
      placed[el.id] = by_position[el.id]
  held: dict = {}

  for bar_id, (member, _) in placed.items():
    slot = held.setdefault(member.id, {"host": member, "kg": ZERO, "bars": 0, "elements": 0})
    slot["kg"] += bar_kg[bar_id][0]
    slot["bars"] += bar_kg[bar_id][1]
    slot["elements"] += 1
  by_solid = {s.id: s for s in member_solids}

  net_m3: dict = {}
  for row in member_ledger:
    owner = by_solid.get(row.solid_id)
    if row.formula_code == "SOLID_NET_VOLUME" and owner is not None and owner.element_id is not None:
      net_m3[owner.element_id] = net_m3.get(owner.element_id, ZERO) + row.quantity
      
  rules = tuple(getattr(profile, "reinforcement_rules", ()) or ())
  scheduled = frozenset(f for f in (role_family(r.role) for r in (getattr(rebar_inputs, "rows", ()) or ())) if f)
  verdicts = {k: host_verdict(v["host"], v["kg"], net_m3.get(k), rules if profile is not None else (), scheduled) for k, v in held.items()}
  floors = {k: v["kg"] for k, v in held.items() if verdicts[k]["state"] == "PARTIAL"}
  absorbed = 0

  for el in sorted(read, key=lambda e: str(e.id)):
    rb = el.rebar
    basis, groups, gflags = _groups_of(rb)
    if not groups:
      if gflags.get("missing") == NO_DIAMETER:
        rejected.append(Rejected(el.id, el.ifc_type, NO_DIAMETER, "The bar gives no diameter (NominalDiameter, a property set value, a cross-section area or a drawn bar); not weighed."))
      else:
        rejected.append(Rejected(el.id, el.ifc_type, NO_LENGTH, "The bar gives no length (a drawn centre line that can be measured, BarLength, or a property or quantity value); not weighed."))
      continue

    weights = [bar_weight_kg(d, total) for d, _, total in groups]
    kg = q6(sum(weights, ZERO))
    nbars = sum(n for _, n, _ in groups)
    length_mm = q6(sum((t for _, _, t in groups), ZERO))
    length_m = q6(length_mm / 1000)
    dia_source = "SweptDisk" if basis == GEOMETRY else rb.get("dia_source")
    derived_dia = dia_source == "CrossSectionArea"
    count_assumed = bool(gflags.get("count_assumed"))
    factor = STEEL_UNCERTAIN_FACTOR if (derived_dia or count_assumed) else ONE
    confidence = q4(max(ZERO, min(ONE, min(STEEL_MAPPING_CONFIDENCE, el.classification_confidence) * factor)))

    host, host_source = placed.get(el.id, (None, None))
    verdict = verdicts.get(host.id) if host is not None else None
    if verdict is not None and verdict["state"] == "PARTIAL":
      absorbed += 1
      continue

    family = role_family(host.role) if host is not None else None
    level_id = el.level_id or (host.level_id if host is not None else None)
    group_name = rb.get("group_name")
    if host is None:
      flags["no_host"] += 1
    elif verdict["state"] == "COVERED":
      hosts.add(host.id)

    warnings: list = []
    if basis == GEOMETRY:
      warnings.append("IFC_BAR_LENGTH_FROM_GEOMETRY")
      flags["length_from_geometry"] += 1
      declared_length, disks = _dec(rb.get("length_mm")), rb.get("disks")
      if declared_length is not None and disks:
        expected = declared_length * int(disks)
        cmp_bars += int(disks); cmp_geo += length_mm; cmp_decl += expected
        if abs(length_mm - expected) / expected > tol:
          warnings.append("IFC_BAR_LENGTH_MISMATCH")
          flags["length_mismatch"] += 1

    if derived_dia:
      warnings.append("IFC_BAR_DIAMETER_DERIVED")
      flags["diameter_derived"] += 1
    if count_assumed:
      warnings.append("IFC_BAR_COUNT_ASSUMED")
      flags["count_assumed"] += 1
    if host is None:
      warnings.append("IFC_BAR_NO_HOST")
    given_area = _dec(rb.get("area_mm2"))
    declared_dia = _dec(rb.get("dia_mm"))

    if basis == DECLARED:
      first = groups[0][0]
      area = q6(PI * first * first / 4)
      if given_area is not None and dia_source == "NominalDiameter" and abs(given_area - area) / area > tol:
        warnings.append("IFC_BAR_AREA_MISMATCH")
        flags["area_mismatch"] += 1
    elif declared_dia is not None and rb.get("dia_source") == "NominalDiameter" and len(groups) == 1 and abs(declared_dia - groups[0][0]) / groups[0][0] > tol:
      warnings.append("IFC_BAR_AREA_MISMATCH")
      flags["area_mismatch"] += 1
    given_kg = _dec(rb.get("file_kg"))
    if given_kg is not None:
      file_bars += nbars
      file_kg += given_kg
      same_bars_kg += kg
      if abs(given_kg - kg) / given_kg > tol:
        warnings.append("IFC_BAR_FILE_WEIGHT_MISMATCH")
        flags["file_weight_mismatch"] += 1

    solid = Solid(
      id=uuid5(ctx.run_id, f"solid|ifc-bar|{el.id}"), element_id=el.id, ifc_type=el.ifc_type, role="REBAR", level_id=level_id,
      geometry_kind=el.geometry_kind or "QTO_ONLY", classification_confidence=el.classification_confidence, confidence_factor=factor,
      component_type="REBAR", material_grade=rb.get("grade"), gross_length_m=length_m, count=nbars)

    group_rows = [{"dia_mm": str(d), "bars": n, "length_mm": str(t), "kg": str(w)} for (d, n, t), w in zip(groups, weights)]
    inputs = {
      "basis": basis, "groups": group_rows, "bars": nbars, "dia_source": dia_source,
      "length_source": "Directrix" if basis == GEOMETRY else rb.get("length_source"),
      "density_kg_m3": str(STEEL_DENSITY_KG_M3), "grade": rb.get("grade"),
      "host": {"element_id": str(host.id), "global_id": host.ifc_global_id, "name": host.name or rb.get("host_name"), "role": host.role,
        "family": family, "found_by": host_source, "state": verdict["state"],
        "model_kg_per_m3": str(verdict["kg_per_m3"]) if verdict["kg_per_m3"] is not None else None,
        "band_low_kg_per_m3": str(verdict["band_low"]) if verdict["band_low"] is not None else None} if host is not None else None,
      "group_name": group_name,
      "count_source": ("assumed" if count_assumed else (rb.get("count_source") or ("Disks" if rb.get("disks") else None))) if basis == DECLARED else "Disks",
      "declared_length_mm": str(q6(_dec(rb.get("length_mm")))) if _dec(rb.get("length_mm")) is not None else None,
      "file_kg": str(q6(given_kg)) if given_kg is not None else None, "file_kg_source": rb.get("file_kg_source") if given_kg is not None else None,
    }

    if basis == DECLARED:
      inputs["geometry_kind"] = "QTO_ONLY"
    steps: list = []
    for (d, n, t), w in zip(groups, weights):
      steps.append({"op": "bar_group", "dia_mm": str(d), "bars": n, "length_mm": str(t), "section_mm2": str(q6(PI * d * d / 4)), "kg": str(w)})
    steps.append({"op": "density", "kg_per_m3": str(STEEL_DENSITY_KG_M3)})
    steps.append({"op": "weight", "kg": str(kg)})
    solids.append(solid)
    ledger.append(LedgerEntry(
      solid_id=solid.id, element_id=el.id, level_id=level_id, work_item_code=REBAR_WORK_ITEM, quantity=kg, unit="kg",
      material_grade=rb.get("grade"), confidence=confidence, formula_code=FORMULA_IFC_BAR,
      trace={"engine_version": ctx.engine_version, "convention": ctx.convention_code, "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
        "rounding": "half_up,6dp", "formula_code": FORMULA_IFC_BAR, "inputs": inputs, "steps": steps, "net": {"kg": str(kg)}},
      warnings=tuple(dict.fromkeys(warnings))))

    total_kg += kg
    total_len += length_m
    piece_count += nbars
    for (d, n, t), w in zip(groups, weights):
      key = f"{d.normalize():f}"
      slot = by_dia.setdefault(key, {"bars": 0, "kg": ZERO, "length_m": ZERO})
      slot["bars"] += n; slot["kg"] += w; slot["length_m"] += q6(t / 1000)
    fam = family or "NO_HOST"
    by_family[fam] = by_family.get(fam, ZERO) + kg

  stats = {
    "bars": len(bars), "bar_count": piece_count, "bars_without_data": len(bars) - len(read), "measured": len(ledger),
    "no_diameter": sum(1 for r in rejected if r.code == NO_DIAMETER), "no_length": sum(1 for r in rejected if r.code == NO_LENGTH),
    "kg": str(q6(total_kg)), "tonnes": str(q4(total_kg / 1000)), "length_m": str(q6(total_len)), "hosts": len(hosts),
    "by_dia": {k: {"bars": v["bars"], "kg": str(q6(v["kg"])), "length_m": str(q6(v["length_m"]))} for k, v in sorted(by_dia.items(), key=lambda kv: Decimal(kv[0]))},
    "by_family_kg": {k: str(q6(v)) for k, v in sorted(by_family.items())},
    **flags,
    "declared_length": {
      "bars": cmp_bars, "drawn_m": str(q6(cmp_geo / 1000)), "declared_m": str(q6(cmp_decl / 1000)),
      "difference_pct": str(q4((cmp_geo - cmp_decl) / cmp_decl * 100)) if cmp_decl > ZERO else None,
    },
    "file_weight": {
      "bars": file_bars, "file_kg": str(q6(file_kg)), "computed_kg": str(q6(same_bars_kg)),
      "difference_pct": str(q4((same_bars_kg - file_kg) / file_kg * 100)) if file_kg > ZERO else None,
    },
  }
  partial = sorted(((k, v) for k, v in verdicts.items() if v["state"] == "PARTIAL"), key=lambda kv: -held[kv[0]]["kg"])
  states: dict = {}
  for v in verdicts.values():
    states[v["state"]] = states.get(v["state"], 0) + 1
  how: dict = {}
  for _, found_by in placed.values():
    how[found_by] = how.get(found_by, 0) + 1
    
  stats.update({
    "absorbed": absorbed, "hosts_with_bars": len(held), "host_states": dict(sorted(states.items())), "host_found_by": dict(sorted(how.items())),
    "partial": {
      "hosts": len(partial), "bars": sum(held[k]["bars"] for k, _ in partial), "modelled_kg": str(q6(sum((held[k]["kg"] for k, _ in partial), ZERO))),
      "items": [{"name": held[k]["host"].name, "role": held[k]["host"].role, "bars": held[k]["bars"], "modelled_kg": str(q6(held[k]["kg"])),
        "m3": str(v["m3"]), "kg_per_m3": str(v["kg_per_m3"]), "band_low": str(v["band_low"])} for k, v in partial[:30]],
    },
  })
  return IfcBarResult(solids=solids, ledger=ledger, rejected=rejected, hosts=frozenset(hosts), stats=stats, floors=floors)

def ifc_bar_check(solids: list, ledger: list) -> list[str]:
  by_id = {s.id: s for s in solids}
  failures: list[str] = []

  for r in ledger:
    if r.formula_code != FORMULA_IFC_BAR:
      continue
    s = by_id.get(r.solid_id)
    if s is None:
      failures.append(f"IFC bar row has no solid ({r.solid_id})")
      continue

    inputs = (r.trace or {}).get("inputs") or {}
    try:
      expected = q6(sum((bar_weight_kg(Decimal(g["dia_mm"]), Decimal(g["length_mm"])) for g in inputs["groups"]), ZERO))
    except Exception:
      failures.append(f"IFC bar row {r.solid_id} has no diameters and lengths in its trace")
      continue
    if r.unit != "kg" or r.work_item_code != REBAR_WORK_ITEM:
      failures.append(f"IFC bar row {r.solid_id} is not steel in kg")
    elif abs(r.quantity - expected) > Decimal("0.000004"):
      failures.append(f"IFC bar weight {r.quantity} != {expected} from its bars on solid {r.solid_id}")
  return failures
