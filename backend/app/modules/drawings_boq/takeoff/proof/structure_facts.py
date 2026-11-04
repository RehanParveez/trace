from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.proof import closure_checks as CC
from app.modules.drawings_boq.takeoff.proof import known_facts as KF

SIZE_TOL_MM = 13.0

def _mark(text) -> str:
  return re.sub(r"[\s\-_]", "", str(text or "")).upper()

def _result(text: str, status: str, expected, found, message: str, pages: list) -> dict:
  return {"text": text, "status": status, "expected": expected, "found": found, "message": message, "pages": sorted(set(p for p in pages if p))}

def _inches(text) -> float:
  t = str(text).replace("½", ".5").replace("¼", ".25").replace("¾", ".75")
  return float(re.sub(r"[^0-9.]", "", t))

def _size_in(text) -> tuple:
  parts = [p for p in re.split(r"x", str(text).lower().replace("×", "x")) if p.strip()]
  if len(parts) != 2:
    raise ValueError("size must be width x depth, for example 12\"x21\"")
  return _inches(parts[0]), _inches(parts[1])

def _same(a: tuple, b: tuple) -> bool:
  return all(abs(x - y) * 25.4 <= SIZE_TOL_MM for x, y in zip(a, b))

def _tables(read: list, name: str) -> list:
  return [(sh["page_no"], ((sh.get("meta") or {}).get("structure_tables") or {}).get(name)) for sh in read if ((sh.get("meta") or {}).get("structure_tables") or {}).get(name)]

def _rows(text: str, rows: list, pages: list) -> dict:
  if not rows or all(r[2] is None for r in rows):
    return _result(text, KF.MISSING, [r[1] for r in rows], None, "Nothing of this was read from the sheets.", pages)
  bad = [r for r in rows if not r[3]]
  shown = {r[0]: r[2] for r in rows}
  if not bad:
    return _result(text, KF.PASS, {r[0]: r[1] for r in rows}, shown, f"{len(rows)} value(s) read: as printed.", pages)
  return _result(text, KF.FAIL, {r[0]: r[1] for r in rows}, shown, "; ".join(f"{r[0]}: {r[2] if r[2] is not None else 'not read'} read, {r[1]} stated" for r in bad) + ".", pages)

def column_schedule(read: list, f: dict) -> dict:
  mark, floor = _mark(f["mark"]), str(f["floor"]).upper()
  text = f"column schedule {f['mark']} on the {floor.lower()} floor"
  
  for page, sched in _tables(read, "column_schedule"):
    for rec in sched["cells"]:
      if rec.get("state") == "READ" and _mark(rec["mark"]) == mark and rec["floor"] == floor:
        rows = []
        if f.get("size") is not None:
          got = (rec.get("size") or {}).get("size_in")
          rows.append(("size_in", list(_size_in(f["size"])), list(got) if got else None, bool(got) and _same(_size_in(f["size"]), tuple(got))))
        if f.get("bars") is not None:
          m = re.match(r"^(\d+)-?#(\d+)$", str(f["bars"]).replace(" ", ""))
          if not m:
            raise ValueError("bars must be like 10-#4")
          want = [int(m.group(1)), int(m.group(2))]
          rows.append(("bars", want, list(rec["steel"]) if rec.get("steel") else None, bool(rec.get("steel")) and list(rec["steel"]) == want))
        for key, name in (("stirrup_mid_in", "mid"), ("stirrup_joint_in", "joint")):
          if f.get(key) is not None:
            got = (rec.get(name) or {}).get("mid" if name == "mid" else "end")
            rows.append((key, float(f[key]), got, got is not None and abs(float(got) - float(f[key])) < 0.01))
        out = _rows(text, rows, [page])
        if f.get("conflict") and out["status"] == KF.PASS:
          seen = [c["kind"] for c in (rec.get("sketch") or {}).get("conflicts") or []]
          if f["conflict"] not in seen:
            return _result(text, KF.FAIL, f["conflict"], seen, f"The drawing's own conflict {f['conflict']} was not raised.", [page])
        return out
    
  return _result(text, KF.MISSING, f"{f['mark']} {floor}", None, f"No cell for {f['mark']} on the {floor.lower()} floor was read.", [])

def beam_section(read: list, f: dict) -> dict:
  mark = _mark(f["mark"])
  text = f"beam section {f['mark']}"
  for page, secs in _tables(read, "beam_sections"):
    for rec in secs["sections"]:
      if _mark(rec["mark"]) == mark:
        rows = []
        if f.get("size") is not None:
          rows.append(("size_in", list(_size_in(f["size"])), [rec["width_in"], rec["depth_in"]], _same(_size_in(f["size"]), (rec["width_in"], rec["depth_in"]))))
        for key in ("top", "bottom"):
          if f.get(key) is not None:
            got = rec.get(f"{key}_bars") or []
            rows.append((key, list(f[key]), got, [re.sub(r"\s+", "", x) for x in got] == [re.sub(r"\s+", "", str(x)) for x in f[key]]))
        if f.get("stirrup") is not None:
          rows.append(("stirrup", f["stirrup"], rec.get("stirrup"), re.sub(r"[\s\"']", "", str(rec.get("stirrup"))) == re.sub(r"[\s\"']", "", str(f["stirrup"]))))
        return _rows(text, rows, [page])
    
  return _result(text, KF.MISSING, f["mark"], None, f"No section for {f['mark']} was read.", [])

def footing_section(read: list, f: dict) -> dict:
  if f.get("joined"):
    mark = _mark(f["mark"])
    text = f"footing {f['mark']} joined to its section"
    seen = [(sh["page_no"], (c.facts or {}).get("footing_section_join")) for sh in read for c in sh["candidates"] if c.category == "FOOTING" and _mark(c.tag) == mark and (c.facts or {}).get("footing_section_join")]
    
    if not seen:
      return _result(text, KF.MISSING, "a section", None, f"No footing marked {f['mark']} was read.", [])
    if any(j["status"] == "JOINED" for _p, j in seen):
      return _result(text, KF.PASS, "a section", [j["to"]["key"] for _p, j in seen if j["to"]], f"{f['mark']} is joined to its section.", [p for p, _j in seen])
    return _result(text, KF.MISSING, "a section", None, f"{f['mark']} has no section joined: {seen[0][1].get('reason')}.", [p for p, _j in seen])
  if f.get("wall_in") is not None:
    return CC.wall_footing(read, f)
  return CC.column_footing(read, f)

def rebar_rules(read: list, f: dict) -> dict:
  key = str(f["key"]).upper()
  text = f"rebar rule {key}"
  for sh in read:
    for rec in (((sh.get("meta") or {}).get("rebar_rules") or {}).get("facts")) or []:
      if rec["key"].upper() == key:
        want = f["value"]
        ok = (abs(float(rec["value"]) - float(want)) < 1e-6) if isinstance(rec["value"], (int, float)) and isinstance(want, (int, float)) else str(rec["value"]).lower() == str(want).lower()
        return _rows(text, [("value", want, rec["value"], ok)], [sh["page_no"]])
  return _result(text, KF.MISSING, f.get("value"), None, f"The rule {key} was not read.", [])

def tank_detail(read: list, f: dict) -> dict:
  view = str(f["view"]).upper()
  text = f"tank detail {view}"
  for sh in read:
    for d in (sh.get("meta") or {}).get("tank_details") or []:
      if str(d.get("view") or "").upper() == view:
        rows = []
        for key in ("depth_in", "plan_in"):
          if f.get(key) is not None:
            got = d.get(key)
            rows.append((key, f[key], got, got is not None and (got == f[key] if not isinstance(got, (int, float)) else abs(float(got) - float(f[key])) <= 0.5)))
        return _rows(text, rows or [("read", True, True, True)], [sh["page_no"]])
    
  return _result(text, KF.MISSING, view, None, f"No tank drawing of the view {view} was read.", [])

CHECKS = {"COLUMN_SCHEDULE": column_schedule, "BEAM_SECTION": beam_section, "FOOTING_SECTION": footing_section, "REBAR_RULES": rebar_rules, "TANK_DETAIL": tank_detail}
