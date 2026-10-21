from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import members as M
from app.modules.drawings_boq.takeoff.prep.details import norm_mark
from app.modules.drawings_boq.takeoff.prep.census import dense_flags
from app.modules.drawings_boq.takeoff.prep.texts import is_tag

NO_MEMBER, UNKNOWN_KIND = "NO_MEMBER", "UNKNOWN_KIND"
REJECTED, INVALID = "REJECTED", "INVALID"
MAX_TAGS = 200
MAX_POINTS_PER_TAG = 200
MAX_SET_ASIDE = 300

def _anchor(geometry) -> list | None:
  g = geometry or {}
  pts = g.get("points") or g.get("outer") or []
  clean = []
  for p in pts:
    try:
      clean.append((float(p[0]), float(p[1])))
    except (TypeError, ValueError, IndexError):
      continue
  if not clean:
    return None
  return [round(sum(p[0] for p in clean) / len(clean), 3), round(sum(p[1] for p in clean) / len(clean), 3)]

def _error_codes(notes) -> list:
  return [str(n.get("code")) for n in (notes or []) if isinstance(n, dict) and n.get("severity") == "error" and n.get("code")]

def reading_gaps(words: list, candidates: list) -> dict:
  read = {norm_mark(c.tag) for c in candidates if getattr(c, "tag", None)}
  flags = dense_flags(words) if words else []
  by: dict = {}
  for w, dense in zip(words, flags):
    if dense or not is_tag(w.text):
      continue
    key = norm_mark(w.text)
    if key in read:
      continue
    row = by.setdefault(key, {"tag": w.text.strip().upper(), "count": 0, "points": []})
    row["count"] += 1
    if len(row["points"]) < MAX_POINTS_PER_TAG:
      row["points"].append([round(w.cx, 3), round(w.cy, 3)])
      
  tags = []
  for key, row in by.items():
    category = M.category_of(row["tag"])
    tags.append({"tag": row["tag"], "category": category, "reason": NO_MEMBER if category else UNKNOWN_KIND, "count": row["count"], "points": row["points"]})
  tags.sort(key=lambda t: (t["reason"] != NO_MEMBER, -t["count"], t["tag"]))
  aside = []
  for c in candidates:
    codes = _error_codes(getattr(c, "notes", None))
    if c.decision == "REJECTED":
      reason = REJECTED
    elif c.status == "INVALID" or codes:
      reason = INVALID
    else:
      continue
  
    aside.append({"id": str(c.id), "label": c.label, "tag": c.tag, "category": c.category, "reason": reason, "codes": codes, "anchor": _anchor(c.geometry)})
  aside.sort(key=lambda a: (a["reason"], str(a["category"]), str(a["label"])))
  summary = {
    "tags": len(tags), "tag_marks": sum(t["count"] for t in tags),
    "no_member": sum(1 for t in tags if t["reason"] == NO_MEMBER), "unknown_kind": sum(1 for t in tags if t["reason"] == UNKNOWN_KIND),
    "set_aside": len(aside), "rejected": sum(1 for a in aside if a["reason"] == REJECTED), "invalid": sum(1 for a in aside if a["reason"] == INVALID),
    "tags_cut": max(0, len(tags) - MAX_TAGS), "set_aside_cut": max(0, len(aside) - MAX_SET_ASIDE),
  }
  return {"tags": tags[:MAX_TAGS], "set_aside": aside[:MAX_SET_ASIDE], "summary": summary}
