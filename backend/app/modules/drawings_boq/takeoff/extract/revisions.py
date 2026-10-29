from __future__ import annotations
import hashlib
import re
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.drawings_boq.takeoff.extract import sheet_identity as SID

BY = FS.OPTION_BY

SHEET_NO_RX = re.compile(r"^[A-Z]{1,4}-?\d{1,3}[A-Z]?$")

TOLERANCE = {"OPTION": "the same discipline, kind of plan and caption, and two or more different option labels",
  "REVISION": "the same discipline, kind of plan, floor and sheet number (as AA-01), with a different latest revision stamp (number or date); a sheet with no stamp is the earliest",
  "UNMARKED": "not decided here: two sheets of one floor with no option, stamp or sheet number that differ in rooms or marks stay with the floor and layout choices (a door moved is below what can be told from drafting)"}

def _rank(stamps: list) -> tuple:
  best = ((-1, ""), None)
  for s in stamps or []:
    n = int(s["rev"]) if str(s["rev"]).isdigit() else ord(str(s["rev"])[0]) - 64
    best = max(best, ((n, s.get("date") or ""), s))
  return best[0]

def _rank_text(rank: tuple) -> str:
  return "no revision mark" if rank[0] < 0 else f"revision {rank[0]}" + (f", {rank[1]}" if rank[1] else "")

def _caption(s: dict) -> str:
  t = (s.get("identity") or {}).get("title") or (s.get("title") or {}).get("title") or ""
  return re.sub(r"[^A-Z0-9]+", " ", str(t).upper()).strip()

def _eligible(s: dict) -> bool:
  i = s.get("identity") or {}
  return bool(i) and SID.read_as(i) == "PLAN_ITEMS" and ((s.get("stats") or {}).get("sheet_role") or {}).get("advice") != "SKIP"

def _sample(rows: list) -> dict | None:
  pick = [c for c in rows if getattr(c, "id", None) is not None]
  if not pick:
    return None
  c = max(pick, key=lambda c: (c.category in ("FOOTING", "COLUMN", "BEAM", "WALL"), len(str(c.geometry or ""))))
  return {"id": str(c.id), "label": c.label, "geometry": c.geometry}

def _sheet(s: dict) -> dict:
  i = s.get("identity") or {}
  rows = list(s.get("candidates") or [])
  state = lambda c: getattr(c, "decision", "NEW")
  aside = lambda c: ((c.facts or {}).get(FS.SET_ASIDE) or {}).get("by") == BY
  live = [c for c in rows if state(c) != "REJECTED" and not aside(c)]
  return {"sheet_id": s["sheet_id"], "page_no": s["page_no"], "drawing_id": s.get("drawing_id"), "sheet_no": i.get("sheet_no"), "option": i.get("option"), "stamps": i.get("stamps") or [],
    "items": len(rows), "open": sum(1 for c in live if state(c) != "ACCEPTED"), "accepted": sum(1 for c in live if state(c) == "ACCEPTED"), "rejected": sum(1 for c in rows if state(c) == "REJECTED"),
    "set_aside": bool(rows) and not live and any(aside(c) for c in rows), "sample": _sample(live or rows)}

def _id(*parts) -> str:
  return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:12]

def _group(kind: str, key: tuple, values: list, caption: str, floor: str | None, sheet_no: str | None) -> dict:
  options = []
  for value, label, text, sheets in values:
    live = sum(s["open"] + s["accepted"] for s in sheets)
    options.append({"value": value, "label": label, "text": text, "pages": sorted(s["page_no"] for s in sheets), "sheet_ids": [s["sheet_id"] for s in sheets], "items": sum(s["items"] for s in sheets),
      "open": sum(s["open"] for s in sheets), "accepted": sum(s["accepted"] for s in sheets), "set_aside": all(s["set_aside"] for s in sheets), "live": live, "sample": next((s["sample"] for s in sheets if s["sample"]), None)})
  live = [o for o in options if o["live"] > 0]
  state = "OPEN" if len(live) > 1 else "CHOSEN" if len(live) == 1 else "NONE"
  default = None
  
  if kind == "REVISION":
    default = options[-1]["value"]
  question = (f"Which option was built for the {caption.lower()}? The set prints {len(options)}: " + ", ".join(o["label"] for o in options) + "." if kind == "OPTION"
    else f"Sheet {sheet_no} is printed with {len(options)} revisions. Which one is current? The later one is the default.")
  return {"id": _id(kind, *key, *[o["value"] for o in options]), "kind": kind, "caption": caption, "floor": floor, "sheet_no": sheet_no, "question": question, "state": state, "default": default,
    "chosen": live[0]["value"] if state == "CHOSEN" else None, "options": options, "choosable": True}

def build(sheets: list) -> dict:
  cards = [(s, _sheet(s)) for s in sheets if _eligible(s)]
  groups: list = []
  in_option: set = set()

  by_key: dict = {}
  for s, c in cards:
    if c["option"]:
      i = s["identity"]
      by_key.setdefault((str(c["drawing_id"]), i.get("discipline"), i.get("plan_kind"), _caption(s)), []).append((s, c))
  for key, members in sorted(by_key.items(), key=lambda kv: min(c["page_no"] for _s, c in kv[1])):
    labels = sorted({c["option"]["label"] for _s, c in members})
    if len(labels) < 2:
      continue
    values = [(lab, lab.title(), next(c["option"]["text"] for _s, c in members if c["option"]["label"] == lab), [c for _s, c in members if c["option"]["label"] == lab]) for lab in labels]
    groups.append(_group("OPTION", key, values, key[3].title() if key[3] else "plan", None, None))
    in_option.update(c["sheet_id"] for _s, c in members)
    
  rev: dict = {}
  for s, c in cards:
    i = s["identity"]
    no = re.sub(r"\s+", "-", str(c["sheet_no"] or "").strip().upper())
    if c["sheet_id"] in in_option or not SHEET_NO_RX.match(no):
      continue
    rev.setdefault((i.get("discipline"), i.get("plan_kind"), i.get("floor"), no), []).append((s, c))
  for key, members in sorted(rev.items(), key=lambda kv: min(c["page_no"] for _s, c in kv[1])):
    ranks = sorted({_rank(c["stamps"]) for _s, c in members})
    if len(ranks) < 2 or ranks[-1][0] < 0:
      continue
    values = [(_rank_text(r), _rank_text(r).capitalize(), _rank_text(r), [c for _s, c in members if _rank(c["stamps"]) == r]) for r in ranks]
    groups.append(_group("REVISION", key, values, _caption(members[0][0]).title(), key[2], key[3]))

  return {"groups": groups, "to_decide": sum(1 for g in groups if g["state"] == "OPEN"), "tolerance": TOLERANCE}

def plan_choice(group: dict, value: str, sheets_by_id: dict) -> dict:
  keep = next((o for o in group["options"] if o["value"] == value), None)
  if keep is None:
    return {"keep": None, "set_aside": [], "blocked": "OPTION_NOT_OFFERED"}
  others = [o for o in group["options"] if o["value"] != value]
  held = [o for o in others if o["accepted"] > 0]
  if held:
    return {"keep": keep, "set_aside": [], "blocked": "OPTION_OTHER_ACCEPTED", "pages": [p for o in held for p in o["pages"]]}
  return {"keep": keep, "set_aside": others, "blocked": None}

def sheet_mark(rows: list) -> dict | None:
  if not rows:
    return None
  marks = [((c.facts or {}).get(FS.SET_ASIDE) or {}) for c in rows]
  if all(getattr(c, "decision", "NEW") == "REJECTED" and m.get("by") == BY for c, m in zip(rows, marks)):
    return dict(marks[0])
  return None

def apply_defaults(sheets: list) -> dict:
  used: dict = {}
  for g in build(sheets)["groups"]:
    if g["kind"] != "REVISION" or g["state"] != "OPEN" or g["default"] is None:
      continue
  
    keep = next(o for o in g["options"] if o["value"] == g["default"])
    drop = {sid for o in g["options"] if o["value"] != g["default"] for sid in o["sheet_ids"]}
    for s in sheets:
      if s["sheet_id"] in drop:
        for c in s.get("candidates") or []:
          c.facts = {**(c.facts or {}), FS.SET_ASIDE: {"by": BY, "page_no": keep["pages"][0]}}
    used[g["id"]] = keep["pages"][0]
  return used
