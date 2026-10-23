from __future__ import annotations
import re

ALL = "ALL"
PCC = "PCC"
CONCRETE, STEEL = "CONCRETE", "STEEL"
MEMBER_KINDS = ("COLUMN", "BEAM", "LINTEL", "FOOTING", "SLAB", "CHAJJA", "BALCONY_SLAB", "STAIR", "RCC_WALL", "TANK", "PARAPET")

_WORDS = (
  (re.compile(r"\bcolumns?\b"), ("COLUMN",)),
  (re.compile(r"\bbeams?\b|\bgirders?\b|\bplinth\b|\btie\s*bands?\b|\bgrade\s*beams?\b"), ("BEAM",)),
  (re.compile(r"\blintels?\b"), ("LINTEL",)),
  (re.compile(r"\bslabs?\b|\broof\b"), ("SLAB", "CHAJJA", "BALCONY_SLAB")),
  (re.compile(r"\bchajjas?\b|\bchhajjas?\b|\bsunshades?\b"), ("CHAJJA",)),
  (re.compile(r"\bbalcon(?:y|ies)\b"), ("BALCONY_SLAB",)),
  (re.compile(r"\bfootings?\b|\bfoundations?\b|\braft\b|\bpile\s*caps?\b"), ("FOOTING",)),
  (re.compile(r"\bstair(?:s|case|cases)?\b"), ("STAIR",)),
  (re.compile(r"\btanks?\b|\bohwt\b|\bugwt\b|\bseptic\b|\breservoirs?\b"), ("TANK",)),
  (re.compile(r"\bwalls?\b"), ("RCC_WALL",)),
  (re.compile(r"\bparapets?\b|\bcoping\b"), ("PARAPET",)),
)
_RING_WORDS = re.compile(r"\b(?:stirrups?|ties|links?|hoops?)\b")
_MAIN_WORDS = re.compile(r"\bmain\s+(?:bars?|steel|reinforcement)\b|\blongitudinal\b")
_CLAUSES = re.compile(r"\s*(?:,|;|&|\+|/|\band\b)\s*")
_PCC = re.compile(r"\bp\s*c\s*c\b|\bplain\b|\bblinding\b|\blean\b")
_GENERAL = re.compile(r"\ball\b|\bevery\b|\bwhole\b|\bstructural\b|\br\s*c\s*c\b|\breinforced\b|\bgeneral\b|\bwork\b|\bmembers?\b|\bconcrete\b")

def members_of(scope: str | None) -> tuple:
  text = re.sub(r"[^a-z0-9 ]+", " ", str(scope or "").lower())
  text = re.sub(r"\s+", " ", text).strip()
  
  if not text:
    return (ALL,), "GENERAL"
  named: list = []
  for pat, kinds in _WORDS:
    if pat.search(text):
      named.extend(k for k in kinds if k not in named)
  if named:
    return tuple(named), "NAMED"
  if _PCC.search(text) and not re.search(r"\br\s*c\s*c\b|\breinforced\b", text):
    return (PCC,), "PCC"
  if _GENERAL.search(text):
    return (ALL,), "GENERAL"
  return (), "NONE"

def steel_clauses(scope: str | None) -> dict:
  text = str(scope or "").lower()
  out: dict = {"ALL": [], "MAIN": [], "RING": []}
  if not (_RING_WORDS.search(text) or _MAIN_WORDS.search(text)):
    out["ALL"].append(text)
    return out

  for clause in _CLAUSES.split(text):
    clause = clause.strip()
    if not clause:
      continue
    if _RING_WORDS.search(clause):
      out["RING"].append(re.sub(r"\s+", " ", _RING_WORDS.sub(" ", clause)).strip())
    elif _MAIN_WORDS.search(clause):
      out["MAIN"].append(re.sub(r"\s+", " ", _MAIN_WORDS.sub(" ", clause)).strip())
    else:
      out["ALL"].append(clause)
  return out

def _expanded(items: list):
  for it in items:
    if it.get("kind") != "STEEL_GRADE":
      yield it
      continue
  
    parts = steel_clauses(it.get("scope"))
    if not parts["RING"] and not parts["MAIN"]:
      yield it
      continue
  
    if parts["ALL"]:
      yield {**it, "part": "ALL", "clause": ", ".join(parts["ALL"])}
    for part in ("MAIN", "RING"):
      for clause in parts[part]:
        yield {**it, "part": part, "clause": clause}

def steel_label(grade) -> str:
  return f"G-{int(grade)}"

def concrete_label(klass: str | None, mix: str | None) -> str | None:
  mix = (mix or "").strip()
  if not mix:
    return None
  return f"Reinforced concrete, Class {klass} {mix}" if klass else f"Reinforced concrete, {mix}"

def rules_from_items(items: list) -> dict:
  out: dict = {"concrete": [], "steel": []}
  seen: dict = {}
  
  for it in _expanded(items or []):
    kind = it.get("kind")
    if kind == "CONCRETE_CLASS" and it.get("mix"):
      value, label, bucket = str(it["mix"]).replace(" ", ""), concrete_label(it.get("concrete_class"), it.get("mix")), "concrete"
      extra = {"class": it.get("concrete_class"), "mix": value}
    elif kind == "STEEL_GRADE" and it.get("grade") is not None:
      value, label, bucket = steel_label(it["grade"]), steel_label(it["grade"]), "steel"
      extra = {"grade": int(it["grade"])}
    else:
      continue
    members, how = members_of(it.get("clause") if it.get("clause") is not None else it.get("scope"))
    key = (bucket, value, it.get("part"), tuple(members), it.get("scope") or "")
    row = seen.get(key)
    
    if row is None:
      row = seen[key] = {"value": value, "label": label, **extra, "scope": it.get("scope") or "", "members": list(members), "how": how, "text": it.get("text"),
        "pages": [], "count": 0, **({"part": it["part"]} if it.get("part") else {})}
      out[bucket].append(row)
    row["count"] += int(it.get("count", 1))
    
    for p in it.get("pages") or []:
      if p not in row["pages"]:
        row["pages"].append(p)
  for bucket in out:
    for row in out[bucket]:
      row["pages"] = sorted(row["pages"])
    out[bucket].sort(key=lambda r: (r["value"], r["scope"], r.get("part") or ""))
  return out

PARTS_OF = {"RING": (("RING",), ("ALL", "MAIN")), "MAIN": (("MAIN",), ("ALL",)), None: (("ALL", "MAIN"),)}

def resolve(rules: list, category: str | None, part: str | None = None) -> dict:
  if not category:
    return {"rule": None, "clash": []}
  last = {"rule": None, "clash": []}
  for kinds in PARTS_OF.get(part, PARTS_OF[None]):
    last = _resolve_in([r for r in rules or [] if (r.get("part") or "ALL") in kinds], category)
    if last["rule"] is not None or last["clash"]:
      return last
  return last

def _resolve_in(rules: list, category: str) -> dict:
  for tier in ("NAMED", "GENERAL"):
    hit = [r for r in rules or [] if r.get("how") == tier and (category in (r.get("members") or ()) or (tier == "GENERAL" and ALL in (r.get("members") or ())))]
    if not hit:
      continue
  
    values = sorted({r["value"] for r in hit})
    if len(values) == 1:
      return {"rule": sorted(hit, key=lambda r: (-int(r.get("count", 1)), r.get("scope") or ""))[0], "clash": []}
    return {"rule": None, "clash": values}
  return {"rule": None, "clash": []}

def category_of_candidate(category: str | None, facts: dict | None) -> str | None:
  facts = facts or {}
  if category in ("COLUMN", "BEAM", "LINTEL", "FOOTING", "SLAB", "STAIR"):
    return category
  if category == "SITE":
    return "TANK" if str(facts.get("site_kind") or "") in ("OHWT", "UGWT", "SEPTIC") else None
  if category == "WALL":
     return "RCC_WALL" if facts.get("construction") == "RCC" else None
  return None

def steel_grade_of(ctx, category: str | None, part: str | None = None) -> dict:
  rules = (((getattr(ctx, "drawing_params", None) or {}).get("grades") or {}).get("steel")) or []
  got = resolve(rules, category, part)
  rule = got["rule"]
  return {"label": rule["label"] if rule else None, "clash": got["clash"], "scope": rule["scope"] if rule else None, "pages": list(rule["pages"]) if rule else [],
    "part": (rule.get("part") or "ALL") if rule else None}
