from __future__ import annotations
import math
import re
from collections import Counter
from app.modules.drawings_boq.takeoff.prep import title_strip as TS

LETTERED = re.compile(r"^[A-Z]{1,4}-\d{1,3}[A-Z]?$")
PLAIN = re.compile(r"^\d{1,3}[A-Z]?$")
SPLIT = re.compile(r"^([A-Z]{1,4})\s?-?\s?([0-9OIl]{1,3}[A-Z]?)$")
MARGIN = 0.04
MAX_REGION = 0.5
SEED_SHARE = 0.25
MIN_SEEDS = 2
REPEAT_SHARE = 0.5
MIN_REPEAT_PAGES = 3
CLUSTER_TOL = 0.12
SEQUENCE_SHARE = 0.7
FIRST_TOKEN, LABEL, LEARNED, DOMINANT = "FIRST_TOKEN", "LABEL", "LEARNED_BOX", "SET_VALUE"
CONFIRMED_REPEATED, CONFIRMED_SEQUENCE, UNCONFIRMED = "REPEATED", "SEQUENCE", "UNCONFIRMED"

def normalise(text: str | None) -> str | None:
  t = TS.clean_no(str(text or ""))
  m = SPLIT.match(t)
  if m:
    digits = m.group(2).translate(str.maketrans({"O": "0", "I": "1", "l": "1"}))
    cand = f"{m.group(1)}-{digits}"
    return cand if LETTERED.match(cand) else None
  return t if PLAIN.match(t) else None

def _label_value(text) -> str | None:
  if not text:
    return None
  whole = normalise(text)
  if whole:
    return whole
  words = str(text).split()
  first = normalise(words[0]) if len(words) > 1 else None
  return first if first and LETTERED.match(first) else None

def candidates(zone: list) -> list:
  out = []
  for z in zone:
    text = z["t"].strip()
    for tok in (text, text.split()[0] if text.split() else ""):
      v = normalise(tok)
      if v and LETTERED.match(v):
        out.append({"v": v, "b": z["b"]})
        break
  return out

def _centre(b: list) -> tuple:
  return (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0

def _inside(region: list, b: list) -> bool:
  cx, cy = _centre(b)
  return region[0] <= cx <= region[2] and region[1] <= cy <= region[3]

def _hull(boxes: list, margin: float) -> list:
  return [round(min(b[0] for b in boxes) - margin, 4), round(min(b[1] for b in boxes) - margin, 4), round(max(b[2] for b in boxes) + margin, 4), round(max(b[3] for b in boxes) + margin, 4)]

def _repeating(rows: list) -> list | None:
  clusters: list = []
  for idx, r in enumerate(rows):
    for c in candidates(r["zone"]):
      cx, cy = _centre(c["b"])
      for k in clusters:
        if abs(cx - k["cx"]) <= CLUSTER_TOL and abs(cy - k["cy"]) <= CLUSTER_TOL:
          k["m"].append((idx, c["b"]))
          break
      else:
        clusters.append({"cx": cx, "cy": cy, "m": [(idx, c["b"])]})
        
  need = max(MIN_REPEAT_PAGES, math.ceil(REPEAT_SHARE * len(rows)))
  best = max(clusters, key=lambda k: len({m[0] for m in k["m"]}), default=None)
  if best is None or len({m[0] for m in best["m"]}) < need:
    return None
  return [m[1] for m in best["m"]]

def learn(rows: list) -> dict | None:
  seeds = [r["box"] for r in rows if r.get("no") and r.get("box")]
  basis, boxes = None, None
  if len(seeds) >= max(MIN_SEEDS, math.ceil(SEED_SHARE * len(rows))):
    basis, boxes = LABEL, seeds
    
  else:
    rep = _repeating(rows)
    if rep:
      basis, boxes = "REPEATING_NUMBERS", rep
  if not boxes:
    return None
  region = _hull(boxes, MARGIN)
  if region[2] - region[0] > MAX_REGION or region[3] - region[1] > MAX_REGION:
    return None
  return {"region": region, "basis": basis, "seeds": len(boxes), "pages": len(rows)}

def _sequence(values: list) -> bool:
  pairs = []
  for a, b in zip(values, values[1:]):
    ma, mb = re.match(r"^([A-Z]*)-?(\d+)", a), re.match(r"^([A-Z]*)-?(\d+)", b)
    if ma and mb and ma.group(1) == mb.group(1):
      pairs.append(int(mb.group(2)) >= int(ma.group(2)))
  return len(pairs) >= 2 and sum(pairs) / len(pairs) >= SEQUENCE_SHARE

def confirm(values: list) -> str:
  if len(values) < 2:
    return UNCONFIRMED
  top = Counter(values).most_common(1)[0][1]
  if len(set(values)) == 1 or top / len(values) >= REPEAT_SHARE:
    return CONFIRMED_REPEATED
  return CONFIRMED_SEQUENCE if _sequence(values) else UNCONFIRMED

def settle(rows: list) -> dict:
  rejected, clean = [], []
  for r in rows:
    v = _label_value(r.get("no"))
    if r.get("no") and not v:
      rejected.append({"page": r["page"], "text": str(r["no"])[:30]})
    clean.append({**r, "no": v, "box": r.get("box") if v else None})
  learned = learn(clean)
  numbers: dict = {}
  
  for r in clean:
    if r["no"]:
      numbers[r["page"]] = {"no": r["no"], "basis": LABEL}
      continue
    found = {c["v"] for c in candidates(r["zone"]) if learned and _inside(learned["region"], c["b"])}
    if len(found) == 1:
      numbers[r["page"]] = {"no": next(iter(found)), "basis": LEARNED}
    elif not learned and normalise(r.get("first_token")):
      numbers[r["page"]] = {"no": normalise(r["first_token"]), "basis": FIRST_TOKEN}
    else:
      numbers[r["page"]] = {"no": None, "basis": None, "ambiguous": sorted(found) if len(found) > 1 else None}
  dominant = _dominant(numbers, len(clean))
  
  if dominant:
    for r in clean:
      here = numbers[r["page"]]
      if here["no"] != dominant and any(c["v"] == dominant for c in candidates(r["zone"])):
        numbers[r["page"]] = {"no": dominant, "basis": DOMINANT}
  numbered = sum(1 for n in numbers.values() if n["no"])
  repeated = None if dominant or numbered * 2 >= len(clean) else _repeated_value(clean)
  if repeated:
    for r in clean:
      if not numbers[r["page"]]["no"] and any(c["v"] == repeated for c in candidates(r["zone"])):
        numbers[r["page"]] = {"no": repeated, "basis": DOMINANT}
  dominant = dominant or repeated
  return {"numbers": numbers, "learned": learned, "confirmed": confirm([n["no"] for _p, n in sorted(numbers.items()) if n["no"]]), "rejected": rejected, "dominant": dominant}

def _repeated_value(rows: list) -> str | None:
  seen = Counter()
  for r in rows:
    seen.update({c["v"] for c in candidates(r["zone"])})
  common = [v for v, n in seen.items() if n >= MIN_REPEAT_PAGES and n / max(len(rows), 1) >= REPEAT_SHARE]
  return common[0] if len(common) == 1 else None

def _dominant(numbers: dict, pages: int) -> str | None:
  counts = Counter(n["no"] for n in numbers.values() if n["no"])
  if not counts:
    return None
  value, top = counts.most_common(1)[0]
  return value if top >= MIN_REPEAT_PAGES and top / max(pages, 1) >= REPEAT_SHARE else None

def apply(pages: list) -> dict:
  rows = []
  for no, meta in sorted(pages, key=lambda p: p[0]):
    strip = meta.get("sheet_strip") or {}
    box = next((e.get("box") for e in strip.get("evidence") or [] if e.get("label") == "sheet_no"), None)
    title = meta.get("title") if isinstance(meta.get("title"), dict) else {}
    ident = meta.get("identity") if isinstance(meta.get("identity"), dict) else {}
    rows.append({"page": no, "no": strip.get("sheet_no"), "box": box, "zone": strip.get("zone") or [], "first_token": title.get("sheet_no") or ident.get("sheet_no")})
    
  res = settle(rows)
  for no, meta in pages:
    n = res["numbers"].get(no) or {"no": None, "basis": None}
    strip = meta.get("sheet_strip")
    if isinstance(strip, dict):
      strip["sheet_no"] = n["no"]
    for holder in (meta.get("title"), meta.get("identity")):
      if isinstance(holder, dict):
        holder["sheet_no"] = n["no"]
    meta["sheet_no_basis"] = n["basis"]
  return {"learned": res["learned"], "confirmed": res["confirmed"], "rejected": res["rejected"], "dominant": res["dominant"], "assigned": sum(1 for n in res["numbers"].values() if n["no"])}
