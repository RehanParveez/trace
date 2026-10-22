from __future__ import annotations
from dataclasses import dataclass, field

MAX_PDF_PAGES = 2500

@dataclass
class Cell:
  y: float         
  x0: float
  x1: float
  text: str

@dataclass
class PageCells:
  number: int       
  width: float
  height: float
  cells: list = field(default_factory=list)

def page_cells(page, number: int) -> PageCells:
  width, height = page.get_size()
  tp = page.get_textpage()
  try:
    cells: list = []
    for i in range(tp.count_rects()):
      left, bottom, right, top = tp.get_rect(i)
      text = (tp.get_text_bounded(left, bottom, right, top) or "").replace("\r", "")
      for k, part in enumerate(p for p in text.split("\n") if p.strip()):
        cells.append(Cell(y=round(height - top + k * 9.0, 2), x0=round(left, 2), x1=round(right, 2), text=part.strip()))
        
  finally:
    tp.close()
  cells.sort(key=lambda c: (c.y, c.x0))
  return PageCells(number=number, width=float(width), height=float(height), cells=cells)

def read_pdf_cells(data: bytes, *, first_page: int = 1, last_page: int | None = None) -> tuple[list, int]:
  import pypdfium2 as pdfium
  try:
    pdf = pdfium.PdfDocument(data)
  except Exception as exc:
    raise ValueError("The PDF could not be opened.") from exc
  try:
    total = len(pdf)
    if total > MAX_PDF_PAGES:
      raise ValueError(f"The PDF has {total} pages; the limit is {MAX_PDF_PAGES}.")
  
    out = []
    for n in range(max(1, first_page), min(total, last_page or total) + 1):
      page = pdf[n - 1]
      try:
        out.append(page_cells(page, n))
      finally:
        page.close()
    return out, total
  finally:
    pdf.close()
