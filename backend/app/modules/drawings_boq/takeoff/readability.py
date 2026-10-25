from __future__ import annotations

READABLE, WITH_QUESTIONS, BADLY, NOT_READ, NOT_A_PLAN = "READABLE", "READ_WITH_QUESTIONS", "READ_BADLY", "NOT_READ", "NOT_A_PLAN"
RANK = {READABLE: 0, WITH_QUESTIONS: 1, BADLY: 2}
MAX_SHEETS_LISTED = 12

REASONS = {
  "TEXT_NOT_RECOVERED": (BADLY, "The lettering is drawn as outlines and could not be read, so the scale, marks and sizes printed on these sheets are missing."),
  "STAGE_FAILED": (BADLY, "A reading step failed and was skipped on these sheets, so its items are missing."),
  "SCALE_LOOKS_WRONG": (BADLY, "The doors and rooms drawn are not the size doors and rooms are built, so the scale used for these sheets is probably wrong."),
  "SCALE_CONFLICT": (WITH_QUESTIONS, "The sheet prints conflicting scale information."),
  "SCALE_UNVERIFIED": (WITH_QUESTIONS, "The scale is taken from the title block and not checked against a printed dimension."),
  "TEXT_FROM_PICTURE": (WITH_QUESTIONS, "The lettering was read from the picture of the sheet, so a mark or a figure may be misread."),
  "TIME_LIMIT": (WITH_QUESTIONS, "Reading took too long and some items may be missing."),
  "VALUES_DISAGREE": (WITH_QUESTIONS, "The drawing prints different values for the same thing."),
  "SHEET_KIND_UNKNOWN": (WITH_QUESTIONS, "The kind of sheet could not be told from its title."),
}
DISAGREE_NOTES = ("SLAB_THICKNESS_DISAGREES",)

def sheet_status(stats: dict | None, notes: list | None, scale_unverified: bool = False) -> dict:
  stats = stats or {}
  role = stats.get("sheet_role") or {}
  if role.get("advice") == "SKIP":
    return {"state": NOT_A_PLAN, "reasons": [], "role": role.get("role")}
  codes = {n.get("code") for n in (notes or []) if isinstance(n, dict)}
  pdf = stats.get("pdf_type") or {}
  found: list = []

  if pdf.get("type") == "VECTOR_OUTLINED":
    found.append("TEXT_FROM_PICTURE" if pdf.get("text_recovered") else "TEXT_NOT_RECOVERED")
  elif pdf.get("type") == "RASTER" or "SCAN_TEXT_READ" in codes:
    found.append("TEXT_FROM_PICTURE")
  if stats.get("stage_failures"):
    found.append("STAGE_FAILED")
  if (stats.get("scale_plausibility") or {}).get("status") == "IMPLAUSIBLE" or "SCALE_LOOKS_WRONG" in codes:
    found.append("SCALE_LOOKS_WRONG")
  if "SCALE_CONFLICT" in codes:
    found.append("SCALE_CONFLICT")
  if scale_unverified and not stats.get("scale_settled_by_schedule"):
    found.append("SCALE_UNVERIFIED")
  if "TIME_LIMIT" in codes:
    found.append("TIME_LIMIT")
  if any(c in codes for c in DISAGREE_NOTES):
    found.append("VALUES_DISAGREE")
  if role.get("role") == "UNKNOWN":
    found.append("SHEET_KIND_UNKNOWN")
  worst = max((RANK[REASONS[c][0]] for c in found), default=0)
  return {"state": next(k for k, v in RANK.items() if v == worst), "reasons": found, "role": role.get("role")}

def drawing_status(extractions: list) -> dict:
  if not extractions:
    return {"state": NOT_READ, "sheets_read": 0, "sheets_not_plans": 0, "reasons": []}
  by_reason: dict = {}
  worst = 0
  not_plans = 0

  for e in extractions:
    s = sheet_status(e.get("stats"), e.get("notes"), bool(e.get("scale_unverified")))
    if s["state"] == NOT_A_PLAN:
      not_plans += 1
      continue
    worst = max(worst, RANK[s["state"]])
    for code in s["reasons"]:
      by_reason.setdefault(code, []).append(e.get("page_no"))

  reasons = []
  for code, pages in by_reason.items():
    level, text = REASONS[code]
    pages = sorted(p for p in pages if p is not None)
    reasons.append({"code": code, "level": level, "text": text, "sheets": len(pages), "pages": pages[:MAX_SHEETS_LISTED]})
  reasons.sort(key=lambda r: (-RANK[r["level"]], -r["sheets"], r["code"]))
  return {"state": next(k for k, v in RANK.items() if v == worst), "sheets_read": len(extractions), "sheets_not_plans": not_plans, "reasons": reasons}
