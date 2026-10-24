from __future__ import annotations

OK, WARN, INFO = "OK", "WARN", "INFO"
LOOK, PARTIAL = "LOOK", "PARTIAL"

def _c(code: str, status: str, title: str, message: str, pages=(), count: int | None = None) -> dict:
  pages = sorted({int(p) for p in pages if p is not None})
  return {"code": code, "status": status, "title": title, "message": message, "pages": pages, "count": len(pages) if count is None and pages else (count or 0)}

def _plural(n: int, one: str, many: str) -> str:
  return one if n == 1 else many

def run(sheets: list, extractions: list, cands: list, reader: dict | None, code_version: int, notes: dict | None = None) -> dict:
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

  warns = sum(1 for c in out if c["status"] == WARN)
  infos = sum(1 for c in out if c["status"] == INFO)
  oks = sum(1 for c in out if c["status"] == OK)
  status = LOOK if warns else PARTIAL if infos else OK
  return {"status": status, "checks": out, "summary": {"warn": warns, "info": infos, "ok": oks, "sheets": n, "read": len(read)}}
