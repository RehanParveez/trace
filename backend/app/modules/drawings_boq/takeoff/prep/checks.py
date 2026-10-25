from __future__ import annotations

READ_OK = ("OCR", "OCR_SQUARE")

def inches(a, b) -> str:
  def one(v):
    return f"{v:g}\""
  return f"{one(a)}×{one(b)}"

def _check(code: str, severity: str, title: str, message: str, marks: list | None = None, pages: list | None = None) -> dict:
  return {"code": code, "severity": severity, "title": title, "message": message, "marks": sorted(set(marks or [])), "pages": sorted(set(pages or []))}

def _ft_in(mm: float) -> str:
  inches_total = int(round(mm / 25.4))
  return f"{inches_total // 12}'-{inches_total % 12}\""

def storey_checks(storeys: dict | None, heights: dict, names: dict) -> list[dict]:
  """storeys: the storey heights read from the building sections; heights: floor key -> {clear_mm, ...} that could be matched to the floors;
  names: floor key -> floor name."""
  if not storeys or not storeys.get("clusters"):
    return []
  page = [storeys["page_no"]] if storeys.get("page_no") else []
  clusters = storeys["clusters"]
  
  if heights:
    listed = ", ".join(f"{names.get(k, k)} {_ft_in(h['clear_mm'])}" for k, h in heights.items())
    slabs = {round(c["implied_slab_mm"]) for c in clusters if c.get("implied_slab_mm")}
    slab = f" The level marks less these heights leave a slab of {_ft_in(slabs.pop())}." if len(slabs) == 1 else ""
    notes = storeys.get("basis") == "PLAN_NOTES"
    return [_check("STOREY_HEIGHTS_FROM_SECTION", "info", "Storey heights read from the room notes of the plans" if notes else "Storey heights read from the building sections",
      f"{'The room notes of the plans (ceiling height and the level of the floor above the road level) give' if notes else 'The sections print'} the clear height of each storey: {listed}. They are used as the column and wall height of those floors.{slab}", [], page)]
  listed = ", ".join(_ft_in(c["clear_mm"]) for c in clusters)
  return [_check("STOREY_HEIGHTS_NOT_MATCHED", "info", "Storey heights on the sections not matched to floors",
    f"{'The room notes of the plans give' if storeys.get('basis') == 'PLAN_NOTES' else 'The sections print'} {len(clusters)} storey heights ({listed}, lowest first)but they could not be matched with certainty to the floors of this drawing, "
    "so none was used. Type the heights on the walls and columns.", [], page)]
  
def column_checks(details: list, reader: str | None, plan_marks: set, mismatches: list) -> list[dict]:
  """details: the column details found [{mark, page_no, read, w_in, h_in}]; reader: OK / UNAVAILABLE / FAILED; plan_marks: column marks counted on
  the plans; mismatches: [{tag, drawn_in, detail_in}] where the plan square and the detail differ."""
  if not details:
    return []
  out = []
  
  marks = sorted({d["mark"] for d in details})
  unread = [d for d in details if d.get("read") not in READ_OK]
  timed = [d for d in unread if d.get("read") == "TIMEOUT"]
  unread = [d for d in unread if d.get("read") != "TIMEOUT"]
  if reader in ("UNAVAILABLE", "FAILED"):
    out.append(_check("DETAIL_READER_UNAVAILABLE", "warning", "Column detail sizes not read",
      f"{len(details)} column detail drawings were found ({', '.join(marks)}). Their sizes are drawn as lines, not text, and the character reader is "
      "not available on the server, so the plan squares were used. Install the reader (tesseract) or type the column sizes.",
      marks, [d.get("page_no") for d in details if d.get("page_no")]))
    
  elif timed:
    tm = sorted({d["mark"] for d in timed})
    out.append(_check("DETAIL_READER_TIMEOUT", "warning", "Column detail reading ran out of time",
      f"Reading the sizes beside the details of {', '.join(tm)} was cut off by the time limit; the character reader is slow on this server. The plan square is "
      "used for them. Raise the limit with the TRACE_OCR_BUDGET_S setting (seconds) and have the sheet read again, or type the column sizes.",
      tm, [d.get("page_no") for d in timed if d.get("page_no")]))
  if unread and reader not in ("UNAVAILABLE", "FAILED"):
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

def slab_checks(values: list, plan_notes: list) -> list[dict]:
  """values: the slab thicknesses printed for slabs in general [{mm, count, pages}] (facts.slab_values); plan_notes: [{mm, pages, floors}] the thickness
  each structural plan states in its own slab note. Slabs are measured with the plan note; another thickness printed elsewhere is a dispute to settle."""
  if len(values) < 2:
    return []
  def inch(mm):
    return f"{mm / 25.4:g}\""
  def where(v):
    pages = ", ".join(str(p) for p in v["pages"])
    return f"{inch(v['mm'])} on sheet{'s' if len(v['pages']) > 1 else ''} {pages}" if pages else inch(v["mm"])
  used = sorted({n["mm"] for n in plan_notes})
  listed = " and ".join(where(v) for v in values)
  
  if used:
    us = " and ".join(inch(m) for m in used)
    tail = f" The slabs found on the structural plans are measured with the plan note ({us}). If the other thickness is right, type it when you accept the slab; a difference of 1 inch on a 5 inch slab is 20% of the slab concrete."
  else:
    tail = " No structural plan states a slab thickness, so none was chosen. Type it when you accept the slab."
  pages = sorted({p for v in values for p in v["pages"]})
  return [_check("SLAB_THICKNESS_DISAGREES", "warning", "Slab thickness is printed two ways", f"The drawing prints slab thickness as {listed}.{tail}", [], pages)]

def lintel_checks(lintels: list, tie_band: dict | None) -> list[dict]:
  """lintels: the rows of the lintel table printed on the drawing; tie_band: {"text", "pages"} when the drawing also prints a tie band at lintel level.
  Both are real members. A band that runs over an opening is the lintel there, so the same concrete must not be counted twice."""
  if not lintels or not tie_band:
    return []

  pages = sorted(set(tie_band.get("pages") or []) | {p for r in lintels for p in (r.get("pages") or [])})
  return [_check("LINTEL_AND_TIE_BAND_PRINTED", "warning", "Lintels and a tie band are both printed",
    f"The drawing prints a lintel table and also a tie band at lintel level ({tie_band['text'].lower()}). A band that runs over an opening takes the place of a separate lintel there. "
    "The tie band is listed as a beam over the brick walls of each plan, at lintel level, and the lintels are listed too, each marked as covered by the band. "
    "Switch on 'tie band replaces lintel' in the site assumptions to leave the covered lintels out once the band is measured; until then both are counted.", [], pages)]
