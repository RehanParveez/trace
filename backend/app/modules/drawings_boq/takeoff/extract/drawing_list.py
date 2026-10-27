from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.prep import title_strip as TS

MIN_ENTRIES = 3
ROW_SAME = 0.55
COLUMN_GAP_H = 3.0
ATTACH_PITCH = 0.7
TITLE_GAP_H = 6.0
MAX_HEADING_WORDS = 7
HEADING = re.compile(r"^(?:LIST|SCHEDULE|REGISTER|INDEX)\s+OF\s+(?:DRAWINGS?|DRGS?|SHEETS?)\b|^(?:DRAWINGS?|DRG|SHEET)\s+(?:LIST|INDEX|SCHEDULE|REGISTER)\b|^INDEX\s+TO\s+DRAWINGS?\b|^SHEET\s+INDEX\b", re.I)
_NUMBER = re.compile(r"^[A-Z0-9][A-Z0-9/\-.]*[A-Z0-9]$")
_DATE = re.compile(r"^\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}$")
_SHEETS = re.compile(r"\(?\s*(\d{1,3})\s*SHEETS?\s*\)?", re.I)
_TO = re.compile(r"^TO\s+(\S+)", re.I)

def heading_of(words: list):
  best = None
  for p in TS.phrases(words):
    text = p["text"].strip()
    if len(text.split()) <= MAX_HEADING_WORDS and HEADING.match(text):
      if best is None or p["h"] > best["h"]:
        best = p
  return best

def _number_like(text: str) -> bool:
  t = text.strip().upper().strip(".,;:|")
  if len(t) < 3 or not _NUMBER.match(t) or _DATE.match(t):
    return False
  has_digit = any(ch.isdigit() for ch in t)
  has_alpha = any(ch.isalpha() for ch in t)
  if not has_digit or not (has_alpha or "/" in t):
    return False
  return not re.match(r"^\d+[:]\d+$", t)

def _join_dashes(items: list) -> list:
  out: list = []
  i = 0
  while i < len(items):
    a = items[i]
    t = a["text"]
    j = i

    while j + 1 < len(items):
      nxt = items[j + 1]
      same = abs(nxt["mid"] - a["mid"]) <= 0.5 * max(nxt["h"], a["h"]) and nxt["a0"] - items[j]["a1"] <= 1.5 * a["h"]
      if not same:
        break
      if t.endswith("-") or nxt["text"].startswith("-") or nxt["text"] == "-":
        t = t + nxt["text"]
        j += 1
        continue
      break
    box = a["bbox"] if j == i else (min(a["bbox"][0], items[j]["bbox"][0]), min(a["bbox"][1], items[j]["bbox"][1]), max(a["bbox"][2], items[j]["bbox"][2]), max(a["bbox"][3], items[j]["bbox"][3]))
    out.append({**a, "text": t, "a1": items[j]["a1"], "bbox": box})
    i = j + 1
  return out

def _rows(words: list) -> list:
  items = []
  count: dict = {}
  for w in words:
    if not (w.text or "").strip() or abs(((float(w.angle or 0.0) + 45) % 90) - 45) > 8:
      continue
    q, a0, a1, c0, c1 = TS._frame(w)
    count[q] = count.get(q, 0) + 1
    items.append({"q": q, "text": w.text.strip(), "a0": a0, "a1": a1, "c0": c0, "c1": c1, "mid": (c0 + c1) / 2.0, "h": c1 - c0, "bbox": (w.x0, w.y0, w.x1, w.y1)})
  if not items:
    return []

  top = max(count, key=lambda k: count[k])
  items = [it for it in items if it["q"] == top]
  items.sort(key=lambda t: -t["mid"])
  rows: list = []
  for it in items:
    for r in rows:
      if abs(it["mid"] - r["mid"]) <= ROW_SAME * max(it["h"], r["h"]):
        r["items"].append(it)
        n = len(r["items"])
        r["mid"] += (it["mid"] - r["mid"]) / n
        r["h"] = max(r["h"], it["h"])
        break
    else:
      rows.append({"mid": it["mid"], "h": it["h"], "items": [it], "q": top})
  for r in rows:
    r["items"] = _join_dashes(sorted(r["items"], key=lambda t: t["a0"]))
  rows.sort(key=lambda r: -r["mid"])
  return rows

def _column_x(cands: list) -> list:
  if not cands:
    return []
  hs = sorted(c["h"] for c in cands)
  h = hs[len(hs) // 2]
  xs = sorted(c["a0"] for c in cands)
  groups = [[xs[0]]]
  for x in xs[1:]:
    if x - groups[-1][-1] > COLUMN_GAP_H * h:
      groups.append([x])
    else:
      groups[-1].append(x)
  need = max(MIN_ENTRIES, int(0.2 * len(cands)))
  return [(min(g) - COLUMN_GAP_H * h, max(g) + COLUMN_GAP_H * h) for g in groups if len(g) >= need]

def number_column(words: list, heading: dict | None = None):
  rows = _rows(words)
  if heading is not None and rows and heading["q"] == rows[0]["q"]:
    rows = [r for r in rows if r["mid"] < heading["c0"]]

  first = []
  for r in rows:
    for it in r["items"]:
      if _number_like(it["text"]):
        first.append(it)
        break
  cols = _column_x(first)
  if not cols:
    return None

  lo, hi = cols[0]
  boxes = [it["bbox"] for r in rows for it in r["items"] if lo <= it["a0"] <= hi and _number_like(it["text"])]
  if not boxes:
    return None
  h = max(it["h"] for r in rows for it in r["items"] if lo <= it["a0"] <= hi and _number_like(it["text"]))
  pad = 0.6 * h
  return (min(b[0] for b in boxes) - pad, min(b[1] for b in boxes) - pad, max(b[2] for b in boxes) + pad, max(b[3] for b in boxes) + pad)

def _contiguous(items: list) -> list:
  out: list = []
  for it in sorted(items, key=lambda t: t["a0"]):
    if out and it["a0"] - out[-1]["a1"] > TITLE_GAP_H * max(it["h"], out[-1]["h"]):
      break
    out.append(it)
  return out

def _sublines(items: list) -> list:
  lines: list = []
  for it in sorted(items, key=lambda t: -t["mid"]):
    for ln in lines:
      if abs(it["mid"] - ln["mid"]) <= ROW_SAME * max(it["h"], ln["h"]):
        ln["items"].append(it)
        break
    else:
      lines.append({"mid": it["mid"], "h": it["h"], "items": [it]})
  return lines

def read(words: list, heading: dict | None = None) -> dict:
  rows = _rows(words)
  if heading is not None and rows and heading["q"] == rows[0]["q"]:
    rows = [r for r in rows if r["mid"] < heading["c0"]]
  first: list = []
  for r in rows:
    for it in r["items"]:
      if _number_like(it["text"]):
        first.append({**it, "row": r})
        break
  cols = _column_x(first)
  if not cols:
    return {"entries": [], "rows": len(rows)}

  anchors: list = []
  for r in rows:
    for lo, hi in cols:
      cand = [it for it in r["items"] if lo <= it["a0"] <= hi and _number_like(it["text"])]
      if cand:
        anchors.append({"tok": cand[0], "mid": r["mid"], "h": r["h"], "lo": lo, "hi": hi})
  anchors.sort(key=lambda a: -a["mid"])
  pitches = sorted(abs(anchors[i]["mid"] - anchors[i + 1]["mid"]) for i in range(len(anchors) - 1) if anchors[i]["lo"] == anchors[i + 1]["lo"])
  pitch = pitches[len(pitches) // 2] if pitches else 2.0 * anchors[0]["h"]
  all_items = [it for r in rows for it in r["items"]]

  starts: list = []
  for a in anchors:
    nearby = [it for it in all_items if abs(it["mid"] - a["mid"]) <= 0.45 * pitch and it["a0"] > a["tok"]["a1"] and not _number_like(it["text"])]
    if nearby:
      f = min(nearby, key=lambda it: it["a0"])
      if f["a0"] - a["tok"]["a1"] <= 15.0 * max(f["h"], a["h"]):
        starts.append(f["a0"])

  starts.sort()
  col_left = starts[len(starts) // 2] if starts else min(a["tok"]["a1"] for a in anchors)
  out: list = []
  for a in anchors:
    tok = a["tok"]
    h = a["h"]
    neighbours = [abs(b["mid"] - a["mid"]) for b in anchors if b is not a and b["lo"] == a["lo"]]
    half = min(0.45 * pitch, 0.5 * min(neighbours)) if neighbours else 0.45 * pitch
    nxt_cols = [lo for lo, _hi in cols if lo > a["lo"]]
    limit = min(nxt_cols, default=1e9)
    band = [it for it in all_items if abs(it["mid"] - a["mid"]) <= half and it["a0"] < limit and it is not tok]
    lines = []
    to = None

    for ln in sorted(_sublines(band), key=lambda l: -l["mid"]):
      under_number = [it for it in ln["items"] if abs(it["a0"] - tok["a0"]) <= 2.5 * h]
      if under_number and re.match(r"^TO$", under_number[0]["text"], re.I):
        rest = sorted([it for it in ln["items"] if it["a0"] > under_number[0]["a0"]], key=lambda t: t["a0"])
        if rest:
          to = TS.clean_no(rest[0]["text"])
        continue
      cand = [it for it in ln["items"] if col_left - 4.0 * h <= it["a0"] <= col_left + 20.0 * h]
      if not cand:
        continue

      start = min(cand, key=lambda t: t["a0"])
      lines.append(_contiguous([it for it in ln["items"] if it["a0"] >= start["a0"]]))
    title = re.sub(r"\s+", " ", " ".join(" ".join(it["text"] for it in ws) for ws in lines)).strip(" |_")
    sheets = None
    whole = " ".join(it["text"] for it in sorted(band, key=lambda t: (-round(t["mid"] / max(h, 1.0)), t["a0"])))
    m = _SHEETS.search(whole)
    if m:
      sheets = int(m.group(1))
    out.append({"no": TS.clean_no(tok["text"]), "title": title[:160], "to": to, "sheets": sheets, "_mid": a["mid"]})

  merged: list = []
  for e in out:
    only_count = not re.sub(r"\(?\s*\d*\s*SHEETS?\s*\)?", "", e["title"], flags=re.I).strip(" ()")
    if merged and only_count and not merged[-1]["to"] and abs(merged[-1]["_mid"] - e["_mid"]) <= 1.1 * pitch:
      merged[-1]["to"] = e["no"]
      merged[-1]["sheets"] = merged[-1]["sheets"] or e["sheets"]
      continue
    merged.append(e)
  for e in merged:
    e.pop("_mid", None)
  return {"entries": merged, "rows": len(rows), "pitch": round(pitch, 2)}
