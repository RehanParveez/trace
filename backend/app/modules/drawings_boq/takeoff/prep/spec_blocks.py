from __future__ import annotations
import re
import math

HEADING = re.compile(r"^(?P<name>(?:GROUND|FIRST|SECOND|THIRD|FOURTH|FIFTH|TOP|UPPER|LOWER|MEZZANINE)\s+FLOORS?|BASEMENT|TERRACE|PORCH\s+ROOF|MUMTY(?:\s+ROOF)?|ROOF(?:\s+TERRACE)?)\s+SPE[CS]IFICATIONS?\.?:?$", re.I)
SPEC_WORD = re.compile(r"^SPE[CS]IFICATIONS?\.?:?$", re.I)
BULLETS = ("*", "•", "●", "·")
KEY_OF = {"GROUND FLOOR": "GROUND", "GROUND FLOORS": "GROUND", "FIRST FLOOR": "FIRST", "SECOND FLOOR": "SECOND", "THIRD FLOOR": "THIRD", "FOURTH FLOOR": "FOURTH",
  "FIFTH FLOOR": "FIFTH", "TOP FLOOR": "TOP", "UPPER FLOOR": "UPPER", "LOWER FLOOR": "LOWER", "MEZZANINE FLOOR": "MEZZANINE", "BASEMENT": "BASEMENT", "TERRACE": "TERRACE",
  "PORCH ROOF": "PORCH_ROOF", "MUMTY": "MUMTY", "MUMTY ROOF": "MUMTY", "ROOF": "ROOF", "ROOF TERRACE": "ROOF"}
ROOF_KEYS = ("TERRACE", "ROOF", "PORCH_ROOF", "MUMTY")
RUN_GAP = 2.5
ROW_TOL = 0.5
COLUMN_TOL = 0.6
BLOCK_GAP = 3.2
MAX_RUN_WORDS = 6

def heading_key(name: str) -> str:
  return KEY_OF.get(re.sub(r"\s+", " ", name.strip().upper()), re.sub(r"[^A-Z]+", "_", name.strip().upper()).strip("_"))

def _placed(words: list) -> dict:
  groups: dict = {}
  
  for w in words:
    if abs(((w.angle + 45) % 90) - 45) > 6:
      continue
    ang = (round(w.angle / 90.0) % 4) * 90
    rad = math.radians(ang)
    ux, uy = math.cos(rad), math.sin(rad)
    along = w.cx * ux + w.cy * uy
    across = -w.cx * uy + w.cy * ux
    groups.setdefault(ang, []).append({"w": w, "u0": along - w.length / 2.0, "u1": along + w.length / 2.0, "v": across, "size": max(float(w.size), 1.0), "text": w.text})
  return groups

def _headings(group: list) -> list:
  out: list = []
  
  for s in group:
    if not SPEC_WORD.match(s["text"]):
      continue
    row = sorted((p for p in group if abs(p["v"] - s["v"]) <= ROW_TOL * s["size"]), key=lambda p: p["u0"])
    i = row.index(s)
    start = i
    while start > 0 and row[start]["u0"] - row[start - 1]["u1"] <= RUN_GAP * s["size"]:
      start -= 1
    run = row[start:i + 1]
    for k in range(min(len(run), MAX_RUN_WORDS), 1, -1):
      cand = run[-k:]
      m = HEADING.match(" ".join(p["text"] for p in cand))
      if m:
        out.append({"key": heading_key(m.group("name")), "name": " ".join(p["text"] for p in cand), "u0": cand[0]["u0"], "v": sum(p["v"] for p in cand) / len(cand),
          "size": s["size"], "words": cand})
        break
  return out

def _margins(heads: list) -> list:
  us = sorted(h["u0"] for h in heads)
  size = max(h["size"] for h in heads)
  out: list = []
  for u in us:
    if out and u - out[-1][-1] <= size:
      out[-1].append(u)
    else:
      out.append([u])
  return [sum(g) / len(g) for g in out]

def _rows(members: list) -> list:
  out: list = []
  for p in sorted(members, key=lambda p: -p["v"]):
    if out and out[-1]["top"] - p["v"] <= ROW_TOL * max(p["size"], out[-1]["size"]):
      out[-1]["words"].append(p)
      out[-1]["size"] = max(out[-1]["size"], p["size"])
    else:
      out.append({"top": p["v"], "size": p["size"], "words": [p]})
  for r in out:
    r["words"].sort(key=lambda p: p["u0"])
    r["v"] = sum(p["v"] for p in r["words"]) / len(r["words"])
  return out

def _entries(rows: list) -> list:
  bullets = any(r["words"][0]["text"] in BULLETS for r in rows)
  entries: list = []
  for r in rows:
    words = [p["text"] for p in r["words"] if p["text"] not in BULLETS]
    if not words:
      continue
  
    text = " ".join(words)
    if r["words"][0]["text"] in BULLETS or not bullets or not entries:
      entries.append(text)
    else:
      entries[-1] += " " + text
  return entries

def read(words: list | None) -> dict:
  blocks: list = []
  used: set = set()
  
  for ang, group in sorted(_placed(words or []).items()):
    heads = _headings(group)
    if not heads:
      continue
  
    margins = _margins(heads)
    tol = COLUMN_TOL * max(h["size"] for h in heads)
    head_ids = {id(p["w"]) for h in heads for p in h["words"]}
    columns: dict = {}
    
    for p in group:
      if id(p["w"]) in head_ids:
        continue
      fit = [i for i, m in enumerate(margins) if m - tol <= p["u0"]]
      if fit:
        columns.setdefault(fit[-1], []).append(p)
        
    for ci, members in columns.items():
      mine = sorted((h for h in heads if min(range(len(margins)), key=lambda i: abs(margins[i] - h["u0"])) == ci), key=lambda h: -h["v"])
      rows = _rows(members)
      for hi, h in enumerate(mine):
        floor_v = mine[hi + 1]["v"] if hi + 1 < len(mine) else -math.inf
        mine_rows: list = []
        prev = h["v"]
        for r in rows:
          if r["v"] >= h["v"] - ROW_TOL * h["size"]:
            continue
        
          if r["v"] <= floor_v + ROW_TOL * h["size"]:
            break
          if prev - r["v"] > BLOCK_GAP * h["size"]:
            break
          mine_rows.append(r)
          prev = r["v"]
        entries = _entries(mine_rows)
        
        for r in mine_rows:
          used.update(id(p["w"]) for p in r["words"])
        used.update(id(p["w"]) for p in h["words"])
        blocks.append({"key": h["key"], "heading": h["name"], "entries": entries, "angle": ang})
  return {"blocks": blocks, "used": used}
