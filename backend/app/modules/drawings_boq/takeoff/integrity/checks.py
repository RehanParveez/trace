from __future__ import annotations
from app.modules.drawings_boq.takeoff.integrity import sheet_list as SL

OK, WARN, INFO = "OK", "WARN", "INFO"
LOOK, PARTIAL = "LOOK", "PARTIAL"

def _c(code: str, status: str, title: str, message: str, pages=(), count: int | None = None) -> dict:
  pages = sorted({int(p) for p in pages if p is not None})
  return {"code": code, "status": status, "title": title, "message": message, "pages": pages, "count": len(pages) if count is None and pages else (count or 0)}

def _plural(n: int, one: str, many: str) -> str:
  return one if n == 1 else many

def _nos(items: list, limit: int = 6) -> str:
  shown = ", ".join(items[:limit])
  return shown + (f" and {len(items) - limit} more" if len(items) > limit else "")

def _sheet_list_checks(sheets: list) -> list:
  ready = [s for s in sheets if s.get("prep_status") == "READY"]
  numbered = [{"page_no": s["page_no"], "sheet_no": s.get("sheet_no"), "title": s.get("sheet_title")} for s in ready]
  lists = [{"page_no": s["page_no"], "entries": (s.get("drawing_list") or {}).get("entries") or []} for s in ready if s.get("drawing_list")]
  from_picture = any((s.get("drawing_list") or {}).get("basis") != "TEXT" for s in ready if s.get("drawing_list"))
  read = sum(1 for n in numbered if n["sheet_no"])
  if not read and not lists:
    return []
  rep = SL.check(numbered, lists)
  out: list = []

  if rep["repeated"]:
    pages = [p for r in rep["repeated"] for p in r["pages"]]
    shown = "; ".join(f"{r['sheet_no']} on pages {', '.join(map(str, r['pages']))}" for r in rep["repeated"][:4])
    listed_twice = {m["sheet_no"] for m in rep["more_than_listed"]}
    sev = WARN if (not lists or any(r["sheet_no"] in listed_twice for r in rep["repeated"]) or not rep["listed"]) else INFO
    out.append(_c("SHEET_NUMBERS_UNIQUE", sev, "Every sheet has its own drawing number", f"The same drawing number is printed on more than one sheet: {shown}. " + ("The list of drawings gives fewer sheets than this." if rep["more_than_listed"] else "Check that the number was read correctly and that no sheet is repeated."), pages))
  elif read:
    out.append(_c("SHEET_NUMBERS_UNIQUE", OK, "Every sheet has its own drawing number", f"{read} {_plural(read, 'sheet carries', 'sheets carry')} a drawing number and no number is printed twice.", count=read))
  if not lists:
    out.append(_c("SHEET_LIST", INFO, "Sheets agree with the list of drawings", f"Drawing numbers were read from {read} of {len(ready)} sheets. No list of drawings was found among the sheets, so they could not be checked against one."))
    return out
  parts = [f"The list of drawings (page {', '.join(map(str, rep['list_pages']))}) names {rep['listed']} {_plural(rep['listed'], 'drawing', 'drawings')}; {rep['matched']} {_plural(rep['matched'], 'is', 'are')} on a sheet."]
  pages: list = []
  status = OK

  if rep["missing"]:
    status = WARN
    parts.append(f"No sheet carries {_plural(len(rep['missing']), 'this listed number', 'these listed numbers')}: {_nos([m['no'] for m in rep['missing']])}." + (" The list was read from a picture, so a listed number may be misread." if from_picture else ""))
  if rep["extra"]:
    status = WARN
    pages += [e["page_no"] for e in rep["extra"]]
    parts.append(f"{len(rep['extra'])} {_plural(len(rep['extra']), 'sheet carries a number', 'sheets carry numbers')} that {_plural(len(rep['extra']), 'is', 'are')} not on the list: {_nos([e['sheet_no'] + ' (page ' + str(e['page_no']) + ')' for e in rep['extra']])}. The number may be misread.")
  if rep["more_than_listed"]:
    status = WARN
    for m in rep["more_than_listed"]:
      pages += m["pages"]
    parts.append("More sheets than the list gives: " + _nos([f"{m['sheet_no']} ({len(m['pages'])} sheets, {m['listed_sheets']} listed)" for m in rep["more_than_listed"]]) + ".")
  if rep["fuzzy"]:
    if status == OK:
      status = INFO
    pages += [f["page_no"] for f in rep["fuzzy"]]
    parts.append(f"{len(rep['fuzzy'])} {_plural(len(rep['fuzzy']), 'number was', 'numbers were')} taken to be the listed number: each differs from it by one character that a reader mixes up. " + _nos([f"{f['read']} as {f['listed']} (page {f['page_no']})" for f in rep["fuzzy"]]) + ".")
  if rep["title_differs"]:
    if status == OK:
      status = INFO
    pages += [d["page_no"] for d in rep["title_differs"]]
    parts.append(f"The title on {len(rep['title_differs'])} {_plural(len(rep['title_differs']), 'sheet differs', 'sheets differ')} from the listed title: " + _nos([f"{d['sheet_no']} (page {d['page_no']})" for d in rep["title_differs"]]) + ".")
  unread = [p for p in rep["unread_pages"]]
  
  if unread:
    parts.append(f"No drawing number was read on {len(unread)} {_plural(len(unread), 'sheet', 'sheets')} ({_plural(len(unread), 'page', 'pages')} {_nos([str(p) for p in unread], 10)}). Covers and dividers have none; on a drawing, the number may not have been legible.")
  if status == OK:
    parts.append("Every listed drawing is on a sheet and every numbered sheet is on the list.")
  out.append(_c("SHEET_LIST", status, "Sheets agree with the list of drawings", " ".join(parts), pages, count=rep["matched"] if not pages else None))
  return out

def run(sheets: list, extractions: list, cands: list, reader: dict | None, code_version: int, notes: dict | None = None, code_scan: dict | None = None) -> dict:
  out: list = []
  
  n = len(sheets)
  failed = [s["page_no"] for s in sheets if s.get("prep_status") == "FAILED"]
  pending = [s["page_no"] for s in sheets if s.get("prep_status") == "PENDING"]
  if failed or pending:
    bits = []
    if failed:
      bits.append(f"{len(failed)} could not be prepared (page {', '.join(map(str, failed))})")
    if pending:
      bits.append(f"{len(pending)} {_plural(len(pending), 'is', 'are')} not prepared yet (page {', '.join(map(str, pending))})")
    out.append(_c("SHEETS_PREPARED", WARN, "Sheets prepared", "Of " + str(n) + f" {_plural(n, 'sheet', 'sheets')}, " + " and ".join(bits) + f". Nothing is read from {_plural(len(failed) + len(pending), 'it', 'them')}.", failed + pending))
  else:
    out.append(_c("SHEETS_PREPARED", OK, "Sheets prepared", f"All {n} {_plural(n, 'sheet is', 'sheets are')} prepared.", count=n))

  ready = [s["page_no"] for s in sheets if s.get("prep_status") == "READY"]
  read = {e["page_no"] for e in extractions}
  unread = [p for p in ready if p not in read]

  if unread:
    out.append(_c("SHEETS_READ", INFO, "Sheets read for items", f"{len(unread)} prepared {_plural(len(unread), 'sheet has', 'sheets have')} not been read for items yet.", unread))
  elif ready:
    out.append(_c("SHEETS_READ", OK, "Sheets read for items", f"All {len(ready)} prepared {_plural(len(ready), 'sheet has', 'sheets have')} been read.", count=len(ready)))
  stale = [e["page_no"] for e in extractions if int(e.get("extract_version") or 0) != int(code_version)]
  if stale:
    out.append(_c("READS_CURRENT", WARN, "Readings are current", f"{len(stale)} {_plural(len(stale), 'sheet was', 'sheets were')} read with an older version of the reader (now version {code_version}). Read again to get today's readings.", stale))
  elif extractions:
    out.append(_c("READS_CURRENT", OK, "Readings are current", f"Every sheet was read with the current version of the reader (version {code_version}).", count=len(extractions)))
  broken = [e["page_no"] for e in extractions if int(e.get("stage_failures") or 0) > 0]
  if broken:
    out.append(_c("NO_STAGE_FAILED", WARN, "Every reading step ran", f"On {len(broken)} {_plural(len(broken), 'sheet', 'sheets')} one or more reading steps failed and were skipped (the sheet carries a STAGE_FAILED note), so the items of those steps are missing. Read again after the fault is fixed.", broken))
  elif extractions:
    out.append(_c("NO_STAGE_FAILED", OK, "Every reading step ran", "No reading step failed on any sheet read.", count=len(extractions)))
  late = [e["page_no"] for e in extractions if e.get("decisions_stale")]
  if late:
    out.append(_c("DECISIONS_APPLIED", WARN, "Your choices are applied", f"{len(late)} {_plural(len(late), 'sheet was', 'sheets were')} read before a choice made for this drawing (see Decisions). Read again to apply it.", late))
  noscale = [e["page_no"] for e in extractions if e.get("mm_per_pt") in (None, 0)]
  unverified = [e["page_no"] for e in extractions if e.get("mm_per_pt") not in (None, 0) and e.get("scale_unverified")]
  if noscale:
    out.append(_c("SCALE_KNOWN", WARN, "Scale known", f"{len(noscale)} {_plural(len(noscale), 'sheet was', 'sheets were')} read without a usable scale, so no length or area is measured on {_plural(len(noscale), 'it', 'them')}.", noscale))
  if unverified:
    out.append(_c("SCALE_CONFIRMED", WARN, "Scale confirmed", f"The scale of {len(unverified)} {_plural(len(unverified), 'sheet is', 'sheets are')} taken from its title block and not confirmed by a measured dimension.", unverified))
  if extractions and not noscale and not unverified:
    out.append(_c("SCALE_KNOWN", OK, "Scale known", "Every sheet read has a usable scale.", count=len(extractions)))
  nofacts = [s["page_no"] for s in sheets if s.get("prep_status") == "READY" and not s.get("has_facts")]
  if nofacts:
    out.append(_c("NOTES_READ", INFO, "Notes read", f"The notes of {len(nofacts)} prepared {_plural(len(nofacts), 'sheet were', 'sheets were')} not read (prepared before the notes reader existed). Prepare {_plural(len(nofacts), 'it', 'them')} again.".replace("1 prepared sheet were", "1 prepared sheet was"), nofacts))
  scans = [s["page_no"] for s in sheets if s.get("text_source") == "OCR"]
  if scans:
    out.append(_c("TEXT_FROM_SCAN", INFO, "Text read from the PDF", f"{len(scans)} {_plural(len(scans), 'sheet has', 'sheets have')} no text of its own and {_plural(len(scans), 'was', 'were')} read from the picture, so a figure may be misread.", scans))
  if reader is not None and not reader.get("usable"):
    out.append(_c("CHARACTER_READER", INFO, "Character reader", "The character reader is not available on the server, so the sizes and bars written beside column and beam details can be read only from sheets that carry text.", count=1))
  accepted = [c for c in cands if c.get("decision") == "ACCEPTED"]
  lost = [c for c in accepted if not c.get("linked")]
  if lost:
    out.append(_c("ACCEPTED_LINKED", WARN, "Accepted items kept", f"{len(lost)} accepted {_plural(len(lost), 'item has', 'items have')} lost {_plural(len(lost), 'its', 'their')} measurement (it was deleted). {_plural(len(lost), 'It is', 'They are')} counted as accepted but {_plural(len(lost), 'gives', 'give')} no quantity.", [c.get("page_no") for c in lost], count=len(lost)))
  elif accepted:
    out.append(_c("ACCEPTED_LINKED", OK, "Accepted items kept", f"All {len(accepted)} accepted {_plural(len(accepted), 'item still has', 'items still have')} {_plural(len(accepted), 'its', 'their')} measurement.", count=len(accepted)))
  invalid = [c for c in cands if c.get("status") == "INVALID" and c.get("decision") != "REJECTED"]
  if invalid:
    out.append(_c("ITEMS_MEASURABLE", INFO, "Items measurable", f"{len(invalid)} found {_plural(len(invalid), 'item is', 'items are')} marked invalid ({_plural(len(invalid), 'it', 'they')} could not be measured) and {_plural(len(invalid), 'is', 'are')} still waiting for a decision.", [c.get("page_no") for c in invalid], count=len(invalid)))
  if notes and notes.get("notes"):
    look = int(notes.get("look") or 0)
    if look:
      out.append(_c("NOTES_AGREE", WARN, "Printed notes agree with the drawing", f"{look} {_plural(look, 'place is', 'places are')} where a printed note and the drawing disagree, or where no item is made from a note. See 'What the printed notes did'.", count=look))
    else:
      out.append(_c("NOTES_AGREE", OK, "Printed notes agree with the drawing", f"All {notes['notes']} printed notes are used, compared or listed without a disagreement.", count=int(notes["notes"])))

  typed = [s for s in sheets if s.get("pdf_type")]
  if typed:
    outlined = [s for s in typed if (s["pdf_type"] or {}).get("type") == "VECTOR_OUTLINED"]
    lost = [s["page_no"] for s in outlined if not (s["pdf_type"] or {}).get("text_recovered")]
    seen = [s["page_no"] for s in outlined if (s["pdf_type"] or {}).get("text_recovered")]
    bare = [s["page_no"] for s in typed if (s["pdf_type"] or {}).get("type") == "VECTOR_NOLETTER"]
    if lost:
      out.append(_c("PDF_TYPE_ROUTED", WARN, "Lettering of every sheet is readable", f"The lettering of {len(lost)} {_plural(len(lost), 'sheet is', 'sheets are')} drawn as outlines and could not be read from the picture, so the scale, marks and sizes printed on {_plural(len(lost), 'it', 'them')} are missing.", lost))
    elif seen:
      out.append(_c("PDF_TYPE_ROUTED", INFO, "Lettering of every sheet is readable", f"The lettering of {len(seen)} {_plural(len(seen), 'sheet is', 'sheets are')} drawn as outlines. It was read from the picture, so a mark or a figure may be misread.", seen))
    elif not bare:
      out.append(_c("PDF_TYPE_ROUTED", OK, "Lettering of every sheet is readable", "Every prepared sheet carries its lettering as text or was read from its picture.", count=len(typed)))
    if bare:
      out.append(_c("PDF_NO_LETTERING", WARN, "Lettering of every sheet is readable", f"{len(bare)} {_plural(len(bare), 'sheet has', 'sheets have')} a drawing but no readable lettering (the text was turned into line strokes), so the title, scale, marks and sizes printed on {_plural(len(bare), 'it', 'them')} are missing.", bare))
  if code_scan is not None:
    bad = int(code_scan.get("unresolved") or 0)
    if bad:
      shown = "; ".join(f"{x['file'].rsplit('/', 1)[-1]} line {x['line']}: {x['alias']}.{x['name']}" for x in (code_scan.get("listed") or [])[:5])
      out.append(_c("CALLS_RESOLVE", WARN, "Every call in the reader resolves", f"{bad} {_plural(bad, 'call names', 'calls name')} a function or constant that its module does not define, so {_plural(bad, 'it fails', 'they fail')} when the step runs and the step is skipped ({shown}).", count=bad))
    else:
      out.append(_c("CALLS_RESOLVE", OK, "Every call in the reader resolves", f"Every call to another module in the {code_scan.get('files', 0)} files of the reader names something that module defines.", count=int(code_scan.get("files") or 0)))

  out.extend(_sheet_list_checks(sheets))

  warns = sum(1 for c in out if c["status"] == WARN)
  infos = sum(1 for c in out if c["status"] == INFO)
  oks = sum(1 for c in out if c["status"] == OK)
  status = LOOK if warns else PARTIAL if infos else OK
  return {"status": status, "checks": out, "summary": {"warn": warns, "info": infos, "ok": oks, "sheets": n, "read": len(read)}}
