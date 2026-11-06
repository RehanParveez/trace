from __future__ import annotations
import math
import re
from app.engine.measure import rule_registry as RR

RULE = "FINISH_SPEC_ITEMS"
META_KEY = "finish_spec_items"
SOURCE_KEY = "finish_specs"
HEADING = re.compile(r"^(?P<name>.+?)\s+SPECIFICATIONS?$", re.I)
BULLETS = ("*", "•", "·", "-", "–", "—", "▪", "●")
FRACTIONS = {"½": 0.5, "¼": 0.25, "¾": 0.75}
THICK = re.compile(r"(?P<n>\d+(?:\.\d+)?)\s*(?P<f>[½¼¾]|\d/\d)?\s*[\"”″]\s*(?:-\s*\d+(?:\.\d+)?\s*[\"”″]\s*)?(?:THICK|TH\b)", re.I)
INITIALS = re.compile(r"^(?:[A-Za-z]\.){2,}$")
MIN_ENTRIES = 2
GAP_FACTOR = 3.0
WRAP_FACTOR = 2.2

def enabled() -> bool:
  return RR.on(RULE)

def thickness_in(text: str) -> float | None:
  m = THICK.search(text or "")
  if m is None:
    return None
  value = float(m.group("n"))
  frac = m.group("f")
  
  if frac:
    value += FRACTIONS[frac] if frac in FRACTIONS else int(frac.split("/")[0]) / int(frac.split("/")[1])
  return value

def _frame(angle: float) -> tuple:
  a = math.radians(round(float(angle) / 90.0) * 90.0)
  r = (round(math.cos(a)), round(math.sin(a)))
  return r, (r[1], -r[0])

def _lines(words: list, angle: float) -> list:
  r, n = _frame(angle)
  rows = []
  
  for w in words:
    xs, ys = (w.x0, w.x1), (w.y0, w.y1)
    u = [x * r[0] + y * r[1] for x in xs for y in ys]
    v = [x * n[0] + y * n[1] for x in xs for y in ys]
    rows.append({"w": w, "u0": min(u), "u1": max(u), "v0": min(v), "v1": max(v)})
  if not rows:
    return []
  
  rows.sort(key=lambda t: (t["v0"] + t["v1"]) / 2)
  thick = sorted(t["v1"] - t["v0"] for t in rows)[len(rows) // 2] or 1.0
  lines: list = []
  
  for t in rows:
    vc = (t["v0"] + t["v1"]) / 2
    if lines and abs(vc - lines[-1]["v"]) <= thick * 0.5:
      lines[-1]["words"].append(t)
      lines[-1]["v"] = sum((x["v0"] + x["v1"]) / 2 for x in lines[-1]["words"]) / len(lines[-1]["words"])
    else:
      lines.append({"v": vc, "words": [t]})
  split: list = []
  
  for ln in lines:
    ws = sorted(ln["words"], key=lambda t: t["u0"])
    run = [ws[0]]
    for t in ws[1:]:
      if t["u0"] - max(x["u1"] for x in run) > thick * GAP_FACTOR:
        split.append({"v": ln["v"], "words": run})
        run = []
      run.append(t)
    split.append({"v": ln["v"], "words": run})
  lines = split
  for ln in lines:
    ln["words"].sort(key=lambda t: t["u0"])
    ln["text"] = " ".join((t["w"].text or "").strip() for t in ln["words"]).strip()
    ln["u0"] = ln["words"][0]["u0"]
    ln["u1"] = max(t["u1"] for t in ln["words"])
    ln["tol"] = thick
  return lines

def _sentence_end(text: str) -> str:
  last = text.split(" ")[-1] if text else ""
  if text.endswith(".") and not INITIALS.match(last):
    return text[:-1].strip()
  return text

def _bullet_of(line: dict, bullets: list) -> dict | None:
  best = None
  for b in bullets:
    gap = line["u0"] - b["u1"]
    if gap > line["tol"] * GAP_FACTOR or gap < -line["tol"] or abs((b["v0"] + b["v1"]) / 2 - line["v"]) > line["tol"] * 0.6:
      continue
    if best is None or gap < line["u0"] - best["u1"]:
      best = b
  return best

def blocks_of(words: list) -> list:
  by_angle: dict = {}
  for w in words:
    if (w.text or "").strip():
      by_angle.setdefault(round(float(w.angle) / 90.0) % 4, []).append(w)
  out = []
  
  for group in by_angle.values():
    marks = [w for w in group if w.text.strip() in BULLETS]
    text = [w for w in group if w.text.strip() not in BULLETS]
    lines = _lines(text, group[0].angle)
    if not lines:
      continue
    r, n = _frame(group[0].angle)
    bullets = []
    
    for w in marks:
      u = [x * r[0] + y * r[1] for x in (w.x0, w.x1) for y in (w.y0, w.y1)]
      v = [x * n[0] + y * n[1] for x in (w.x0, w.x1) for y in (w.y0, w.y1)]
      bullets.append({"w": w, "u0": min(u), "u1": max(u), "v0": min(v), "v1": max(v)})
    heads = [ln for ln in lines if HEADING.match(ln["text"])]
    entries = []
    for ln in lines:
      if HEADING.match(ln["text"]):
        continue
      bullet = _bullet_of(ln, bullets)
      if bullet is not None:
        entries.append({"line": ln, "bullet": bullet, "parts": [ln["text"]], "last": ln})
    for ln in sorted(lines, key=lambda t: t["v"]):
      if HEADING.match(ln["text"]) or any(e["line"] is ln for e in entries):
        continue
      for e in entries:
        first, last = e["line"], e["last"]
        if 0 < ln["v"] - last["v"] <= ln["tol"] * WRAP_FACTOR and abs(ln["u0"] - first["u0"]) <= ln["tol"] * 2:
          e["parts"].append(ln["text"])
          e["last"] = ln
          break
        
    owned: dict = {}
    for e in entries:
      ln, bullet = e["line"], e["bullet"]
      before = [h for h in heads if h["v"] < ln["v"] and h["u0"] - h["tol"] <= bullet["u0"] <= h["u1"] + h["tol"]]
      if not before:
        continue
      head = max(before, key=lambda h: h["v"])
      text = _sentence_end(" ".join(e["parts"]).strip())
      if not text:
        continue
      ws = [t["w"] for t in ln["words"]] + [bullet["w"]]
      at = [round((min(w.x0 for w in ws) + max(w.x1 for w in ws)) / 2, 2), round((min(w.y0 for w in ws) + max(w.y1 for w in ws)) / 2, 2)]
      owned.setdefault(id(head), (head, []))[1].append({"v": ln["v"], "text": text, "at": at})
    for head, items in owned.values():
      if len(items) < MIN_ENTRIES:
        continue
      name = HEADING.match(head["text"]).group("name").strip().upper()
      layers = []
      
      for order, e in enumerate(sorted(items, key=lambda e: e["v"]), 1):
        rec = {"order": order, "text": e["text"], "at": e["at"]}
        t = thickness_in(e["text"])
        if t is not None:
          rec["thickness_in"] = t
        layers.append(rec)
      out.append({"mark": name, "layers": layers})
  return sorted(out, key=lambda b: (b["layers"][0]["at"][1], b["layers"][0]["at"][0]))

def read(raw) -> dict | None:
  if not enabled() or not raw.words:
    return None
  blocks = blocks_of(raw.words)
  return {"blocks": blocks} if blocks else None

def apply(rows: list) -> int:
  made = 0
  for row in rows:
    meta = row.get("meta")
    if meta is None:
      continue
    
    meta.pop(META_KEY, None)
    if not enabled():
      continue
    blocks = ((meta.get("structure_tables") or {}).get(SOURCE_KEY) or {}).get("blocks") or []
    if blocks:
      meta[META_KEY] = {"blocks": blocks}
      made += sum(len(b["layers"]) for b in blocks)
  return made
