from __future__ import annotations

import re

ARCH_PLAN, FURNITURE_PLAN, STRUCT_PLAN, DETAIL, SECTION, ELEVATION, MEP_PLAN, NOTES, SCHEDULE, COVER = (
  "ARCH_PLAN", "FURNITURE_PLAN", "STRUCT_PLAN", "DETAIL", "SECTION", "ELEVATION", "MEP_PLAN", "NOTES", "SCHEDULE", "COVER")
ROLES = (ARCH_PLAN, FURNITURE_PLAN, STRUCT_PLAN, DETAIL, SECTION, ELEVATION, MEP_PLAN, NOTES, SCHEDULE, COVER)
PLAN_ROLES = (ARCH_PLAN, FURNITURE_PLAN, STRUCT_PLAN, MEP_PLAN)
WEIGHTS = {"TITLE_BLOCK": 0.35, "DRAWING_LIST": 0.30, "VIEW_TITLES": 0.20, "CONTENT": 0.15, "VIEW_COUNT": 0.30}
DETAIL_TITLE = re.compile(r"\bSEC(?:TION)?\.?\s*\w+\s*[-\u2013]\s*\w+|\bFOUNDATION\s+PLAN\s+\w+|\bTYP\.|\bDETAILS?\b", re.I)   
MIN_DETAIL_VIEWS = 3            
DETAIL_SHARE = 0.8              
MAX_ROOM_SIZES = 3             
PASS = 0.6                      
STRONG = 0.7                   
IMAGE_PAGE_COVER = 0.5          
IMAGE_PAGE_MAX_WORDS = 120
VIEW_MAJORITY = 0.5             
SHEET_TYPE_ROLE = {"SECTION": SECTION, "ELEVATION": ELEVATION, "DETAIL": DETAIL, "SCHEDULE": SCHEDULE, "LEGEND": NOTES, "SPEC": NOTES}

READ_AS_OF = {COVER: "SKIP", NOTES: "SKIP", ELEVATION: "SKIP", DETAIL: "DETAILS_ONLY", SECTION: "DETAILS_ONLY", SCHEDULE: "DETAILS_ONLY"}

def _signal(name: str, role: str | None, certainty: float, why: str, **extra) -> dict | None:
  if role is None or certainty <= 0.0:
    return None
  return {"signal": name, "role": role, "certainty": round(float(certainty), 2), "why": why, **extra}

def _plan_role(sheet_type: str | None, discipline: str | None, plan_kind: str | None, services: tuple) -> str | None:
  if sheet_type == "PLAN":
    if discipline in services:
      return MEP_PLAN
    if discipline == "STRUCTURAL" or plan_kind in ("FRAMING", "FOUNDATION"):
      return STRUCT_PLAN
    return FURNITURE_PLAN if plan_kind == "FURNITURE" else ARCH_PLAN
  return SHEET_TYPE_ROLE.get(sheet_type or "")

def title_block_signal(identity: dict | None, read_view=None, services: tuple = ("ELECTRICAL", "PLUMBING", "FIRE", "HVAC", "GAS")) -> dict | None:
  i = identity or {}
  sheet_type, certainty = i.get("sheet_type"), 0.9 if i.get("basis") == "TITLE_BLOCK" else 0.75 if i.get("basis") == "TITLE" else 0.6
  if i.get("title") and read_view is not None:
    own = read_view(i["title"]).get("sheet_type")
    
    if own:
      sheet_type = own
    elif sheet_type:
      certainty = min(certainty, 0.6)
  role = _plan_role(sheet_type, i.get("discipline"), i.get("plan_kind"), services)
  if role is None:
    return None
  return _signal("TITLE_BLOCK", role, certainty, f"the sheet says {sheet_type}" + (f": {i['title']}" if i.get("title") else ""))

def view_titles_signal(views: list | None, read_view, services: tuple = ("ELECTRICAL", "PLUMBING", "FIRE", "HVAC", "GAS")) -> dict | None:
  kinds: dict = {}
  total = 0
  for v in views or []:
    r = read_view(v.get("caption"))
    role = _plan_role(r.get("sheet_type"), r.get("discipline"), None, services)
    total += 1
    if role is not None:
      kinds[role] = kinds.get(role, 0) + 1
  if not total or not kinds:
    return None
  role, n = max(kinds.items(), key=lambda kv: kv[1])
  share = n / total
  if share <= VIEW_MAJORITY:
    return None
  return _signal("VIEW_TITLES", role, min(0.9, 0.5 + 0.4 * share), f"{n} of {total} view titles say {role.lower().replace('_', ' ')}")

def drawing_list_signal(is_list: bool) -> dict | None:
  return _signal("DRAWING_LIST", NOTES, 0.95, "the page is the list of drawings") if is_list else None

def content_signal(pdf_type: str | None, image_cover: float, words: int, drawn: int) -> dict | None:
  if pdf_type == "IMAGE_PAGE" and float(image_cover or 0.0) >= IMAGE_PAGE_COVER and int(words or 0) <= IMAGE_PAGE_MAX_WORDS:
    return _signal("CONTENT", COVER, 0.85, f"{round(float(image_cover) * 100)}% of the page is one picture and it has {int(words)} words")
  return None

def detail_sheet_signal(views: list | None, room_sizes: int) -> dict | None:
  titled = [v for v in views or [] if DETAIL_TITLE.search(str(v.get("caption") or ""))]
  if len(titled) < MIN_DETAIL_VIEWS or len(titled) < DETAIL_SHARE * len(views or []) or int(room_sizes or 0) > MAX_ROOM_SIZES:
    return None
  return _signal("VIEW_COUNT", DETAIL, 0.9, f"{len(titled)} of its {len(views or [])} views are titled as details and it prints {int(room_sizes or 0)} room sizes")

def decide(signals: list) -> dict:
  spoke = [s for s in signals if s]
  weight = sum(WEIGHTS[s["signal"]] for s in spoke)
  
  votes: dict = {}
  for s in spoke:
    votes[s["role"]] = votes.get(s["role"], 0.0) + WEIGHTS[s["signal"]] * s["certainty"]
  shares = {r: round(v / weight, 3) for r, v in sorted(votes.items(), key=lambda kv: -kv[1])} if weight else {}
  strong = sorted({s["role"] for s in spoke if s["certainty"] >= STRONG})
  top = next(iter(shares), None)
  clash = len(strong) > 1
  
  held = not spoke or shares.get(top, 0.0) < PASS or clash
  why = "no signal had an opinion" if not spoke else ("two strong signals disagree: " + ", ".join(strong)) if clash else (f"no role reaches {PASS:g}") if held else None
  role = None if held else top
  return {"role": role, "votes": shares, "held": held, "why": why, "read_as": READ_AS_OF.get(role) if role else None, "signals": spoke}

def apply(identity: dict, signals: list) -> dict:
  vote = decide(signals)
  identity["role_vote"] = vote
  return vote
