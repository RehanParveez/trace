from __future__ import annotations
import hashlib
import json

def _element_key(e) -> dict:
  return {
    "id": str(e.id), "t": e.ifc_type, "r": e.role,
    "l": str(e.level_id) if e.level_id else None,
    "k": e.geometry_kind, "p": e.profile, "pl": e.placement,
    "v": str(e.volume_mm3) if e.volume_mm3 is not None else None,
    "bmin": [str(v) for v in e.bbox_min_mm] if e.bbox_min_mm else None,
    "bmax": [str(v) for v in e.bbox_max_mm] if e.bbox_max_mm else None,
    "c": str(e.classification_confidence), "s": e.normalization_status,
  }

def compute_fingerprint(*, elements, mappings, profile_fingerprint: str, rule_set_ref: str,
  convention_code: str | None, engine_version: str, settings: dict) -> str:
  payload = {
    "elements": [_element_key(e) for e in sorted(elements, key=lambda e: str(e.id))],
    "mappings": [[m.ifc_type, m.work_item_code, str(m.confidence_base)]
      for m in sorted(mappings, key=lambda m: m.ifc_type)],
    "profile": profile_fingerprint,
    "rule_set": rule_set_ref,
    "convention": convention_code,
    "engine": engine_version,
    "settings": settings,
  }
  blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
  return hashlib.sha256(blob.encode("utf-8")).hexdigest()