from __future__ import annotations
import os
import re
import yaml
from app.engine.catalogue import conventions as CV
from app.engine.catalogue import model as CM

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "standards_pk.yaml")
PINS = os.path.join(HERE, "standards_pins.yaml")
ID_PREFIX = "STD_"
KINDS = CV.SOURCE_KINDS
STANDARD = CV.STANDARD
SOURCE_FIELDS = ("book", "sha256", "chapter", "item", "page")
SHAPES = ("value", "values", "range")
READERS = ("mortar_table",)
UNITS = ("table", "cft", "cft_per_100cft", "kg_per_cft", "bricks_per_cft", "ratio", "percent", "in", "mm", "mm2")
FIELDS = ("id", "name", "unit", "scope", "source")
SHA = re.compile(r"^[0-9a-f]{64}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

class StandardsError(Exception):
  pass

def _load(path: str) -> dict:
  if not os.path.isfile(path):
    return {}
  with open(path, encoding="utf-8") as fh:
    data = yaml.safe_load(fh)
  return data if isinstance(data, dict) else {}

def raw(path: str = PATH) -> dict:
  data = _load(path)
  if not isinstance(data.get("books"), list) or not isinstance(data.get("entries"), list):
    raise StandardsError("standards_pk.yaml must hold a books list and an entries list")
  return data

def pins(path: str = PINS) -> dict:
  data = _load(path)
  return {"books": dict(data.get("books") or {}), "entries": dict(data.get("entries") or {})}

def books(doc: dict | None = None) -> list:
  return [b for b in (doc or raw())["books"] if isinstance(b, dict)]

def entries(doc: dict | None = None) -> list:
  return [e for e in (doc or raw())["entries"] if isinstance(e, dict)]

def entry(entry_id: str, doc: dict | None = None) -> dict | None:
  for e in entries(doc):
    if e.get("id") == entry_id:
      return e
  return None

def _num(x) -> bool:
  return isinstance(x, (int, float)) and not isinstance(x, bool) and x == x

def _table_ok(table) -> bool:
  if not (isinstance(table, list) and table):
    return False
  for row in table:
    if not (isinstance(row, dict) and re.fullmatch(r"1:\d+", str(row.get("ratio") or "")) and isinstance(row.get("values"), list) and row["values"]):
      return False
    if not all(re.fullmatch(r"\d+(\.\d+)?", str(v)) for v in row["values"]):
      return False
  return True

def _shape(e: dict) -> list:
  return [k for k in SHAPES if k in e]

def problems(path: str = PATH, pins_path: str = PINS) -> list:
  out: list = []
  doc = raw(path)
  pn = pins(pins_path)
  book_ids: list = []
  for n, b in enumerate(doc["books"], 1):
    bid = str(b.get("id") or f"book {n}") if isinstance(b, dict) else f"book {n}"
    if not isinstance(b, dict) or not all(str(b.get(k) or "").strip() for k in ("id", "name", "edition", "match")):
      out.append(f"{bid}: a book needs id, name, edition and match (a word in the PDF file name)")
      continue
    if bid in book_ids:
      out.append(f"{bid}: book id used twice")
    book_ids.append(bid)
  seen: set = set()
  
  for n, e in enumerate(doc["entries"], 1):
    eid = str(e.get("id") or f"entry {n}") if isinstance(e, dict) else f"entry {n}"
    if not isinstance(e, dict):
      out.append(f"{eid}: not a mapping")
      continue
    gone = [f for f in FIELDS if f not in e]
    if gone:
      out.append(f"{eid}: missing {', '.join(gone)}")
      continue
    
    if eid in seen:
      out.append(f"{eid}: id used twice")
    seen.add(eid)
    if not eid.startswith(ID_PREFIX):
      out.append(f"{eid}: a standards id starts with {ID_PREFIX}")
    src = e["source"] if isinstance(e["source"], dict) else {}
    kind = src.get("kind")
    shapes = _shape(e)
    reader = e.get("read")
    if "table" in e:
      out.append(f"{eid}: a table is read from the book by `standards_check pin`, never typed here (set read: mortar_table)")
    if reader is not None:
      if reader not in READERS:
        out.append(f"{eid}: read must be one of {', '.join(READERS)}")
      if shapes:
        out.append(f"{eid}: a figure read from the book has no typed value, values or range")
      if kind != STANDARD:
        out.append(f"{eid}: only a STANDARD entry is read from a book")
      if e["unit"] != "table":
        out.append(f"{eid}: a table entry has unit table")
    elif len(shapes) != 1:
      out.append(f"{eid}: give exactly one of {', '.join(SHAPES)} (or read: for a table)")
      
    else:
      v = e[shapes[0]]
      if shapes[0] == "value" and not _num(v):
        out.append(f"{eid}: value must be a number")
      if shapes[0] == "values" and not (isinstance(v, list) and v and all(_num(x) for x in v)):
        out.append(f"{eid}: values must be a list of numbers")
      if shapes[0] == "range" and not (isinstance(v, list) and len(v) == 2 and all(_num(x) for x in v) and v[0] < v[1]):
        out.append(f"{eid}: range must be two numbers, low then high")
      if e["unit"] not in UNITS or e["unit"] == "table":
        out.append(f"{eid}: unit {e['unit']} is not one of {', '.join(u for u in UNITS if u != 'table')}")
    if reader is not None and e["unit"] not in UNITS:
      out.append(f"{eid}: unit {e['unit']} is not one of {', '.join(UNITS)}")
    scope = e["scope"]
    
    if not (isinstance(scope, list) and scope and all(s in CM.USES for s in scope)):
      out.append(f"{eid}: scope must list H, P or both")
    if kind not in KINDS:
      out.append(f"{eid}: source kind must be one of {', '.join(KINDS)}")
    elif kind in CV.SOURCE_LABELS and src.get("label") != CV.SOURCE_LABELS[kind]:
      out.append(f"{eid}: a {kind} source is labelled {CV.SOURCE_LABELS[kind]!r}")
    elif kind == STANDARD and not str(src.get("label") or "").startswith("Standard: "):
      out.append(f"{eid}: a STANDARD source is labelled 'Standard: ' and the book")
    if not str(src.get("note") or "").strip():
      out.append(f"{eid}: the source needs a note saying where the figure comes from")
    if kind == STANDARD:
      if src.get("book") not in book_ids:
        out.append(f"{eid}: source book {src.get('book')!r} is not in the books list")
      if src.get("find") is not None:
        if not (isinstance(src["find"], list) and src["find"] and all(isinstance(p, str) for p in src["find"])):
          out.append(f"{eid}: find must be a list of patterns")
        else:
          for p in src["find"]:
            try:
              re.compile(p)
            except re.error as exc:
              out.append(f"{eid}: find pattern {p!r} is not a regular expression ({exc})")
              
      if src.get("on") not in (None, "norms"):
        out.append(f"{eid}: on is norms or absent")
      if src.get("chapter") is not None and not isinstance(src["chapter"], int):
        out.append(f"{eid}: the expected chapter is a whole number")
      spot = src.get("expect_rows")
      if spot is not None and not (reader and isinstance(spot, dict) and all(re.fullmatch(r"1:\d+", str(k)) and isinstance(v, list) and v for k, v in spot.items())):
        out.append(f"{eid}: expect_rows is a spot-check of a table read from the book: ratio to a list of leading figures")
    elif kind in (CV.QS_CONVENTION, CV.TRACE_SEED):
      stray = [k for k in ("book", "chapter", "page", "item", "find") if k in src]
      if stray:
        out.append(f"{eid}: a {kind} figure does not name a book ({', '.join(stray)})")
      if kind == CV.QS_CONVENTION and not (str(src.get("by") or "").strip() and DATE.match(str(src.get("date") or ""))):
        out.append(f"{eid}: a QS_CONVENTION carries the QS's name (by) and the date he said it (date, YYYY-MM-DD)")
        
  for bid, p in pn["books"].items():
    if bid not in book_ids:
      out.append(f"pins: book {bid} is not in standards_pk.yaml")
    elif not (isinstance(p, dict) and SHA.match(str(p.get("sha256") or ""))):
      out.append(f"pins: book {bid} has no sha256")
  by_id = {e["id"]: e for e in entries(doc) if "id" in e}
  for eid, p in pn["entries"].items():
    e = by_id.get(eid)
    if e is None:
      out.append(f"pins: {eid} is not an entry of standards_pk.yaml")
      continue
    if (e.get("source") or {}).get("kind") != STANDARD:
      out.append(f"pins: {eid} is not a STANDARD entry, so nothing is pinned for it")
      continue
    if not isinstance(p, dict):
      out.append(f"pins: {eid} is not a mapping")
      continue
    for bid in (p.get("where") or {}):
      if bid not in book_ids:
        out.append(f"pins: {eid} is located in book {bid}, which is not in the books list")
    if e.get("read") and "table" in p and not _table_ok(p["table"]):
      out.append(f"pins: {eid} holds a table that is not rows of a ratio and figures")
    spot = ((e.get("source") or {}).get("expect_rows") or {}) if isinstance(e.get("source"), dict) else {}
    if spot and _table_ok(p.get("table")):
      rows = {r["ratio"]: [str(v) for v in r["values"]] for r in p["table"]}
      for ratio, lead in spot.items():
        got = rows.get(str(ratio))
        want = [str(v) for v in lead]
        if got is None or got[:len(want)] != want:
          out.append(f"pins: {eid} row {ratio} reads {got}, but Build File K quotes it as starting {want}; the table reader and the book layout disagree (run: standards_check show)")
  return out

def table(entry_id: str, pins_: dict | None = None) -> list | None:
  p = ((pins_ or pins())["entries"].get(entry_id) or {})
  return p.get("table") if _table_ok(p.get("table")) else None

def value(entry_id: str, doc: dict | None = None, pins_: dict | None = None):
  e = entry(entry_id, doc)
  if e is None:
    raise StandardsError(f"{entry_id} is not a standards entry")
  if e.get("read"):
    return table(entry_id, pins_)
  for k in SHAPES:
    if k in e:
      return e[k]
  return None

def source(entry_id: str, doc: dict | None = None, pins_: dict | None = None) -> dict:
  d = doc or raw()
  pn = pins_ or pins()
  e = entry(entry_id, d)
  if e is None:
    raise StandardsError(f"{entry_id} is not a standards entry")
  src = dict(e["source"])
  out = {"id": entry_id, "kind": src["kind"], "label": src["label"], "note": src.get("note")}
  if src["kind"] != STANDARD:
    out.update({"complete": True, "missing": []})
    return out
  
  book = src.get("book")
  pin_book = pn["books"].get(book) or {}
  where = ((pn["entries"].get(entry_id) or {}).get("where") or {}).get(book) or {}
  out.update({"book": book, "sha256": pin_book.get("sha256"), "chapter": where.get("chapter", src.get("chapter")), "item": src.get("item") or where.get("item") or (pn["entries"].get(entry_id) or {}).get("item"), "page": where.get("page")})
  out["missing"] = [f for f in SOURCE_FIELDS if not out.get(f)]
  out["complete"] = not out["missing"]
  return out

def label(entry_id: str, doc: dict | None = None, pins_: dict | None = None) -> str:
  s = source(entry_id, doc, pins_)
  if s["kind"] != STANDARD:
    return s["label"]
  if not s["complete"]:
    return f"{s['label']} (not yet pinned: {', '.join(s['missing'])} unknown)"
  return f"{s['label']}, ch. {s['chapter']}, p. {s['page']} (book {str(s['sha256'])[:16]})"

def counts(doc: dict | None = None, pins_: dict | None = None) -> dict:
  d = doc or raw()
  pn = pins_ or pins()
  out = {STANDARD: 0, "pinned": 0, CV.QS_CONVENTION: 0, CV.TRACE_SEED: 0}
  for e in entries(d):
    kind = (e.get("source") or {}).get("kind")
    if kind in out:
      out[kind] += 1
    if kind == STANDARD and source(e["id"], d, pn)["complete"] and (not e.get("read") or table(e["id"], pn)):
      out["pinned"] += 1
  return out

def state() -> str:
  c = counts()
  return f"{sum(c[k] for k in (STANDARD, CV.QS_CONVENTION, CV.TRACE_SEED))} entries: {c[STANDARD]} STANDARD ({c['pinned']} pinned to a book page), {c[CV.QS_CONVENTION]} QS_CONVENTION, {c[CV.TRACE_SEED]} TRACE_SEED"
