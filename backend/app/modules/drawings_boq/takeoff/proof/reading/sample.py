from __future__ import annotations
import datetime
import hashlib
import io
import json
import math
import os
import random
import yaml
from app.modules.drawings_boq.takeoff.run import vocab as V
from app.modules.drawings_boq.takeoff.proof.reading import formats as F
from app.modules.drawings_boq.takeoff.proof.reading import regions as RG
from app.modules.drawings_boq.takeoff.proof.reading import sets as S
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.proof.reading import settings as ST

FILE_OF = {"register": "register.yaml", "element": "elements.yaml", "join": "joins.yaml", "region": "regions.yaml"}
LETTER = {"register": "R", "element": "E", "join": "J", "region": "G"}
KIND_OF = {v: k for k, v in LETTER.items()}
RIGHT, WRONG, CANNOT = "right", "wrong", "cannot tell"
VERDICTS = (RIGHT, WRONG, CANNOT)
SAMPLE_SHEET, META_SHEET = "Sample", "_meta"
ELEMENT_TOP = ("sheet", "class", "mark", "mark_kind")
REGISTER_FIELDS = ("sheet_no", "title", "role", "plan_kind", "floor", "discipline", "scale_ratio", "scale_basis", "text_type")
JOIN_SIDES = ("from", "to")
CROP_PX = 420
THUMB_SCALE = 0.35
STATUS_NO_TRUTH, STATUS_UNCHECKED, STATUS_PARTIAL, STATUS_OK, STATUS_REDRAFT = "NO_TRUTH", "UNCHECKED", "PARTIAL", "OK", "REDRAFT"

class SampleError(Exception):
  pass

def _unalias(value):
  if isinstance(value, dict):
    return {k: _unalias(v) for k, v in value.items()}
  if isinstance(value, list):
    return [_unalias(v) for v in value]
  return value

def read_rows(folder: str) -> dict:
  out = {}
  for kind, name in FILE_OF.items():
    path = os.path.join(folder, name)
    rows = []
    if os.path.isfile(path):
      with open(path, encoding="utf-8") as fh:
        rows = _unalias(yaml.safe_load(fh) or [])
    out[kind] = rows
  return out

def fingerprint(row: dict) -> str:
  return hashlib.sha1(json.dumps(row, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:10]

def stamp_of(row: dict) -> dict | None:
  s = row.get("truth")
  return s if isinstance(s, dict) else None

def is_draft_row(row: dict) -> bool:
  s = stamp_of(row) or {}
  return str(s.get("by") or "").strip().upper() == V.TruthSource.DRAFT.value or str(s.get("source") or "").strip().lower() == F.DRAFT_SOURCE

def is_truth_row(row: dict) -> bool:
  return isinstance(row, dict) and stamp_of(row) is not None and not is_draft_row(row)

def is_checked_row(row: dict) -> bool:
  return (stamp_of(row) or {}).get("checked") is True

def row_id(kind: str, n: int) -> str:
  return f"{LETTER[kind]}{n}"

def parse_id(text: str) -> tuple:
  text = str(text or "").strip().upper()
  if len(text) < 2 or text[0] not in KIND_OF or not text[1:].isdigit():
    raise SampleError(f"{text!r} is not a row id (R, E or J and a number)")
  return KIND_OF[text[0]], int(text[1:])

def total_rows(rows: dict) -> int:
  return sum(1 for kind in FILE_OF for r in rows[kind] if is_truth_row(r))

def stratum_of(kind: str, row: dict) -> str:
  if kind == "register":
    return "register"
  if kind == "join":
    return f"join:{row.get('kind')}"
  if kind == "region":
    return f"region:{row.get('kind')}"
  return f"element:{row.get('class')}"

def population(rows: dict) -> list:
  out = []
  for kind in FILE_OF:
    for n, r in enumerate(rows[kind], 1):
      if is_truth_row(r) and not is_checked_row(r):
        out.append({"id": row_id(kind, n), "kind": kind, "n": n, "stratum": stratum_of(kind, r), "row": r})
  return out

def log_rounds(log: list) -> dict:
  rounds: dict = {}
  for e in log or []:
    s = e.get("sample") if isinstance(e, dict) else None
    if not isinstance(s, dict) or not isinstance(s.get("round"), int):
      continue
    slot = rounds.setdefault(s["round"], {"drawn": 0, "right": 0, "wrong": 0, "cannot_tell": 0, "fixed": 0})
    slot["drawn"] = max(slot["drawn"], int(s.get("drawn") or 0))
    for k in ("right", "wrong", "cannot_tell", "fixed"):
      slot[k] += int(s.get(k) or 0)
  return rounds

def sample_size(total: int, available: int) -> int:
  return min(available, max(ST.sample_min(), math.ceil(ST.sample_share() * total)))

def allocate(sizes: dict, n: int) -> dict:
  have = sum(sizes.values())
  if n >= have:
    return dict(sizes)
  floor_one = 1 if n >= len(sizes) else 0
  ideal = {k: n * v / have for k, v in sizes.items()}
  got = {k: min(v, max(floor_one, int(ideal[k]))) for k, v in sizes.items()}
  while sum(got.values()) > n:
    k = max((k for k in got if got[k] > floor_one), key=lambda k: (got[k] - ideal[k], got[k], k))
    got[k] -= 1
  while sum(got.values()) < n:
    k = max((k for k in got if got[k] < sizes[k]), key=lambda k: (ideal[k] - got[k], sizes[k] - got[k], k))
    got[k] += 1
  return got

def draw(key: str, pop: list, n: int, round_no: int) -> list:
  by: dict = {}
  for p in pop:
    by.setdefault(p["stratum"], []).append(p)
  got = allocate({k: len(v) for k, v in by.items()}, n)
  picked = []
  for stratum in sorted(by):
    rng = random.Random(f"{key}:{round_no}:{stratum}")
    picked += [by[stratum][i] for i in sorted(rng.sample(range(len(by[stratum])), got[stratum]))]
  return sorted(picked, key=lambda p: (p["row"].get("sheet") if p["kind"] != "join" else (p["row"].get("from") or {}).get("sheet") or 0, p["kind"], p["n"]))

def _refname(ref: dict | None) -> str:
  ref = ref or {}
  return f"p{ref.get('sheet')} {ref.get('class')} {ref.get('key') or ref.get('mark')}"

def sheet_of(kind: str, row: dict):
  return (row.get("from") or {}).get("sheet") if kind == "join" else row.get("sheet")

def words(kind: str, row: dict) -> str:
  if kind == "register":
    parts = [f"{k}={row[k]}" for k in REGISTER_FIELDS if row.get(k) not in (None, "")]
    return "; ".join(parts)
  if kind == "region":
    return f"{row.get('kind')} '{row.get('title')}': box {row.get('box')} (page points)"
  if kind == "region":
    return f"{row.get('kind')} '{row.get('title')}': box {row.get('box')} (page points)"
  if kind == "join":
    return f"{row.get('kind')}: {_refname(row.get('from'))}  ->  {_refname(row.get('to'))}"
  attrs = row.get("attrs") or {}
  parts = [f"mark={row['mark']}"] if row.get("mark") is not None else []
  parts += [f"{k}={json.dumps(v) if isinstance(v, (list, dict)) else v}" for k, v in attrs.items()]
  geom = row.get("geom") or {}
  if geom:
    parts.append(f"geom={next(iter(geom))}")
  return "; ".join(parts)

def class_of(kind: str, row: dict) -> str:
  return {"register": "REGISTER", "join": str(row.get("kind") or "JOIN"), "region": f"REGION {row.get('kind')}"}.get(kind) or str(row.get("class") or "")

def mark_of(kind: str, row: dict) -> str:
  if kind == "element":
    return "" if row.get("mark") is None else str(row["mark"])
  return ""

def crop_png(contents: bytes, kind: str, row: dict) -> bytes | None:
  try:
    from app.modules.drawings_boq.takeoff.crops import render as CR
    page = int(sheet_of(kind, row))
    geom = row.get("geom") or {}
    pts, shape = None, "POINT"
    if geom.get("polygon"):
      pts, shape = geom["polygon"], "AREA"
    elif geom.get("polyline"):
      pts, shape = geom["polyline"], "LENGTH"
    elif kind == "region" and row.get("box"):
      x0, y0, x1, y1 = row["box"]
      pts, shape = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], "AREA"
    elif (row.get("at") or {}).get("page_xy"):
      pts = [row["at"]["page_xy"]]
    if pts:
      return CR.render_crop(contents, page, shape, {"points": pts}, CROP_PX)
    from app.modules.drawings_boq.takeoff.prep.extract import open_document
    doc = open_document(contents)
    try:
      img = doc[page - 1].render(scale=THUMB_SCALE).to_pil().convert("RGB")
    finally:
      doc.close()
    out = io.BytesIO()
    img.save(out, "PNG")
    return out.getvalue()
  except Exception:
    return None

def build_workbook(path: str, alias: str, key: str, round_no: int, total: int, pop_size: int, picks: list, contents: bytes | None, today: str) -> None:
  from openpyxl import Workbook
  from openpyxl.drawing.image import Image as XImage
  from openpyxl.styles import Alignment, Font
  from openpyxl.worksheet.datavalidation import DataValidation
  wb = Workbook()
  ws = wb.active
  ws.title = SAMPLE_SHEET
  head = ["Row", "Page", "Class", "Mark", "What the truth file says", "Crop (red = where the truth file puts it)", "Verdict", "Correct value", "Note"]
  ws.append(head)
  
  for c in ws[1]:
    c.font = Font(bold=True)
  for col, width in zip("ABCDEFGHI", (7, 6, 22, 12, 62, 46, 13, 38, 30)):
    ws.column_dimensions[col].width = width
  ws.freeze_panes = "A2"
  wrap = Alignment(wrap_text=True, vertical="top")
  for p in picks:
    ws.append([p["id"], sheet_of(p["kind"], p["row"]), class_of(p["kind"], p["row"]), mark_of(p["kind"], p["row"]), words(p["kind"], p["row"]), None, None, None, None])
    r = ws.max_row
    for c in ws[r]:
      c.alignment = wrap
    ws.row_dimensions[r].height = 120
    png = crop_png(contents, p["kind"], p["row"]) if contents else None
    if png:
      img = XImage(io.BytesIO(png))
      scale = 150.0 / max(img.width, img.height)
      img.width, img.height = int(img.width * scale), int(img.height * scale)
      ws.add_image(img, f"F{r}")
    else:
      ws.cell(row=r, column=6, value="no crop (the PDF was not given or could not be drawn)").alignment = wrap
      
  last = max(2, ws.max_row)
  dv = DataValidation(type="list", formula1='"' + ",".join(VERDICTS) + '"', allow_blank=True)
  ws.add_data_validation(dv)
  dv.add(f"G2:G{last}")
  guide = wb.create_sheet("Read me", 0)
  
  for line in (f"Truth check for {alias} (PDF key {key}), round {round_no}, drawn {today}.",
    f"{len(picks)} of {pop_size} unchecked truth rows ({total} truth rows in the set), drawn at random with the seed '{key}:{round_no}', in proportion to the class of the row.",
    "The truth rows were written by hand from the drawing; Trace's reading was not used to choose them.",
    "For each row look at the drawing, not at what Trace reads, and set Verdict: right, wrong, or cannot tell.",
    "If wrong, write the correct value in 'Correct value' as field=value, several separated by ;  (for an element: mark=C5; size_mm=[300, 450]). A wrong row with no correct value is counted wrong and left as it is.",
    "Do not add, delete or re-sort rows. Do not change columns A to F.",
    "Then run: python -m app.modules.drawings_boq.takeoff.proof.reading sample-apply <this file> --by \"<your name>\" [--write]"):
    guide.append([line])
  guide.column_dimensions["A"].width = 150
  meta = wb.create_sheet(META_SHEET)
  meta.sheet_state = "hidden"
  
  for k, v in (("key", key), ("alias", alias), ("round", round_no), ("drawn", len(picks)), ("date", today), ("total_rows", total)):
    meta.append([k, v])
  meta.append(["--"])
  for p in picks:
    meta.append([p["id"], fingerprint(p["row"])])
  wb.save(path)

def export_set(ref, out_dir: str, today: str | None = None) -> dict:
  ts = F.load_set(ref.truth_folder)
  rows = read_rows(ref.truth_folder)
  total = total_rows(rows)
  pop = population(rows)
  round_no = max(log_rounds(ts.log), default=0) + 1
  
  if not pop:
    return {"alias": ts.document.alias, "total": total, "population": 0, "drawn": 0, "path": None, "round": round_no}
  picks = draw(ref.pdf_key, pop, sample_size(total, len(pop)), round_no)
  contents = None
  if ref.pdf_path and os.path.isfile(ref.pdf_path):
    with open(ref.pdf_path, "rb") as fh:
      contents = fh.read()
  os.makedirs(out_dir, exist_ok=True)
  path = os.path.join(out_dir, f"sample_{ts.document.alias}_r{round_no}.xlsx")
  build_workbook(path, ts.document.alias, ref.pdf_key, round_no, total, len(pop), picks, contents, today or datetime.date.today().isoformat())
  return {"alias": ts.document.alias, "total": total, "population": len(pop), "drawn": len(picks), "path": path, "round": round_no, "crops": contents is not None}

def cmd_sample(args) -> int:
  refs = [r for r in S.find_sets(args.cases_dir, args.root) if not r.link]
  if args.set:
    refs = [r for r in refs if r.pdf_key.startswith(args.set) or F.load_set(r.truth_folder).document.alias == args.set]
    if not refs:
      print(f"no set matches {args.set!r}")
      return 2
    
  made = 0
  for ref in refs:
    if CIO.is_audit_case(os.path.join(args.root, ref.case)):
      continue
    res = export_set(ref, args.out)
    if res["path"] is None:
      print(f"{res['alias']}: nothing to sample ({res['total']} truth rows, none unchecked)")
      continue
    made += 1
    print(f"{res['alias']}: round {res['round']}, {res['drawn']} of {res['population']} unchecked truth rows ({res['total']} in the set){'' if res['crops'] else '; no crops, PDF not found, give --cases-dir'} -> {res['path']}")
  print(f"{made} workbook(s) written to {args.out}")
  return 0

def read_workbook(path: str) -> dict:
  from openpyxl import load_workbook
  wb = load_workbook(path, data_only=True)
  if META_SHEET not in wb.sheetnames or SAMPLE_SHEET not in wb.sheetnames:
    raise SampleError("this is not a sample workbook made by `reading sample` (no Sample or _meta sheet)")
  meta, prints, section = {}, {}, "head"
  for r in wb[META_SHEET].iter_rows(values_only=True):
    if r[0] == "--":
      section = "prints"
    elif section == "head":
      meta[str(r[0])] = r[1]
    elif r[0] is not None:
      prints[str(r[0])] = str(r[1])
      
  rows = []
  for r in wb[SAMPLE_SHEET].iter_rows(min_row=2, values_only=True):
    if r[0] is None:
      continue
    rows.append({"id": str(r[0]).strip().upper(), "verdict": str(r[6] or "").strip().lower(), "correct": str(r[7] or "").strip(), "note": str(r[8] or "").strip()})
  return {"meta": meta, "prints": prints, "rows": rows}

def parse_correction(text: str) -> list:
  out = []
  for part in [p.strip() for p in text.split(";") if p.strip()]:
    if "=" not in part:
      raise SampleError(f"{part!r}: write the correction as field=value")
    field, value = part.split("=", 1)
    try:
      parsed = yaml.safe_load(value.strip())
    except yaml.YAMLError as exc:
      raise SampleError(f"{part!r}: the value is not readable ({str(exc).splitlines()[0]})")
    out.append((field.strip(), parsed))
  return out

def _set_path(container: dict, path: list, value):
  for p in path[:-1]:
    container = container.setdefault(p, {})
    if not isinstance(container, dict):
      raise SampleError(f"{'.'.join(path)} does not lead to a field")
  old = container.get(path[-1])
  container[path[-1]] = value
  return old

def correct(kind: str, row: dict, field: str, value) -> None:
  parts = field.split(".")
  if kind == "register":
    if field not in REGISTER_FIELDS:
      raise SampleError(f"{field!r} is not a register field ({', '.join(REGISTER_FIELDS)})")
    old = _set_path(row, [field], value)
    
  elif kind == "region":
    if field not in ("kind", "title", "box"):
      raise SampleError(f"{field!r} is not a region field (kind, title, box)")
    old = _set_path(row, [field], value)
  elif kind == "join":
    if parts[0] not in JOIN_SIDES or len(parts) != 2:
      raise SampleError(f"{field!r}: a join is corrected as from.key, to.mark and so on")
    old = _set_path(row, parts, value)
  else:
    if parts[0] in ("truth", "at", "geom", "was"):
      raise SampleError(f"{field!r}: positions and stamps are not corrected here; fix elements.yaml by hand")
    if len(parts) == 1 and field in ELEMENT_TOP:
      old = _set_path(row, [field], value)
    else:
      old = _set_path(row, ["attrs"] + (parts[1:] if parts[0] == "attrs" else parts), value)
  was = row.setdefault("was", {})
  was.setdefault(field, old)

def apply_sheet(path: str, by: str, root: str, write: bool, cases_dir: str | None = None, today: str | None = None) -> dict:
  today = today or datetime.date.today().isoformat()
  if not by or not by.strip():
    raise SampleError("--by must name the person who checked; a check with no name is not a check")
  book = read_workbook(path)
  key = str(book["meta"].get("key") or "")
  refs = [r for r in S.find_sets(cases_dir, root) if not r.link and r.pdf_key == key]
  
  if not refs:
    raise SampleError(f"no truth folder has the key {key!r}")
  folder = refs[0].truth_folder
  ts = F.load_set(folder)
  rows = read_rows(folder)
  round_no = int(book["meta"].get("round") or 0)
  right = wrong = cannot = fixed = pending = 0
  refused, changed_kinds, wrong_ids, judged_ids = [], set(), [], []
  done = {i for e in ts.log if isinstance(e.get("sample"), dict) and e["sample"].get("round") == round_no for i in e["sample"].get("judged_ids") or []}
  
  for item in book["rows"]:
    kind, n = parse_id(item["id"])
    if item["id"] in done:
      refused.append(f"{item['id']}: already judged in round {round_no}")
      continue
    if n < 1 or n > len(rows[kind]):
      refused.append(f"{item['id']}: no such row any more")
      continue
    row = rows[kind][n - 1]
    if book["prints"].get(item["id"]) != fingerprint(row):
      refused.append(f"{item['id']}: the row changed after the workbook was made; draw a new sample")
      continue
    if item["verdict"] == "":
      pending += 1
      continue
    if item["verdict"] not in VERDICTS:
      refused.append(f"{item['id']}: verdict {item['verdict']!r} is not right, wrong or cannot tell")
      continue
    if item["verdict"] == CANNOT:
      cannot += 1
      judged_ids.append(item["id"])
      continue
    if item["verdict"] == WRONG:
      wrong += 1
      wrong_ids.append(item["id"])
      judged_ids.append(item["id"])
      if not item["correct"]:
        continue
      try:
        for field, value in parse_correction(item["correct"]):
          correct(kind, row, field, value)
      except SampleError as exc:
        refused.append(f"{item['id']}: {exc}")
        wrong -= 1
        wrong_ids.pop()
        judged_ids.pop()
        continue
      fixed += 1

    else:
      right += 1
      judged_ids.append(item["id"])
    stamp = row["truth"]
    stamp["checked"] = True
    stamp["checked_by"] = by.strip()
    stamp["checked_date"] = today
    changed_kinds.add(kind)
  res = {"alias": ts.document.alias, "key": key, "round": round_no, "right": right, "wrong": wrong, "cannot_tell": cannot, "fixed": fixed, "pending": pending, "refused": refused, "wrong_ids": wrong_ids, "written": False}
  
  if write and (right or wrong or cannot):
    files = {FILE_OF[k]: rows[k] for k in sorted(changed_kinds) if k != "region"}
    if "region" in changed_kinds:
      RG.parse(rows["region"], ts.document.pages)
    log = list(ts.log)
    log.append({"date": today, "by": by.strip(), "note": f"sample round {round_no}: {right + wrong + cannot} of the drawn rows judged ({right} right, {wrong} wrong of which {fixed} corrected, {cannot} cannot tell); {pending} left blank",
      "sample": {"round": round_no, "drawn": int(book["meta"].get("drawn") or 0), "right": right, "wrong": wrong, "cannot_tell": cannot, "fixed": fixed, "wrong_ids": wrong_ids, "judged_ids": judged_ids}})
    files["truth_log.yaml"] = log
    F.write_truth_files(folder, files, check=True)
    if "region" in changed_kinds:
      RG.write(folder, rows["region"], ts.document.pages)
    res["written"] = True
  return res

def cmd_sample_apply(args) -> int:
  try:
    res = apply_sheet(args.workbook, args.by, args.root, args.write, args.cases_dir)
  except (SampleError, F.TruthFormatError) as exc:
    print(f"refused: {exc}")
    return 1
  
  judged = res["right"] + res["wrong"]
  share = "n/a" if not judged else f"{res['wrong'] / judged:.1%}"
  print(f"{res['alias']} round {res['round']}: {res['right']} right, {res['wrong']} wrong ({res['fixed']} corrected), {res['cannot_tell']} cannot tell, {res['pending']} left blank; wrong share of the judged rows {share}")
  for r in res["refused"]:
    print(f"  not applied: {r}")
  if not args.write:
    print("nothing written; add --write to record this in the truth files")
    return 1 if res["refused"] else 0
  print("truth files written" if res["written"] else "nothing to write")
  return 1 if res["refused"] else 0

def quality(ts: F.TruthSet) -> dict:
  rows = [r for r in (*ts.register, *ts.elements, *ts.joins, *RG.load(ts.folder, ts.document.pages)) if r.truth is not None]
  truth = [r for r in rows if not F.is_draft(r.truth)]
  checked = sum(1 for r in truth if r.truth.checked is True)
  rounds = log_rounds(ts.log)
  out = {"truth_rows": len(truth), "draft_rows": len(rows) - len(truth), "checked_rows": checked, "checked_share": None if not truth else round(checked / len(truth), 4),
    "round": None, "judged": 0, "wrong": 0, "cannot_tell": 0, "wrong_share": None, "status": STATUS_NO_TRUTH if not truth else STATUS_UNCHECKED}
  
  if not rounds or not truth:
    return out
  latest = max(rounds)
  r = rounds[latest]
  judged = r["right"] + r["wrong"]
  out.update({"round": latest, "judged": judged, "wrong": r["wrong"], "cannot_tell": r["cannot_tell"], "wrong_share": None if not judged else round(r["wrong"] / judged, 4)})
  need = min(ST.sample_min(), len(truth))
  if judged < need:
    out["status"] = STATUS_PARTIAL
  elif r["wrong"] / judged > ST.wrong_share_limit():
    out["status"] = STATUS_REDRAFT
  else:
    out["status"] = STATUS_OK
  return out
