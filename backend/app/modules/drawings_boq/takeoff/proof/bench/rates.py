from __future__ import annotations
import argparse
import hashlib
import os
import re
import sys
from app.engine.catalogue import choices as CH
from app.engine.catalogue import loader as CL
from app.modules.drawings_boq import boq_logic as LOGIC
from app.modules.drawings_boq.pricing import mrs_import as MI
from app.modules.drawings_boq.pricing import rate_profile as RP
from app.modules.drawings_boq.takeoff.proof.answers import answers as AN
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.questions import answers as QAN

HERE = os.path.dirname(os.path.abspath(__file__))
RATES = os.path.join(HERE, "rates.yaml")
SHARES = os.path.join(HERE, "money_shares.yaml")
PRICED_KINDS = ("COMPOSITE", "FULL_PRICE")
REASONS = ("NO_MRS_CODE", "NO_CODE_FOR_UNIT", "SEVERAL_CODES", "CODE_NOT_IN_BOOK", "CODE_REPEATED_IN_BOOK", "NO_RATE_IN_BOOK", "LABOUR_ONLY", "BOOK_UNIT_UNKNOWN", "UNIT_CANNOT_CONVERT")
TOP = 20

def newest_book(folder: str, word: str) -> str:
  found = [os.path.join(folder, n) for n in os.listdir(folder) if n.lower().endswith(".pdf") and word.lower() in n.lower()]
  if not found:
    raise FileNotFoundError(f"no PDF with {word!r} in its name under {folder}")
  return max(found, key=os.path.getmtime)

def book_rows(path: str, first_page: int, last_page: int | None, province: str | None, city: str | None) -> tuple:
  with open(path, "rb") as fh:
    data = fh.read()
  digest = hashlib.sha256(data).hexdigest()
  got = MI.read_table(data, first_page, last_page, digest, RP.for_place(province, city))
  return got["rows"], digest, got["report"]

def by_code(rows: list) -> dict:
  out: dict = {}
  for r in rows:
    if r.item_no:
      out.setdefault(re.sub(r"-n\d+$", "", r.item_no), []).append(r)
  return out

def entries_for(item) -> list:
  want = LOGIC.normalise_unit(item.unit)
  keys = {y.qty for y in item.yields if LOGIC.normalise_unit(y.unit) == want}
  return [b for b in item.billing.MRS_PB if b.qty in keys]

def rate_for(item, codes: dict, chosen: dict | None = None) -> tuple:
  if not item.billing.MRS_PB:
    return None, "NO_MRS_CODE"
  named = sorted({b.item for b in entries_for(item)})
  if not named:
    return None, "NO_CODE_FOR_UNIT"
  if len(named) > 1:
    pick = (chosen or {}).get(item.id)
    if pick not in named:
      return None, "SEVERAL_CODES"
    named = [pick]
  code = named[0]
  rows = codes.get(code) or []
  if not rows:
    return None, "CODE_NOT_IN_BOOK"
  if len(rows) > 1:
    return None, "CODE_REPEATED_IN_BOOK"
  r = rows[0]
  if r.rate is None or r.rate <= 0:
    return None, "NO_RATE_IN_BOOK"
  if r.rate_kind not in PRICED_KINDS:
    return None, "LABOUR_ONLY"
  if not r.unit_known or not r.unit:
    return None, "BOOK_UNIT_UNKNOWN"
  per = LOGIC.convert_rate(r.unit_rate, r.unit, item.unit)
  if per is None:
    return None, "UNIT_CANNOT_CONVERT"
  return {"unit": LOGIC.normalise_unit(item.unit), "rate": float(per), "mrs": code}, None

def build(rows: list, name: str, digest: str, chosen: dict | None = None) -> dict:
  codes = by_code(rows)
  priced, no_rate, reasons = {}, [], {}
  for item in CL.items():
    got, why = rate_for(item, codes, chosen)
    if got is None:
      no_rate.append(item.id)
      reasons[item.id] = why
    else:
      priced[item.id] = AN.Flow(got)
  return {"book": name, "source_sha256": digest, "book_rows": len(rows), "per_item_unit": priced, "no_rate": no_rate, "no_rate_reasons": reasons}

def with_code() -> list:
  return sorted(i.id for i in CL.items() if i.billing.MRS_PB)

def shares_doc() -> dict:
  return AN.read_yaml(SHARES) or {}

def share_lines(doc: dict, shares: dict) -> list:
  rows = shares.get("shares") or {}
  if not rows:
    return ["top-20 money shares: money_shares.yaml holds none; the QS gives them at sitting 1 (answers.tolerance_sheet import)"]
  out = [f"top-20 money shares from {shares.get('confirmed_by')}, {shares.get('confirmed_date')} ({shares.get('house')}):"]
  priced = 0.0
  for item, pct in sorted(rows.items(), key=lambda kv: (-kv[1], kv[0])):
    got = (doc["per_item_unit"] or {}).get(item)
    priced += pct if got else 0.0
    out.append(f"  {item}  {pct:g}%  " + (f"{got['rate']:,.2f} per {got['unit']} (MRS {got['mrs']})" if got else f"NO RATE ({doc['no_rate_reasons'].get(item, 'not in the catalogue')})"))
  total = sum(rows.values())
  out.append(f"  rated: {priced:g}% of the {total:g}% the QS puts in these items")
  return out

def lines_of(doc: dict, report: dict, shares: dict) -> list:
  coded = with_code()
  missing = [i for i in coded if i in doc["no_rate"]]
  out = [f"{doc['book']}: {doc['book_rows']} rows read; {len(doc['per_item_unit'])} of {len(CL.items())} items have a rate; {len(coded)} items carry an MRS code, {len(coded) - len(missing)} of them priced"]
  if report:
    out.append(f"  reader status {report.get('status')}; {(report.get('counts') or {}).get('flagged_for_review', 0)} row(s) flagged for review" + ("; check the reader's report before trusting this book" if report.get("status") == "FAIL" else ""))
  by_reason: dict = {}
  for i in doc["no_rate"]:
    by_reason.setdefault(doc["no_rate_reasons"][i], []).append(i)
  for why in REASONS:
    if by_reason.get(why):
      out.append(f"  {why}: {len(by_reason[why])} item(s)" + (f": {', '.join(by_reason[why])}" if why != "NO_MRS_CODE" else ""))
  out += ["  " + ln for ln in share_lines(doc, shares)]
  return out

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Fill rates.yaml from a Bahawalpur MRS rate book through the existing reader: one rate per item and unit, through the catalogue's MRS_PB codes. An item with no code or no usable rate keeps no rate and is listed, never guessed.")
  ap.add_argument("--book", help="the rate book PDF")
  ap.add_argument("--books-dir", help="a folder of rate books; with --match the newest PDF whose name has that word is used")
  ap.add_argument("--match")
  ap.add_argument("--case", help="a case folder name: its decisions.yaml choice answers say which rate-book item an item billed under several is priced under")
  ap.add_argument("--name", help="the book's name as it goes in the file (default: the file name)")
  ap.add_argument("--province", required=True)
  ap.add_argument("--city", required=True)
  ap.add_argument("--first-page", type=int, default=1)
  ap.add_argument("--last-page", type=int)
  ap.add_argument("--write", action="store_true")
  ap.add_argument("--out", default=RATES)
  a = ap.parse_args(argv)
  path = a.book or (newest_book(a.books_dir, a.match) if a.books_dir and a.match else None)
  if not path:
    print("give --book, or --books-dir with --match")
    return 2
  rows, digest, report = book_rows(path, a.first_page, a.last_page, a.province, a.city)
  chosen = CH.billing_items(QAN.split_case(CIO.load_decisions(os.path.join(CIO.HERE, a.case)))[1]) if a.case else None
  doc = build(rows, a.name or os.path.splitext(os.path.basename(path))[0], digest, chosen)
  for ln in lines_of(doc, report, shares_doc()):
    print(ln)
  for ln in CH.problems(None, set(by_code(rows))):
    print("  choice card: " + ln)
  if a.write:
    AN.write_yaml(a.out, doc)
    print(f"wrote {a.out}")
  else:
    print("nothing written; add --write")
  return 0

if __name__ == "__main__":
  sys.exit(main())
