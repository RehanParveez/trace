from __future__ import annotations
import datetime
import math
import os
import tempfile
import yaml
from dataclasses import dataclass
from app.modules.drawings_boq.takeoff.proof.reading import formats as F
from app.modules.drawings_boq.takeoff.proof.reading import settings as ST
from app.modules.drawings_boq.takeoff.proof.reading import sets as S
from app.modules.drawings_boq.takeoff.proof import case_io as CIO

FILE = "regions.yaml"
KINDS = ("VIEW", "SCHEDULE", "LEGEND", "NOTES", "SECTION_PICTURE", "TITLE_BLOCK")
FIND, READ, JOIN, MEASURE = "FIND", "READ", "JOIN", "MEASURE"
STAGES = (FIND, READ, JOIN, MEASURE)
FOUND, MISSED, SPLIT, MERGED = "FOUND", "MISSED", "SPLIT", "MERGED"
OK_OUTCOME, WRONG_OUTCOME, MISSED_S, MISSED_R = "MATCHED_OK", "MATCHED_WRONG_VALUE", "MISSED_SILENT", "MISSED_REPORTED"
UNREAD_JOIN = "the source item was not read"

@dataclass
class Region:
  sheet: int
  kind: str
  box: tuple
  title: str
  truth: F.TruthStamp
  was: dict | None = None

def parse(rows: list, pages: int | None = None) -> list:
  problems = F._Problems()
  out = []

  for i, e in enumerate(rows, 1):
    if not isinstance(e, dict):
      problems.add(FILE, i, "-", "must be a mapping")
      continue
    F._only(e, ("sheet", "kind", "box", "title", "truth", "was"), FILE, i, problems)
    sheet = F._page(e.get("sheet"), pages if pages is not None else 10 ** 6, FILE, i, "sheet", problems)
    kind = e.get("kind")
    if kind not in KINDS:
      problems.add(FILE, i, "kind", f"must be one of {', '.join(KINDS)}")
    box = e.get("box")
    ok = isinstance(box, (list, tuple)) and len(box) == 4 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in box)
    if not ok or not (box[0] < box[2] and box[1] < box[3]):
      problems.add(FILE, i, "box", "must be [x0, y0, x1, y1] with x0 < x1 and y0 < y1, in page points")
      ok = False
    title = e.get("title")
    if not isinstance(title, str) or not title.strip():
      problems.add(FILE, i, "title", "is missing")
    stamp = F._stamp(e.get("truth"), FILE, i, problems, True)
    if None not in (sheet, stamp) and kind in KINDS and ok and isinstance(title, str) and title.strip():
      out.append(Region(sheet=sheet, kind=kind, box=tuple(float(v) for v in box), title=title.strip(), truth=stamp, was=F._was(e, FILE, i, problems)))

  if problems.items:
    raise F.TruthFormatError(problems.items)
  return out

def read_raw(folder: str) -> list:
  path = os.path.join(folder, FILE)
  if not os.path.isfile(path):
    return []
  with open(path, encoding="utf-8") as fh:
    rows = yaml.safe_load(fh) or []
  if not isinstance(rows, list):
    raise F.TruthFormatError([{"file": FILE, "row": "-", "field": "-", "message": "must be a list"}])
  return rows

def load(folder: str, pages: int | None = None) -> list:
  return parse(read_raw(folder), pages)

def write(folder: str, rows: list, pages: int | None = None) -> None:
  parse(rows, pages)
  text = yaml.dump(rows, Dumper=F._NoAlias, sort_keys=False, allow_unicode=True, width=200, default_flow_style=False)
  F.check_folder_key(folder)
  fd, tmp = tempfile.mkstemp(dir=folder, prefix=FILE + ".", suffix=".tmp")

  try:
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
      fh.write(text)
      fh.flush()
      os.fsync(fh.fileno())
    os.replace(tmp, os.path.join(folder, FILE))
  except OSError:
    if os.path.isfile(tmp):
      os.remove(tmp)
    raise

def _mean(pts: list) -> list:
  return [sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)]

def point_of(at: dict | None, geom: dict | None) -> list | None:
  xy = (at or {}).get("page_xy")
  if isinstance(xy, (list, tuple)) and len(xy) == 2:
    return [float(xy[0]), float(xy[1])]
  g = geom or {}
  pts = g.get("polygon") or g.get("polyline") or ([g["point"]] if g.get("point") else None)
  return _mean([[float(p[0]), float(p[1])] for p in pts]) if pts else None

def cfg() -> dict:
  return ST.load()["regions"]

def kind_of_class(cls: str) -> str | None:
  return cfg()["kind_of_class"].get(cls)

def inside(box: tuple, pt: list) -> bool:
  return box[0] <= pt[0] <= box[2] and box[1] <= pt[1] <= box[3]

def _area(b) -> float:
  return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])

def _cut(a, b) -> float:
  return _area((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))

def iou(a, b) -> float:
  inter = _cut(a, b)
  union = _area(a) + _area(b) - inter
  return 0.0 if union <= 0 else inter / union

def share_inside(a, b) -> float:
  return 0.0 if _area(a) <= 0 else _cut(a, b) / _area(a)

def draft(ts: F.TruthSet, sizes: dict, today: str) -> list:
  c = cfg()
  groups: dict = {}
  for e in ts.elements:
    kind = c["kind_of_class"].get(e.cls.value)
    pt = point_of(e.at, e.geom)
    if F.is_draft(e.truth) or kind is None or pt is None:
      continue
    groups.setdefault((e.sheet, kind), []).append((pt, e.cls.value))
  rows = []

  for (sheet, kind) in sorted(groups):
    w, h = sizes[sheet]
    diag = math.hypot(w, h)
    gap, pad = c["gap_share"][kind] * diag, c["pad_share"] * diag
    pts = groups[(sheet, kind)]
    parent = list(range(len(pts)))
    def find(i):
      while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
      return i
    for i in range(len(pts)):
      for j in range(i + 1, len(pts)):
        if math.hypot(pts[i][0][0] - pts[j][0][0], pts[i][0][1] - pts[j][0][1]) <= gap:
          parent[find(i)] = find(j)

    clusters: dict = {}
    for i in range(len(pts)):
      clusters.setdefault(find(i), []).append(pts[i])
    boxes = []
    for members in clusters.values():
      xs, ys = [m[0][0] for m in members], [m[0][1] for m in members]
      boxes.append(((min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad), members))
    for n, (box, members) in enumerate(sorted(boxes, key=lambda b: (b[0][1], b[0][0])), 1):
      classes = ", ".join(sorted({m[1] for m in members}))
      rows.append({"sheet": sheet, "kind": kind, "box": [round(v, 1) for v in box], "title": f"p{sheet} {kind} {n}",
        "truth": {"by": "CLAUDE_EYE", "checked": False, "source": "truth_item_positions", "date": today,
          "note": f"bounding box of the {len(members)} truth item(s) of {classes} that lie within {c['gap_share'][kind]:g} of the page diagonal of one another, padded by {c['pad_share']:g} of it; no page image was used, so a region with no truth item is not drafted and a box may be tighter than the region; check it with `reading sample`"}})
  return rows

def _page_sizes(pdf_path: str) -> dict:
  from app.modules.drawings_boq.takeoff.prep.extract import open_document
  with open(pdf_path, "rb") as fh:
    doc = open_document(fh.read())
  try:
    return {n + 1: tuple(float(v) for v in doc[n].get_size()) for n in range(len(doc))}
  finally:
    doc.close()

def cmd_regions_draft(args) -> int:
  today = datetime.date.today().isoformat()
  done = 0
  for ref in S.find_sets(args.cases_dir, args.root):
    if ref.link or CIO.is_audit_case(os.path.join(args.root, ref.case)):
      continue
    ts = F.load_set(ref.truth_folder)
    if args.set and not (ref.pdf_key.startswith(args.set) or ts.document.alias == args.set):
      continue
    if not ref.pdf_path:
      print(f"{ts.document.alias}: the PDF is not in the PDF folder; give --cases-dir")
      return 1
    if read_raw(ref.truth_folder) and not args.force:
      print(f"{ts.document.alias}: {FILE} already has {len(read_raw(ref.truth_folder))} row(s); --force replaces it")
      continue

    rows = draft(ts, _page_sizes(ref.pdf_path), today)
    kinds: dict = {}
    for r in rows:
      kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    print(f"{ts.document.alias}: {len(rows)} region(s) drafted from {len([e for e in ts.elements if not F.is_draft(e.truth)])} truth item(s): " + (", ".join(f"{k} {v}" for k, v in sorted(kinds.items())) or "none"))
    if args.write and rows:
      write(ref.truth_folder, rows, ts.document.pages)
    done += 1
  if not args.write:
    print("nothing written; add --write")
  return 0 if done else 1

def _reported(item) -> tuple | None:
  r = getattr(item, "region", None)
  return tuple(float(v) for v in r) if isinstance(r, (list, tuple)) and len(r) == 4 else None

def score_regions(regions: list, read) -> dict:
  c = cfg()
  need = float(c["overlap"])
  rows = []
  items_on: dict = {}
  for it in read.items:
    items_on.setdefault(it.sheet, []).append(it)
  by_sheet_kind: dict = {}

  for r in regions:
    by_sheet_kind.setdefault((r.sheet, r.kind), []).append(r)
  reported_all = {sheet: sorted({b for b in (_reported(i) for i in its) if b}) for sheet, its in items_on.items()}
  for r in regions:
    kind_items = [i for i in items_on.get(r.sheet, []) if c["kind_of_class"].get(i.cls.value) == r.kind]
    reported = reported_all.get(r.sheet, [])
    state, basis, n = MISSED, "none", 0
    hits = [b for b in reported if iou(b, r.box) >= need]
    pieces = [b for b in reported if share_inside(b, r.box) >= need and iou(b, r.box) < need]
    swallows = [b for b in reported if share_inside(r.box, b) >= need and any(o is not r and share_inside(o.box, b) >= need for o in regions if o.sheet == r.sheet)]
    if hits:
      state, basis, n = FOUND, "reported", len(hits)
    elif swallows:
      state, basis, n = MERGED, "reported", len(swallows)
    elif len(pieces) >= 2:
      state, basis, n = SPLIT, "reported", len(pieces)
    else:
      located = [i for i in kind_items if _reported(i) is None and point_of(None, i.geom) is not None]
      inside_n = sum(1 for i in located if inside(r.box, point_of(None, i.geom)))
      unlocated = [i for i in kind_items if _reported(i) is None and point_of(None, i.geom) is None]
      if inside_n:
        state, basis, n = FOUND, "inside", inside_n
      elif unlocated and len(by_sheet_kind[(r.sheet, r.kind)]) == 1:
        state, basis, n = FOUND, "class", len(unlocated)
    rows.append({"sheet": r.sheet, "kind": r.kind, "title": r.title, "box": list(r.box), "state": state, "basis": basis, "evidence": n, "checked": r.truth.checked is True})

  by_kind: dict = {}
  for row in rows:
    slot = by_kind.setdefault(row["kind"], {"truth": 0, FOUND: 0, MISSED: 0, SPLIT: 0, MERGED: 0})
    slot["truth"] += 1
    slot[row["state"]] += 1
  return {"rows": rows, "by_kind": by_kind, "reported_regions": sum(len(v) for v in reported_all.values())}

def _truth_miss(o: dict) -> bool:
  return o["side"] == "truth" and o["outcome"] != OK_OUTCOME and o["class"] != "BBS_FINDING"

def apply_stages(regions: list, region_rows: list, read, outcomes: list) -> dict:
  c = cfg()
  state_of = {(r["sheet"], r["kind"], r["title"]): r["state"] for r in region_rows}
  reads_of: dict = {}
  for it in read.items:
    reads_of.setdefault((it.sheet, it.cls.value), 0)
    reads_of[(it.sheet, it.cls.value)] += 1
  counts = {s: 0 for s in STAGES}
  unstaged = 0
  for o in outcomes:
    if not _truth_miss(o):
      continue
    stage, basis = None, None

    cls, unread = o["class"], o["outcome"] in (MISSED_S, MISSED_R)
    if cls == "REGISTER":
      stage, basis = (FIND if unread else READ), "register"
    elif ":FACT:" in o["id"]:
      stage, basis = (READ if unread else MEASURE), "fact"
    elif cls == "JOIN":
      src = o.get("src_class")
      if UNREAD_JOIN in (o.get("detail") or ""):
        stage, basis = (READ if reads_of.get((o["sheet"], src)) else FIND), "join_source"
      else:
        stage, basis = JOIN, "join"
    elif o["outcome"] == WRONG_OUTCOME:
      stage, basis = READ, "matched"
    else:
      kind = c["kind_of_class"].get(cls)
      pt = o.get("at")
      home = None
      
      if kind and pt:
        home = next((r for r in regions if r.sheet == o["sheet"] and r.kind == kind and inside(r.box, pt)), None)
      if home is not None:
        found = state_of.get((home.sheet, home.kind, home.title)) != MISSED
        stage, basis = (READ if found else FIND), "region"
      else:
        stage, basis = (READ if reads_of.get((o["sheet"], cls)) else FIND), "class"
    if stage is None:
      unstaged += 1
      continue
    o["stage"], o["stage_basis"] = stage, basis
    counts[stage] += 1
  return {"counts": counts, "unstaged": unstaged}
