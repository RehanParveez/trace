from __future__ import annotations
import hashlib
import re
from app.modules.drawings_boq.pricing import mrs_cells, mrs_table

NORMS_MARK = "Dry Material Required"
RATIO_CELL = re.compile(r"(?<![\d:.])1\s*:\s*(\d+)(?!\d)(?!\s*:)")
NUMBER = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")
ROW_TOL = 3.0
LINE_CHARS = 160
ALSO = 5

def sha256_of(data: bytes) -> str:
  return hashlib.sha256(data).hexdigest()

def chapter_of(text: str) -> int | None:
  m = mrs_table.FOOTER.search(text) or mrs_table.CHAPTER_HEAD.search(text)
  return int(m.group(1)) if m else None

def _open(data: bytes):
  import pypdfium2 as pdfium
  try:
    return pdfium.PdfDocument(data)
  except Exception as exc:
    raise ValueError("The PDF could not be opened.") from exc

def scan(data: bytes, numbers: list | None = None) -> list:
  pdf = _open(data)
  try:
    total = len(pdf)
    want = range(1, total + 1) if numbers is None else sorted({n for n in numbers if 1 <= n <= total})
    out, carried = [], None
    for n in want:
      page = pdf[n - 1]
      try:
        tp = page.get_textpage()
        try:
          text = (tp.get_text_range() or "").replace("\r", "")
        finally:
          tp.close()
      finally:
        page.close()
      carried = chapter_of(text) or (carried if numbers is None else None)
      out.append({"n": n, "chapter": carried, "text": text})
    return out
  finally:
    pdf.close()

def page_count(data: bytes) -> int:
  pdf = _open(data)
  try:
    return len(pdf)
  finally:
    pdf.close()

def is_norms(text: str) -> bool:
  return NORMS_MARK.lower() in text.lower()

def locate(pages: list, find: list | None, chapter: int | None = None, norms_only: bool = False) -> dict | None:
  if not find:
    return None
  pats = [re.compile(p) for p in find]
  hits = []
  for pg in pages:
    if chapter is not None and pg["chapter"] != chapter:
      continue
    if norms_only and not is_norms(pg["text"]):
      continue
    if all(p.search(pg["text"]) for p in pats):
      hits.append(pg)
      
  if not hits:
    return None
  first = hits[0]
  best, best_n = "", -1
  for ln in first["text"].split("\n"):
    n = sum(1 for p in pats if p.search(ln))
    if n > best_n and ln.strip():
      best, best_n = ln.strip(), n
  return {"page": first["n"], "chapter": first["chapter"], "line": re.sub(r"\s+", " ", best)[:LINE_CHARS], "also": [h["n"] for h in hits[1:1 + ALSO]]}

def grid(pc, tol: float = ROW_TOL) -> list:
  rows: list = []
  for c in sorted(pc.cells, key=lambda c: (c.y, c.x0)):
    if rows and abs(c.y - rows[-1][0].y) <= tol:
      rows[-1].append(c)
    else:
      rows.append([c])
  return [sorted(r, key=lambda c: c.x0) for r in rows]

def _figures(texts: list) -> list:
  out = []
  for t in texts:
    out += [m.replace(",", "") for m in NUMBER.findall(t)]
  return out

def ratio_row(texts: list) -> tuple | None:
  for i, t in enumerate(texts):
    m = RATIO_CELL.search(t)
    if m:
      rest = [t[m.end():], *texts[i + 1:]]
      nums = _figures(rest)
      return (f"1:{m.group(1)}", nums) if nums else None
  return None

def read_mortar(cells: list) -> dict | None:
  item, header, rows, other = None, [], [], 0
  for pc in cells:
    started = False
    for row in grid(pc):
      texts = [c.text for c in row]
      if item is None:
        for t in texts:
          if t.startswith(NORMS_MARK):
            item = t
      got = ratio_row(texts)
      
      if got:
        started = True
        rows.append({"ratio": got[0], "values": got[1], "page": pc.number})
      elif started and any(RATIO_CELL.search(t) or re.search(r"\d\s*:\s*\d", t) for t in texts):
        other += 1
      elif not started and not rows:
        header.append(" | ".join(texts))
  if not rows:
    return None
  return {"item": item, "header": header[-6:], "rows": rows, "other": other}

def cells_of(data: bytes, numbers: list) -> list:
  pdf = _open(data)
  try:
    out = []
    for n in sorted({n for n in numbers if 1 <= n <= len(pdf)}):
      page = pdf[n - 1]
      try:
        out.append(mrs_cells.page_cells(page, n))
      finally:
        page.close()
    return out
  finally:
    pdf.close()

def table_rows(read: dict) -> list:
  return [{"ratio": r["ratio"], "values": list(r["values"])} for r in read["rows"]]

def norm_pages(pages: list) -> list:
  return [pg["n"] for pg in pages if is_norms(pg["text"])]

def from_book(data: bytes, entries: list) -> dict:
  pages = scan(data)
  norms = norm_pages(pages)
  out: dict = {"sha256": sha256_of(data), "page_count": len(pages), "norm_pages": norms, "entries": {}}
  mortar = None
  
  if norms:
    mortar = read_mortar(cells_of(data, norms))
  out["mortar"] = mortar
  by_n = {pg["n"]: pg for pg in pages}
  for e in entries:
    src = e.get("source") or {}
    if src.get("kind") != "STANDARD":
      continue
    found: dict | None = None
    if e.get("read") == "mortar_table":
      if mortar:
        first = mortar["rows"][0]["page"]
        found = {"page": first, "chapter": by_n[first]["chapter"], "line": mortar["item"] or "", "also": [], "table": table_rows(mortar), "header": mortar["header"]}
    else:
      found = locate(pages, src.get("find"), src.get("chapter"), src.get("on") == "norms")
      if found is None and src.get("find") and src.get("chapter") is not None:
        found = locate(pages, src.get("find"), None, src.get("on") == "norms")
        if found:
          found["chapter_differs"] = True
    out["entries"][e["id"]] = found
  return out
