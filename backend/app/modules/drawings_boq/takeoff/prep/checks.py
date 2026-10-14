from __future__ import annotations

READ_OK = ("OCR", "OCR_SQUARE")

def inches(a, b) -> str:
  def one(v):
    return f"{v:g}\""
  return f"{one(a)}×{one(b)}"

def _check(code: str, severity: str, title: str, message: str, marks: list | None = None, pages: list | None = None) -> dict:
  return {"code": code, "severity": severity, "title": title, "message": message, "marks": sorted(set(marks or [])), "pages": sorted(set(pages or []))}

def column_checks(details: list, reader: str | None, plan_marks: set, mismatches: list) -> list[dict]:
  """details: the column details found [{mark, page_no, read, w_in, h_in}]; reader: OK / UNAVAILABLE / FAILED; plan_marks: column marks counted on
  the plans; mismatches: [{tag, drawn_in, detail_in}] where the plan square and the detail differ."""
  if not details:
    return []
  out = []
  marks = sorted({d["mark"] for d in details})
  unread = [d for d in details if d.get("read") not in READ_OK]
  if reader in ("UNAVAILABLE", "FAILED"):
    out.append(_check("DETAIL_READER_UNAVAILABLE", "warning", "Column detail sizes not read",
      f"{len(details)} column detail drawings were found ({', '.join(marks)}). Their sizes are drawn as lines, not text, and the character reader is "
      "not available on the server, so the plan squares were used. Install the reader (tesseract) or type the column sizes.",
      marks, [d.get("page_no") for d in details if d.get("page_no")]))
    
  elif unread:
    um = sorted({d["mark"] for d in unread})
    out.append(_check("DETAIL_SIZE_NOT_READ", "warning", "Some column detail sizes could not be read",
      f"The size beside the detail of {', '.join(um)} could not be read with enough agreement. The plan square is used for it. Check it against the detail.",
      um, [d.get("page_no") for d in unread if d.get("page_no")]))
  sizes: dict = {}
  for d in details:
    if d.get("read") in READ_OK and d.get("w_in") and d.get("h_in"):
      sizes.setdefault(d["mark"], set()).add((min(d["w_in"], d["h_in"]), max(d["w_in"], d["h_in"])))
  disagree = {m: sorted(v) for m, v in sizes.items() if len(v) > 1}
  detail_marks = {d["mark"] for d in details}
  missing = sorted(plan_marks - detail_marks) if plan_marks else []
  
  for m, v in sorted(disagree.items()):
    hint = ""
    if len(disagree) == 1 and len(missing) == 1:
      hint = f" No detail is labelled {missing[0]}, so one of these may be {missing[0]}."
    out.append(_check("DETAILS_DISAGREE", "warning", f"{m} is drawn with two different sizes",
      f"The details labelled {m} show {' and '.join(inches(*s) for s in v)}. No size was taken for {m} from them.{hint} Correct the mark on the drawing or confirm the size.",
      [m], [d.get("page_no") for d in details if d["mark"] == m and d.get("page_no")]))
    
  for mm in mismatches:
    out.append(_check("PLAN_VS_DETAIL", "info", f"{mm['tag']}: plan square differs from its detail",
      f"The plan shows {mm['tag']} as a {inches(*mm['drawn_in'])} square symbol; its detail is {inches(*mm['detail_in'])}. The detail size is used.", [mm["tag"]]))
  if missing and details:
    out.append(_check("PLAN_MARK_WITHOUT_DETAIL", "info", "Column marks with no detail",
      f"{', '.join(missing)} {'is' if len(missing) == 1 else 'are'} on the plans but no column detail carries {'that mark' if len(missing) == 1 else 'those marks'}. "
      "The size is the plan square (a symbol), so confirm it.", missing))
  off = sorted(detail_marks - plan_marks) if plan_marks else []
  
  if off:
    out.append(_check("DETAIL_MARK_NOT_ON_PLAN", "info", "Details of marks not on the plans",
      f"The column details {', '.join(off)} have no matching mark on the plans read so far. They may belong to a plan not read yet.", off))
  return out
