from __future__ import annotations
import json
import hashlib

def _element_key(e) -> dict:
  key = {
    "id": str(e.id), "t": e.ifc_type, "r": e.role,
    "l": str(e.level_id) if e.level_id else None,
    "k": e.geometry_kind, "p": e.profile, "pl": e.placement,
    "v": str(e.volume_mm3) if e.volume_mm3 is not None else None,
    "bmin": [str(v) for v in e.bbox_min_mm] if e.bbox_min_mm else None,
    "bmax": [str(v) for v in e.bbox_max_mm] if e.bbox_max_mm else None,
    "c": str(e.classification_confidence), "s": e.normalization_status,
    "m": getattr(e, "material_class", None),
    "th": str(e.thickness_mm) if getattr(e, "thickness_mm", None) is not None else None,
    "mt": getattr(e, "material_text", None),
    "vc": getattr(e, "volume_check", None),
    "ly": getattr(e, "layers", None),
    "gm": getattr(e, "generic_material", False),
  }
  if getattr(e, "rebar", None):
    key["rb"] = e.rebar
  if getattr(e, "mesh_volume_mm3", None):
    key["mv"] = e.mesh_volume_mm3
  return key

def compute_fingerprint(*, elements, mappings, profile_fingerprint: str, rule_set_ref: str, convention_code: str | None, engine_version: str, settings: dict,
  convention_params: dict | None = None, spatial: dict | None = None) -> str:
  
  payload = {
    "elements": [_element_key(e) for e in sorted(elements, key=lambda e: str(e.id))],
    "mappings": [[m.ifc_type, m.work_item_code, str(m.confidence_base)]
      for m in sorted(mappings, key=lambda m: m.ifc_type)],
    "profile": profile_fingerprint,
    "rule_set": rule_set_ref,
    "convention": convention_code,
    "convention_params": convention_params or {},
    "engine": engine_version,
    "settings": settings,
    "spatial": spatial or {},
  }
  blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
  return hashlib.sha256(blob.encode("utf-8")).hexdigest()

def _short(value) -> str:
  return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()[:10]

def fingerprint_parts(*, elements, mappings, profile_fingerprint: str, rule_set_ref: str, convention_code: str | None, engine_version: str, settings: dict,
  convention_params: dict | None = None, spatial: dict | None = None) -> dict:
  """A short hash for each part of the run input, so a changed input can be named. It does not change the fingerprint itself."""
  parts = {
    "elements": _short([_element_key(e) for e in sorted(elements, key=lambda e: str(e.id))]),
    "mappings": _short([[m.ifc_type, m.work_item_code, str(m.confidence_base)] for m in sorted(mappings, key=lambda m: m.ifc_type)]),
    "profile": _short(profile_fingerprint),
    "rule_set": _short(rule_set_ref),
    "convention": _short([convention_code, convention_params or {}]),
    "engine": _short(engine_version),
    "settings": _short(settings),
  }
  for key, value in sorted((spatial or {}).items()):
    if key == "takeoff" and isinstance(value, dict):
      for sub, sub_value in sorted(value.items()):
        parts[f"takeoff.{sub}"] = _short(sub_value)
    else:
      parts[f"spatial.{key}"] = _short(value)
  return parts

def differing_parts(before: dict | None, now: dict | None) -> list:
  """The names of the parts whose hash differs; empty when nothing was recorded to compare with."""
  if not before or not now:
    return []
  return sorted(k for k in set(before) | set(now) if before.get(k) != now.get(k))
