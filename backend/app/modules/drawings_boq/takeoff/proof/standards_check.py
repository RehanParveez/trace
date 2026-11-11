from __future__ import annotations
import argparse
import csv
import os
import re
import sys
import tempfile
import yaml
from app.engine.catalogue import standards as ST

BOOKS_ENV = "TRACE_BOOKS_DIR"
PIN_HEADER = "# Written by `python -m app.modules.drawings_boq.takeoff.proof.standards_check pin --write`. Do not edit by hand.\n"
SHOWN = 12
STOP = {"and", "the", "with", "for", "per", "of", "in", "on", "to", "by", "or", "a", "an", "all", "any", "not", "from", "type", "kinds", "kind", "including", "etc"}

def books_dir(arg: str | None) -> str | None:
  got = arg or os.environ.get(BOOKS_ENV)
  return got if got and os.path.isdir(got) else None

def find_pdf(folder: str, match: str) -> str | None:
  found = [os.path.join(folder, n) for n in os.listdir(folder) if n.lower().endswith(".pdf") and match.lower() in n.lower()]
  return max(found, key=os.path.getmtime) if found else None

def _read(path: str) -> bytes:
  with open(path, "rb") as fh:
    return fh.read()

def _book(book_id: str) -> dict:
  for b in ST.books():
    if b["id"] == book_id:
      return b
  raise SystemExit(f"{book_id} is not in standards_pk.yaml; books: {', '.join(b['id'] for b in ST.books())}")

def _write_pins(pn: dict, path: str = ST.PINS) -> None:
  with open(path, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(PIN_HEADER)
    yaml.safe_dump({"books": pn["books"], "entries": pn["entries"]}, fh, sort_keys=False, allow_unicode=True, width=160)

def _digits(rows: list) -> dict:
  return {r["ratio"]: [str(v) for v in r["values"]] for r in rows}

def table_diff(want: list, got: list) -> list:
  a, b = _digits(want), _digits(got)
  out = []
  for ratio in sorted(set(a) | set(b), key=lambda r: int(r.split(":")[1])):
    if a.get(ratio) != b.get(ratio):
      out.append(f"row {ratio}: pinned {a.get(ratio)}, book {b.get(ratio)}")
  return out

def verify_book(data: bytes, book_id: str, doc: dict | None = None, pn: dict | None = None) -> tuple:
  from app.modules.drawings_boq.pricing import standards_book as SB
  doc, pn = doc or ST.raw(), pn or ST.pins()
  bad: list = []
  pinned = pn["books"].get(book_id)
  if not pinned:
    return [f"{book_id}: not pinned; run: standards_check pin --book-id {book_id}"], 0
  if pinned.get("sha256") != SB.sha256_of(data):
    return [f"{book_id}: the file is not the pinned book (sha256 {SB.sha256_of(data)[:16]}, pinned {str(pinned.get('sha256'))[:16]}); a new edition is a new book id, not a changed pin"], 0
  where = {}
  for eid, p in pn["entries"].items():
    w = (p.get("where") or {}).get(book_id)
    if w:
      where[eid] = w

  pages = {pg["n"]: pg for pg in SB.scan(data, sorted({w["page"] for w in where.values()}))}
  by_id = {e["id"]: e for e in ST.entries(doc)}
  mortar = None
  checked = 0
  for eid, w in sorted(where.items()):
    e = by_id.get(eid)
    if e is None:
      continue
    checked += 1
    pg = pages.get(w["page"])
    if pg is None:
      bad.append(f"{eid}: page {w['page']} is not in the book")
      continue
    if e.get("read") == "mortar_table":
      if mortar is None:
        mortar = SB.read_mortar(SB.cells_of(data, pinned.get("norm_pages") or [w["page"]]))
      if mortar is None:
        bad.append(f"{eid}: no mortar table could be read from page(s) {pinned.get('norm_pages')}")
        continue
      diff = table_diff(pn["entries"][eid].get("table") or [], SB.table_rows(mortar))
      bad += [f"{eid} in {book_id}: {d}" for d in diff]
    else:
      find = (e.get("source") or {}).get("find") or []
      if w.get("cited") or not find:
        continue
      miss = [p for p in find if not re.search(p, pg["text"])]
      if miss:
        bad.append(f"{eid}: pattern {miss[0]!r} is no longer on page {w['page']} of {book_id}")
  return bad, checked

def gate(folder: str | None = None) -> tuple:
  bad = ST.problems()
  if bad:
    return False, f"{len(bad)} standards problem(s)", bad
  doc, pn = ST.raw(), ST.pins()
  note = ST.state()
  folder = books_dir(folder)
  if folder is None:
    return True, f"{note}; no book folder given ({BOOKS_ENV} or --books-dir), so no book was compared", []
  agree, absent, fails, unpinned = [], [], [], []
  for b in ST.books(doc):
    path = find_pdf(folder, b["match"])
    if path is None:
      absent.append(b["id"])
      continue
    if b["id"] not in pn["books"]:
      unpinned.append(b["id"])
      continue

    got, _n = verify_book(_read(path), b["id"], doc, pn)
    if got:
      fails += got
    else:
      agree.append(f"{pn['books'][b['id']]['sha256'][:16]}")
  if fails:
    return False, f"{len(fails)} figure(s) disagree with a book", fails
  tail = (f"; book {', '.join(agree)} agrees" if agree else "; no pinned book was in the folder") + (f"; not in the folder: {', '.join(absent)}" if absent else "") + (f"; found but not pinned: {', '.join(unpinned)}" if unpinned else "")
  return True, note + tail, []

def cmd_show(a) -> int:
  from app.modules.drawings_boq.pricing import standards_book as SB
  b = _book(a.book_id)
  path = a.book or (find_pdf(books_dir(a.books_dir) or "", b["match"]) if books_dir(a.books_dir) else None)
  if not path:
    print(f"no PDF for {b['id']}: give --book, or --books-dir with a file name that has {b['match']!r}")
    return 2
  data = _read(path)
  got = SB.from_book(data, ST.entries())
  print(f"{b['name']}: {os.path.basename(path)}, sha256 {got['sha256'][:16]}, {got['page_count']} pages")
  print(f"pages of material coefficients (they open with {SB.NORMS_MARK!r}): {got['norm_pages'] or 'none found'}")
  for pc in SB.cells_of(data, got["norm_pages"][:6]):
    print(f"\n--- page {pc.number}: the cells as rows, left to right (a ratio row is marked >>) ---")
    for row in SB.grid(pc)[:70]:
      texts = [c.text for c in row]
      print(("  >> " if SB.ratio_row(texts) else "     ") + " | ".join(texts)[:150])

  m = got["mortar"]
  print("\nmortar table as read:" if m else "\nmortar table: NOT READ (no row with a cement-sand ratio and figures beside it on the norms pages)")
  if m:
    print(f"  heading {m['item']!r}; {len(m['rows'])} ratio rows; {m['other']} other ratio-like rows skipped")
    for r in m["rows"]:
      print(f"  {r['ratio']}: {r['values']}  (page {r['page']})")
  print("\nfigures located by their patterns:")
  for eid, f in got["entries"].items():
    print(f"  {eid}: " + (f"page {f['page']}, ch. {f['chapter']}" + (" (chapter differs from the expected one)" if f.get("chapter_differs") else "") + (f", also on {f['also']}" if f["also"] else "") + (f"\n      line: {f['line']}" if f["line"] and 'table' not in f else "") if f else "NOT FOUND"))
  return 0

def cmd_pin(a) -> int:
  from app.modules.drawings_boq.pricing import standards_book as SB
  b = _book(a.book_id)
  path = a.book or (find_pdf(books_dir(a.books_dir) or "", b["match"]) if books_dir(a.books_dir) else None)
  if not path:
    print(f"no PDF for {b['id']}: give --book, or --books-dir with a file name that has {b['match']!r}")
    return 2

  doc, pn = ST.raw(), ST.pins()
  data = _read(path)
  got = SB.from_book(data, ST.entries(doc))
  cites = dict(c.split("=", 1) for c in (a.cite or []))
  standard_ids = {e["id"] for e in ST.entries(doc) if (e.get("source") or {}).get("kind") == ST.STANDARD and not e.get("read")}
  if set(cites) - standard_ids:
    print(f"--cite names {', '.join(sorted(set(cites) - standard_ids))}, which is not a STANDARD entry with a typed figure")
    return 2

  old = pn["books"].get(b["id"])
  notes, clash, missing = [], [], []
  if old and old.get("sha256") != got["sha256"]:
    notes.append(f"WARNING {b['id']} was pinned to sha256 {str(old.get('sha256'))[:16]} and this file is {got['sha256'][:16]}: a new edition is a new book id in standards_pk.yaml, not a re-pin")
  pn["books"][b["id"]] = {"sha256": got["sha256"], "file": os.path.basename(path), "page_count": got["page_count"], "norm_pages": got["norm_pages"]}
  by_id = {e["id"]: e for e in ST.entries(doc)}
  for eid, f in got["entries"].items():
    e = by_id[eid]
    if f is None and eid in cites:
      n = int(cites[eid])
      pg = SB.scan(data, [n])
      f = {"page": n, "chapter": pg[0]["chapter"] if pg else None, "line": None, "also": [], "cited": True}
    if f is None:
      missing.append(eid)
      continue
    p = pn["entries"].setdefault(eid, {})
    w = {"page": f["page"], "chapter": f["chapter"], "line": f["line"]}
    if f.get("cited"):
      w["cited"] = True
    if f["also"]:
      w["also_on"] = f["also"]
    p.setdefault("where", {})[b["id"]] = w
    if f["line"]:
      p.setdefault("item", f["line"])
    if e.get("read") == "mortar_table":
      if p.get("table") is None:
        p["table"], p["header"] = f["table"], f["header"]
      else:
        clash += [f"{eid}: {d}" for d in table_diff(p["table"], f["table"])]

  for ln in notes:
    print(ln)
  print(f"{b['name']}: sha256 {got['sha256'][:16]}; {sum(1 for e in got['entries'].values() if e)} of {len(got['entries'])} STANDARD entries located; norm pages {got['norm_pages']}")
  if missing:
    print(f"not found in this book ({len(missing)}): {', '.join(missing)}")
    print("  each stays unpinned; after reading the book, record the page with: --cite ID=PAGE")
  if clash:
    print("THE BOOKS DISAGREE: nothing written")
    for ln in clash:
      print("  " + ln)
    return 1
  with tempfile.TemporaryDirectory() as tmp:
    staged = os.path.join(tmp, "pins.yaml")
    _write_pins(pn, staged)
    bad = ST.problems(ST.PATH, staged)
  if bad:
    print("the pins would not pass the library's own checks: nothing written")
    for ln in bad[:SHOWN]:
      print("  " + ln)
    return 1
  if a.write:
    _write_pins(pn)
    print(f"wrote {ST.PINS}")
  else:
    print("nothing written; add --write")
  return 0

def cmd_verify(a) -> int:
  ok, note, details = gate(a.books_dir)
  print(("ok    " if ok else "FAIL  ") + "standards: " + note)
  for ln in details[:SHOWN]:
    print("      " + ln)
  if len(details) > SHOWN:
    print(f"      and {len(details) - SHOWN} more")
  return 0 if ok else 1

def words(text: str) -> set:
  return {w for w in re.findall(r"[a-z]{3,}", text.lower()) if w not in STOP}

def candidates(item, rows: list, limit: int = 8) -> list:
  from app.modules.drawings_boq import boq_logic as LOGIC
  from app.modules.drawings_boq.takeoff.proof.bench import rates as R
  mine = words(item.name)
  out = []
  for r in rows:
    if r.rate is None or r.rate <= 0 or r.rate_kind not in R.PRICED_KINDS or not r.unit_known or not r.unit:
      continue
    if LOGIC.convert_rate(r.unit_rate, r.unit, item.unit) is None:
      continue
    score = len(mine & words(r.description))
    if score:
      out.append((-score, r.item_no or "", r))
  out.sort(key=lambda t: (t[0], t[1]))
  return [(-s, r) for s, _n, r in out[:limit]]

def sheet_rows(items: list, rows: list) -> list:
  from app.modules.drawings_boq.takeoff.proof.bench import rates as R
  codes = R.by_code(rows)
  out = []
  for item in items:
    named = sorted({b.item for b in R.entries_for(item)})
    got, why = R.rate_for(item, codes)
    today = "priced" if got else why
    base = {"item": item.id, "name": item.name, "unit": item.unit, "mrs_codes_on_file": " ".join(sorted({b.item for b in item.billing.MRS_PB})), "codes_for_this_unit": " ".join(named), "today": today}
    cand = candidates(item, rows)
    if not cand:
      out.append({**base, "rank": "", "code": "", "wording": "", "book_unit": "", "rate": "", "page": "", "words_shared": "", "QS_choice": "", "note": "no candidate row"})
    for n, (score, r) in enumerate(cand, 1):
      out.append({**base, "rank": n, "code": r.item_no, "wording": r.description[:140], "book_unit": r.unit_raw, "rate": f"{r.rate}", "page": r.page, "words_shared": score, "QS_choice": "", "note": ""})
  return out

def cmd_sheet(a) -> int:
  from app.engine.catalogue import loader as CL
  from app.modules.drawings_boq.takeoff.proof.bench import rates as R
  path = a.book or (R.newest_book(a.books_dir, a.match) if a.books_dir and a.match else None)

  if not path:
    print("give --book, or --books-dir with --match")
    return 2
  rows, digest, report = R.book_rows(path, a.first_page, a.last_page, a.province, a.city)
  wanted = None
  if a.items_file:
    with open(a.items_file, encoding="utf-8") as fh:
      wanted = {ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")}
  items = [i for i in CL.items() if (i.id in wanted if wanted is not None else (i.billing.PRIVATE_QS or i.billing.MRS_PB))]
  if wanted is not None and wanted - {i.id for i in items}:
    print(f"not in the catalogue: {', '.join(sorted(wanted - {i.id for i in items}))}")
  lines = sheet_rows(items, rows)
  os.makedirs(a.out, exist_ok=True)
  target = os.path.join(a.out, "standards_item_sheet.csv")
  cols = ["item", "name", "unit", "mrs_codes_on_file", "codes_for_this_unit", "today", "rank", "code", "wording", "book_unit", "rate", "page", "words_shared", "QS_choice", "note"]
  with open(target, "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader()
    w.writerows(lines)

  many = sorted({i.id for i in items if R.rate_for(i, R.by_code(rows))[1] == "SEVERAL_CODES"})
  print(f"book {os.path.basename(path)} sha256 {digest[:16]}: {len(rows)} rows read; {len(items)} item(s) on the sheet, {len({r['item'] for r in lines if r['code']})} with at least one candidate")
  print(f"SEVERAL_CODES items (K-4's card chooses; this sheet records the candidate set): {len(many)}" + (f": {', '.join(many)}" if many else ""))
  print(f"wrote {target}; the QS fills QS_choice; MRS_PB goes into elements.yaml only from the signed sheet")
  return 0

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="The standards library against the rate books: show what the reader finds, pin a book, verify every book in a folder, and write the item sheet for the QS.")
  sub = ap.add_subparsers(dest="cmd", required=True)
  for name in ("show", "pin"):
    p = sub.add_parser(name)
    p.add_argument("--book-id", required=True, help="the id from standards_pk.yaml books")
    p.add_argument("--book", help="the rate book PDF")
    p.add_argument("--books-dir", help=f"a folder of rate books (default {BOOKS_ENV}); the PDF is the newest whose name has the book's match word")
    if name == "pin":
      p.add_argument("--cite", action="append", help="ID=PAGE: a figure the pin cannot find, on the page a person read it")
      p.add_argument("--write", action="store_true")
      
  p = sub.add_parser("verify")
  p.add_argument("--books-dir")
  p = sub.add_parser("sheet")
  p.add_argument("--book")
  p.add_argument("--books-dir")
  p.add_argument("--match")
  p.add_argument("--province", required=True)
  p.add_argument("--city", required=True)
  p.add_argument("--first-page", type=int, default=1)
  p.add_argument("--last-page", type=int)
  p.add_argument("--items-file", help="one item id per line (default: every item with a billing line)")
  p.add_argument("--out", default="mapping_out")
  a = ap.parse_args(argv)
  return {"show": cmd_show, "pin": cmd_pin, "verify": cmd_verify, "sheet": cmd_sheet}[a.cmd](a)

if __name__ == "__main__":
  sys.exit(main())
