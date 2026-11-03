from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.extract import floor_overlap as FO
from app.modules.drawings_boq.takeoff.proof import known_facts as KF
from app.modules.drawings_boq.takeoff.proof import closure_checks as CC
from app.modules.drawings_boq.takeoff.extract.crosschecks import _live, _sheet_floor

KINDS = ("OPENING_COUNT", "WALL_TOTAL", "LEGEND_COUNT", "BEAM_SIZE", *CC.CHECKS)
COPIES = ("PLAN", "KEY_PLAN")
WALL_BANDS_MM = {4.5: (90.0, 130.0), 9.0: (200.0, 260.0)}
WALL_TOL_PCT = 3.0
BEAM_TOL_MM = 13.0
FT_PER_M = 3.280839895
FRACTIONS = {"½": ".5", "¼": ".25", "¾": ".75"}

def _mark(text) -> str:
  return re.sub(r"[^A-Z0-9]", "", str(text or "").upper())

def source_problems(f: dict) -> list:
  s = f.get("source")
  if not isinstance(s, dict):
    return ["has no source: {pdf, page}"]
  out = []
  
  if not str(s.get("pdf") or "").lower().endswith(".pdf"):
    out.append("source.pdf must name a drawing PDF (a workbook cell is not a fact)")
  page = s.get("page")
  if isinstance(page, bool) or not isinstance(page, int) or page < 1:
    out.append("source.page must be a page number")
  return out

def _result(text: str, status: str, expected, found, message: str, pages: list) -> dict:
  return {"text": text, "status": status, "expected": expected, "found": found, "message": message, "pages": sorted(set(pages))}

def _verdict(text: str, want, got, noun: str, pages: list, tol: float = 0.0) -> dict:
  if got == 0 and want != 0:
    return _result(text, KF.MISSING, want, 0, f"No {noun} was read.", pages)
  if abs(got - want) <= tol * max(abs(want), 1e-9):
    return _result(text, KF.PASS, want, got, f"{got:g} {noun}: as stated.", pages)
  d = got - want
  return _result(text, KF.FAIL, want, got, f"{want:g} {noun} stated; {got:g} read ({abs(d):g} {'more' if d > 0 else 'fewer'}).", pages)

def _opening_floor(c, sheet_floor):
  return FO.level_of(c) or (c.facts or {}).get("level_hint") or sheet_floor

def opening_count(read: list, f: dict) -> dict:
  floor = KF.floor_key(f["floor"])
  copy = str(f.get("copy") or "PLAN").upper()
  if copy not in COPIES:
    raise ValueError(f"copy must be one of {', '.join(COPIES)}")
  mark, want = _mark(f["mark"]), int(f["count"])
  
  got, pages = 0, []
  for sh in read:
    sf = _sheet_floor(sh)
    for c in sh["candidates"]:
      if c.category not in ("DOOR", "WINDOW") or _mark(c.tag) != mark or _opening_floor(c, sf) != floor:
        continue
      aside = (c.facts or {}).get("set_aside") or {}
      if copy == "PLAN" and _live(c) or copy == "KEY_PLAN" and aside.get("by") == "FLOOR_CHOICE":
        got += int(c.count or 1)
        pages.append(sh["page_no"])
  return _verdict(f"opening {f['mark']} x{want} on the {floor.title()} floor ({copy.lower().replace('_', ' ')})", want, got, f"{f['mark']} on the {floor.title()} {copy.lower().replace('_', ' ')}", pages)

def wall_total(read: list, f: dict) -> dict:
  floor = KF.floor_key(f["floor"])
  thick = float(f["thickness_in"])
  band = next((b for k, b in WALL_BANDS_MM.items() if abs(k - thick) < 0.01), None)
  if band is None:
    raise ValueError(f"thickness_in must be one of {', '.join(f'{k:g}' for k in WALL_BANDS_MM)}")
  want = float(f["length_ft"])
  tol = float(f["tolerance_pct"] if f.get("tolerance_pct") is not None else WALL_TOL_PCT) / 100.0
  
  best, pages = 0.0, []
  for sh in read:
    sf = _sheet_floor(sh)
    sheet = 0.0
    for c in sh["candidates"]:
      fa = c.facts or {}
      mm = (c.params or {}).get("thickness_mm") or fa.get("thickness_mm") or 0
      if c.category != "WALL" or not _live(c) or not fa.get("length_cc_m") or fa.get("electrical") or not band[0] <= float(mm) <= band[1] or _opening_floor(c, sf) != floor:
        continue
      sheet += float(fa["length_cc_m"]) * int(c.count or 1)
    if sheet > best:
      best, pages = sheet, [sh["page_no"]]
      
  got = round(best * FT_PER_M, 2)
  text = f"wall run {thick:g} in on the {floor.title()} floor {want:g} ft"
  if got == 0:
    return _result(text, KF.MISSING, want, 0, f"No {thick:g} in wall was read on the {floor.title()} floor.", [])
  off = (got - want) / want
  ok = abs(off) <= tol
  return _result(text, KF.PASS if ok else KF.FAIL, want, got, f"{got:g} ft of {thick:g} in wall read on the {floor.title()} floor, {off * 100:+.1f}% from {want:g}: {'within' if ok else 'outside'} {tol * 100:g}%.", pages)

def legend_count(read: list, f: dict) -> dict:
  floor = KF.floor_key(f["floor"])
  words = [w for w in re.split(r"\s+", str(f["description"]).upper().strip()) if w]
  want = int(f["count"])
  best, pages = 0, []
  
  for sh in read:
    sheet = 0
    for c in sh["candidates"]:
      fa = c.facts or {}
      name = f"{fa.get('electrical') or ''} {fa.get('symbol_text') or ''}".upper()
      if not fa.get("electrical") or not _live(c) or not all(w in name for w in words) or KF.floor_key(fa.get("electrical_floor")) != floor:
        continue
      sheet += int(c.count or 1)
    if sheet > best:
      best, pages = sheet, [sh["page_no"]]
  return _verdict(f"legend {str(f['description']).lower()} x{want} on the {floor.title()} floor", want, best, f"{str(f['description']).lower()} on the {floor.title()} floor", pages)

def _inches(text: str) -> float:
  t = str(text)
  for k, v in FRACTIONS.items():
    t = t.replace(k, v)
  return float(re.sub(r"[^0-9.]", "", t))

def beam_size(read: list, f: dict) -> dict:
  mark = _mark(f["mark"])
  parts = [p for p in re.split(r"x", str(f["printed"]).lower().replace("×", "x")) if p.strip()]
  if len(parts) != 2:
    raise ValueError("printed must be width x depth, for example 12\"x13½\"")
  w, d = (_inches(p) * 25.4 for p in parts)
  text = f"beam {f['mark']} {str(f['printed'])}"
  
  seen = []
  for sh in read:
    for c in sh["candidates"]:
      p = c.params or {}
      if c.category == "BEAM" and _mark(c.tag) == mark and p.get("width_mm") and p.get("depth_mm") and _live(c):
        seen.append((sh["page_no"], float(p["width_mm"]), float(p["depth_mm"])))
        
  if not seen:
    return _result(text, KF.MISSING, str(f["printed"]), None, f"No beam marked {f['mark']} was read with a size.", [])
  shown = sorted({f"{a / 25.4:g}\" x {b / 25.4:g}\"" for _p, a, b in seen})
  pages = [p for p, _a, _b in seen]
  if any(abs(a - w) <= BEAM_TOL_MM and abs(b - d) <= BEAM_TOL_MM for _p, a, b in seen):
    return _result(text, KF.PASS, str(f["printed"]), shown, f"{f['mark']} read as {', '.join(shown)}: as printed.", pages)
  return _result(text, KF.FAIL, str(f["printed"]), shown, f"{f['mark']} was read as {', '.join(shown)}; {f['printed']} is printed.", pages)

CHECKS = {"OPENING_COUNT": opening_count, "WALL_TOTAL": wall_total, "LEGEND_COUNT": legend_count, "BEAM_SIZE": beam_size, **CC.CHECKS}

def check(read: list, f: dict, index: int) -> dict:
  kind = str(f.get("kind") or "").upper()
  try:
    return CHECKS[kind](read, f)
  except (KeyError, TypeError, ValueError) as e:
    return {"text": f"fact {index + 1} ({kind} {f.get('mark') or f.get('description') or ''})".strip(), "status": "INVALID", "expected": None, "found": None, "message": f"missing or bad value: {e}", "pages": []}
