from __future__ import annotations
from app.modules.drawings_boq.takeoff.prep.checks import _check

READ_FROM_TEXT = ("TEXT",)
READ_OK = ("TEXT", "TEXT+OCR", "OCR")
PICTURE_ONLY_VOTES = 2

def rows(sheets: list) -> tuple:
  """(beam rows, tank rows) from the details read on each sheet (prep meta). sheets: [{"page_no", "beam_details", "tank_details"}]."""
  from app.engine.measure.steel_grammar import steel_text
  beams, tanks = [], []
  for sh in sheets:
    for d in sh.get("beam_details") or []:
      steel = d.get("steel")
      try:
        text = steel_text(steel) if steel else None
      except Exception:
        text = None
      beams.append({"mark": d.get("mark"), "kind": d.get("kind"), "page_no": sh.get("page_no"), "read": d.get("read") or "NONE", "depth_in": d.get("depth_in"),
        "steel_text": text, "from_text": bool(d.get("from_text"))})
    for d in sh.get("tank_details") or []:
      tanks.append({"kind": d.get("kind"), "view": d.get("view"), "caption": d.get("caption"), "page_no": sh.get("page_no"), "read": d.get("read") or "NONE",
        "sizes": [{"text": x.get("text"), "source": x.get("source") or "PICTURE", "votes": x.get("votes")} for x in d.get("lengths") or []],
        "bar_notes": list(d.get("bar_notes") or []), "from_text": bool(d.get("from_text"))})
  return beams, tanks

def _why(status: dict) -> str:
  if not status.get("installed"):
    return "the character reader (tesseract) is not installed on the server"
  return "the Python packages the character reader needs (Pillow, numpy) are not installed on the server"

def checks(beams: list, tanks: list, status: dict) -> list:
  out = []
  if not beams and not tanks:
    return out
  names = lambda rs, key: sorted({str(r[key]) for r in rs if r.get(key)})
  pages = lambda rs: [r.get("page_no") for r in rs if r.get("page_no")]
  unread_b = [r for r in beams if r["read"] not in READ_OK]
  unread_t = [r for r in tanks if r["read"] not in READ_OK]
  timed_b = [r for r in unread_b if r["read"] == "TIMEOUT"]
  timed_t = [r for r in unread_t if r["read"] == "TIMEOUT"]
  if not status.get("usable"):
    need = [r for r in unread_b + unread_t if r["read"] != "TIMEOUT"]
    if need:
      what = []
      
      if unread_b:
        what.append(f"the depth and bars of beam sections {', '.join(names(unread_b, 'mark'))}")
      if unread_t:
        what.append("the sizes of the water tank drawings")
      out.append(_check("PICTURE_READER_UNAVAILABLE", "warning", "Beam and tank pictures not read",
        f"{_why(status)}, so {' and '.join(what)} could not be read from the pictures. Whatever the PDF carries as text was read (none of it covers these). "
        "Type the beam depths and tank heights when you accept the items, or have the reader installed on the server (the Docker image installs it with "
        "apt-get install tesseract-ocr) and prepare the sheet again.", names(unread_b, "mark"), pages(need)))
  else:
    if timed_b or timed_t:
      out.append(_check("PICTURE_READ_TIMEOUT", "warning", "Reading the beam and tank pictures ran out of time",
        f"The time limit was reached before {', '.join(names(timed_b, 'mark') + (['the tank drawings'] if timed_t else []))} could be read. Raise the limit with the "
        "TRACE_BEAM_OCR_BUDGET_S setting (seconds) and prepare the sheet again; a picture already read is kept, so the second run is quicker.",
        names(timed_b, "mark"), pages(timed_b + timed_t)))
    lost_b = [r for r in unread_b if r["read"] != "TIMEOUT" and not r.get("depth_in")]
    if lost_b:
      out.append(_check("BEAM_DEPTH_NOT_READ", "warning", "Some beam section depths could not be read",
        f"No depth was read for {', '.join(names(lost_b, 'mark'))}, from the text or from the picture. Type it when you accept the beam.", names(lost_b, "mark"), pages(lost_b)))
  weak = [(r, x) for r in tanks for x in r["sizes"] if x["source"] != "TEXT" and (x.get("votes") or 0) <= PICTURE_ONLY_VOTES]
  
  if weak:
    sizes = ", ".join(sorted({x["text"] for _, x in weak if x.get("text")}))
    out.append(_check("TANK_SIZE_PICTURE_ONLY", "info", "Tank sizes read only from the picture",
      f"{sizes} were read from the picture by only two readings and are not written as text in the PDF. A reading like this can be a misreading; check it on the drawing "
      "before using it.", [], pages([r for r, _ in weak])))
  text_b = [r for r in beams if r["read"] in READ_FROM_TEXT or r["from_text"]]
  text_t = [r for r in tanks if r["from_text"]]
  
  if text_b or text_t:
    parts = []
    if text_b:
      parts.append(f"{len(text_b)} beam section{'s' if len(text_b) != 1 else ''} ({', '.join(names(text_b, 'mark'))})")
    if text_t:
      parts.append(f"{len(text_t)} tank drawing{'s' if len(text_t) != 1 else ''}")
    out.append(_check("PICTURE_VALUES_FROM_TEXT", "info", "Some values read from the PDF's own text",
      f"{' and '.join(parts)} carr{'ies' if len(text_b) + len(text_t) == 1 else 'y'} bars or sizes as text in the PDF. Those were read exactly, without the picture reader.",
      names(text_b, "mark"), pages(text_b + text_t)))
  return out
