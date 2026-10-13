from __future__ import annotations

SCOPE_KEY = "scope_drawings"

def _iso(value) -> str | None:
  return value.isoformat() if value is not None else None

def scope_entry(drawing) -> dict:
  fmt = getattr(drawing.format, "value", drawing.format)
  return {
    "drawing_id": str(drawing.id),
    "filename": drawing.original_filename,
    "format": str(fmt),
    "revision_label": drawing.revision_label,
    "revision_group_id": str(drawing.revision_group_id),
    "file_size_bytes": int(drawing.file_size_bytes or 0),
    "uploaded_at": _iso(getattr(drawing, "created_at", None)),
    "parsed_at": _iso(getattr(drawing, "parsed_at", None)),
  }

def build_scope_snapshot(drawings) -> list[dict]:
  entries = [scope_entry(d) for d in drawings]
  return sorted(entries, key=lambda e: (e["filename"].lower(), e["drawing_id"]))