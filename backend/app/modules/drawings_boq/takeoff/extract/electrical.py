from __future__ import annotations
import re
import collections
import hashlib
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import electrical_symbols as ES

LIGHT, FAN, SOCKET, SWITCH, LOWV, BOARD, OTHER = "ELEC_LIGHT", "ELEC_FAN", "ELEC_SOCKET", "ELEC_SWITCH", "ELEC_LOWV", "ELEC_BOARD", "ELEC_OTHER"
ITEMS = (LIGHT, FAN, SOCKET, SWITCH, LOWV, BOARD, OTHER)
WORK_ITEM = {LIGHT: "ELE-LIGHT", FAN: "ELE-FAN", SOCKET: "ELE-SOCKET", SWITCH: "ELE-SWITCH", LOWV: "ELE-LOWV", BOARD: "ELE-BOARD", OTHER: "ELE-OTHER"}
TAG = {LIGHT: "ELEC-LIGHT", FAN: "ELEC-FAN", SOCKET: "ELEC-SOCKET", SWITCH: "ELEC-SWITCH", LOWV: "ELEC-LOWV", BOARD: "ELEC-BOARD", OTHER: "ELEC-OTHER"}
GROUP_TEXT = {LIGHT: "Lights", FAN: "Fans", SOCKET: "Sockets and plugs", SWITCH: "Switches", LOWV: "Telephone, TV, data, alarm and bell points", BOARD: "Boards, earthing and supply",
  OTHER: "Other electrical points"}

GROUP_RULES = (
  (FAN, re.compile(r"\bFAN\b", re.I)),
  (SOCKET, re.compile(r"\b(?:PLUG|SOCKET|RECEPTACLE)\b", re.I)),
  (LOWV, re.compile(r"\b(?:BELL|BUZZER|SMOKE|DETECTOR|SPEAKER|CCTV|CAMERA|TELEPHONE|TEL|TV|CABLE|COMPUTER|NETWORKING|INTERCOM|DATA)\b", re.I)),
  (SWITCH, re.compile(r"\bSWITCH(?:ES)?\b", re.I)),
  (BOARD, re.compile(r"\b(?:BOARD|DB|UPS|GENERATOR|EARTH|MCB|METER)\b", re.I)),
  (LIGHT, re.compile(r"\b(?:LIGHT|LAMP|TUBE|FIXTURE|LUMINAIRE|BULB)S?\b", re.I)),
)
LEGEND_WORDS = re.compile(r"\b(?:LEGEND|SYMBOLS?)\b", re.I)
ELECTRIC_WORD = re.compile(r"ELECTRIC", re.I)
PLAN_WORD = re.compile(r"\bPLAN\b", re.I)
CONFIDENCE_PICTURE, CONFIDENCE_TEXT = 0.6, 0.7

def group_of(name: str) -> str:
  for group, rule in GROUP_RULES:
    if rule.search(name or ""):
      return group
  return OTHER

def _upper(words: list) -> str:
  return " ".join((w.text or "") for w in words)

def is_legend_sheet(words: list) -> bool:
  text = _upper(words)
  return bool(ELECTRIC_WORD.search(text) and LEGEND_WORDS.search(text))

def is_plan_sheet(words: list) -> bool:
  text = _upper(words)
  return bool(ELECTRIC_WORD.search(text) and PLAN_WORD.search(text))

def pack_legend(legend: list) -> list:
  return [{"name": s.name, "description": s.description, "token": s.token, "mounting_height_mm": s.mounting_height_mm,
    "objects": [[o.kind, o.n, o.box[0], o.box[1], o.box[2], o.box[3]] for o in s.objects]} for s in legend]

def unpack_legend(rows: list) -> list:
  out = []
  for ti, r in enumerate(rows or []):
    objs = [ES.Obj(i, int(o[0]), int(o[1]), (float(o[2]), float(o[3]), float(o[4]), float(o[5]))) for i, o in enumerate(r.get("objects") or [])]
    out.append(ES.LegendSymbol(description=r.get("description") or "", name=r.get("name") or "", table=0, row=ti, objects=objs,
      mounting_height_mm=r.get("mounting_height_mm"), token=r.get("token") or ""))
  return out

def read_legend_rows(page, words: list) -> list:
  if not is_legend_sheet(words):
    return []
  return pack_legend(ES.read_legend(page))

def gather_legend(sheets: list) -> dict:
  rows, pages, seen = [], [], set()
  for sh in sorted(sheets, key=lambda s: s["page_no"]):
    if not sh.get("legend"):
      continue
    pages.append(sh["page_no"])
    for r in sh["legend"]:
      key = (r.get("name"), r.get("token"), len(r.get("objects") or []))
      if key not in seen:
        seen.add(key)
        rows.append(r)
  return {"pages": pages, "rows": rows}

def count_page(doc, page_no: int, rows: list) -> dict:
  page = doc[page_no - 1]
  legend = unpack_legend(rows)
  objs, stats = ES.load_objects(page)
  rep = ES.count_symbols(objs, legend, ES.read_tokens(page))
  rot, ox, oy, wu, hu = ES._geometry(page)
  points: dict = collections.defaultdict(list)
  for h in rep.hits:
    l, b, _, _ = ES._to_page_rect(rot, ox, oy, wu, hu, (h.centre[0], h.centre[1], h.centre[0], h.centre[1]))
    points[h.name].append([round(l, 2), round(b, 2)])

  by = {s.name: s for s in legend}
  return {"counts": {k: int(v) for k, v in rep.counts.items()}, "points": dict(points), "aside": dict(collections.Counter(h.name for h in rep.set_aside)),
    "not_countable": list(rep.not_countable), "by_text": sorted({s.name for s in legend if s.by_text}),
    "description": {k: s.description for k, s in by.items()}, "height_mm": {k: s.mounting_height_mm for k, s in by.items() if s.mounting_height_mm},
    "objects": stats.get("objects"), "legend_symbols": len(legend)}

def count_page_bytes(contents: bytes, page_no: int, rows: list) -> dict:
  from app.modules.drawings_boq.takeoff.prep.extract import open_document
  doc = open_document(contents)
  try:
    return count_page(doc, page_no, rows)
  finally:
    try:
      doc.close()
    except Exception:
      pass

def _ft_in(mm: float) -> str:
  inches = round(float(mm) / 25.4)
  return f"{inches // 12}'-{inches % 12}\""

def _key_of(parts: tuple) -> str:
  return hashlib.sha1("|".join(str(p) for p in ("ELE", *parts)).encode()).hexdigest()[:24]

def candidates(read: dict | None, ctx: dict, cls, finish) -> list:
  if not read or read.get("failed"):
    return []
  out: list = []
  for name, n in sorted(read.get("counts", {}).items(), key=lambda kv: kv[0]):
    pts = read.get("points", {}).get(name) or []
    if n <= 0 or len(pts) != n:
      continue

    group = group_of(name)
    by_text = name in (read.get("by_text") or [])
    aside = int((read.get("aside") or {}).get(name, 0))
    height = (read.get("height_mm") or {}).get(name)
    notes = [C.note("ELECTRICAL_COUNT_ONLY")]

    if not by_text:
      notes.append(C.note("ELECTRICAL_PICTURE_MATCH"))
    if aside:
      notes.append(C.note("ELECTRICAL_OTHER_SIZE_SET_ASIDE", count=aside))
    facts = {"electrical": name, "electrical_group": group, "symbol_text": (read.get("description") or {}).get(name), "counted_by": "TEXT" if by_text else "PICTURE",
      "mounting_height_mm": height, "set_aside_other_size": aside, "foundation_item": group, "derived_from": "LEGEND"}
    label = f"{GROUP_TEXT[group]} · {name} · {n} no{'s' if n != 1 else ''}" + (f" · {_ft_in(height)} above floor" if height else "")
    cand = cls(key=_key_of((name, round(pts[0][0], 1), round(pts[0][1], 1))), category="WALL", kind="COUNT", quantity_mode="DIRECT", label=label, tag=TAG[group],
      geometry={"points": pts}, params={"dims_basis": "SPECIFIED"}, missing=[], work_item=WORK_ITEM[group], status="VALID", confidence=0.0, facts=facts, notes=notes,
      source="TAG_SCAN", count=n)
    out.append(finish(cand, ctx, CONFIDENCE_TEXT if by_text else CONFIDENCE_PICTURE))
  return out

def sheet_notes(read: dict | None) -> list:
  if not read or read.get("failed"):
    return [C.note("ELECTRICAL_READ_FAILED")] if read else []
  names = sorted(set(read.get("not_countable") or []))
  return [C.note("ELECTRICAL_SYMBOLS_NOT_READ", count=len(names), symbols=names)] if names else []
