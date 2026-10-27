from __future__ import annotations
import re

HARD = 1.0
SOFT = 0.3
FUZZY_MAX = 1.0
FUZZY_MARGIN = 0.3
TITLE_MIN_WORDS = 2
TITLE_SIMILAR = 0.2
_CONFUSED = ({"J", "D", "U", "0", "O", "Q"}, {"I", "1", "L", "T"}, {"8", "B"}, {"5", "S"}, {"2", "Z"}, {"G", "6"}, {"7", "1"}, {"E", "F"})

def key(text: str) -> str:
  return re.sub(r"[^A-Z0-9]", "", (text or "").upper())

def _sub(a: str, b: str) -> float:
  if a == b:
    return 0.0
  return SOFT if any(a in s and b in s for s in _CONFUSED) else HARD

def distance(a: str, b: str) -> float:
  if abs(len(a) - len(b)) > 2:
    return 9.0
  prev = [float(j) for j in range(len(b) + 1)]
  for i, ca in enumerate(a, 1):
    cur = [float(i)]
    for j, cb in enumerate(b, 1):
      cur.append(min(prev[j] + HARD, cur[j - 1] + HARD, prev[j - 1] + _sub(ca, cb)))
    prev = cur
  return prev[-1]

def _range_cover(entry: dict) -> tuple | None:
  to = key(entry.get("to") or "")
  if not to:
    return None
  k = key(entry["no"])
  tail = to if len(to) >= len(k) else k[: len(k) - len(to)] + to
  m1 = re.match(r"^(.*?)(\d+)[A-Z]?$", k)
  m2 = re.match(r"^(.*?)(\d+)[A-Z]?$", tail)
  if not m1 or not m2 or m1.group(1) != m2.group(1):
    return None
  return m1.group(1), int(m1.group(2)), int(m2.group(2))

def _in_range(k: str, cover: tuple) -> bool:
  m = re.match(r"^(.*?)(\d+)[A-Z]?$", k)
  return bool(m) and m.group(1) == cover[0] and cover[1] <= int(m.group(2)) <= cover[2]

def _words(text: str) -> set:
  return {w for w in re.findall(r"[A-Z]{3,}", (text or "").upper())}

def _expected_sheets(entry: dict) -> int:
  cover = _range_cover(entry)
  if cover:
    return max(1, cover[2] - cover[1] + 1)
  return max(1, int(entry.get("sheets") or 1))

def check(sheets: list, lists: list) -> dict:
  entries: list = []
  seen: set = set()
  for lst in lists:
    for e in lst.get("entries") or []:
      k = key(e.get("no"))
      if not k or k in seen:
        continue
      seen.add(k)
      entries.append({**e, "key": k, "list_page": lst.get("page_no"), "cover": _range_cover(e)})

  numbered = [s for s in sheets if key(s.get("sheet_no"))]
  unread = [s["page_no"] for s in sheets if not key(s.get("sheet_no")) and s["page_no"] not in {l.get("page_no") for l in lists}]
  by_entry: dict = {}
  extra: list = []
  fuzzy: list = []

  for s in numbered:
    k = key(s["sheet_no"])
    hit = next((e for e in entries if e["key"] == k), None)
    how = "EXACT"
    if hit is None:
      hit = next((e for e in entries if e["cover"] and _in_range(k, e["cover"])), None)
      how = "RANGE"
    if hit is None and entries:
      ranked = sorted(((distance(k, e["key"]), e) for e in entries), key=lambda t: t[0])
      best = ranked[0]
      second = ranked[1][0] if len(ranked) > 1 else 9.0
      if best[0] <= FUZZY_MAX and second - best[0] >= FUZZY_MARGIN:
        hit, how = best[1], "FUZZY"
    if hit is None:
      extra.append({"page_no": s["page_no"], "sheet_no": s["sheet_no"]})
      continue
    by_entry.setdefault(hit["key"], []).append(s["page_no"])
    if how == "FUZZY":
      fuzzy.append({"page_no": s["page_no"], "read": s["sheet_no"], "listed": hit["no"]})
  missing = [{"no": e["no"], "title": e.get("title") or "", "list_page": e["list_page"]} for e in entries if e["key"] not in by_entry]

  more = []
  for e in entries:
    pages = by_entry.get(e["key"]) or []
    want = _expected_sheets(e)
    if len(pages) > want:
      more.append({"sheet_no": e["no"], "pages": sorted(pages), "listed_sheets": want})
  plain: dict = {}
  for s in numbered:
    plain.setdefault(key(s["sheet_no"]), []).append(s["page_no"])
  repeated = [{"sheet_no": next(x["sheet_no"] for x in numbered if key(x["sheet_no"]) == k), "pages": sorted(p)} for k, p in plain.items() if len(p) > 1]

  differs = []
  for e in entries:
    pages = by_entry.get(e["key"]) or []
    if len(pages) == 1:
      s = next((x for x in numbered if x["page_no"] == pages[0]), None)
      a, b = _words(s.get("title")), _words(e.get("title"))
      if s and len(a) >= TITLE_MIN_WORDS and len(b) >= TITLE_MIN_WORDS and len(a & b) / len(a | b) < TITLE_SIMILAR and key(s["sheet_no"]) == e["key"]:
        differs.append({"page_no": pages[0], "sheet_no": e["no"], "sheet_title": (s.get("title") or "")[:60], "listed_title": (e.get("title") or "")[:60]})
  return {"list_pages": sorted({l.get("page_no") for l in lists if l.get("page_no") is not None}), "listed": len(entries), "matched": len(by_entry), "missing": missing, "extra": extra,
    "more_than_listed": more, "repeated": repeated, "fuzzy": fuzzy, "title_differs": differs, "unread_pages": unread, "read": len(numbered), "sheets": len(sheets)}
