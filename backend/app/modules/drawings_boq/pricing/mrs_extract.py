from __future__ import annotations
from dataclasses import dataclass, field
import io
from app.modules.drawings_boq.pricing import mrs_parse as mp

MAX_PDF_PAGES = 2500

@dataclass
class Extracted:
  pages: list[list[str]]
  second_pass_tokens: dict[int, set[str]] = field(default_factory=dict)
  page_count: int = 0
  empty_text_pages: list[int] = field(default_factory=list)
  failed_pages: list[dict] = field(default_factory=list)

def extract_pdf(data: bytes, *, first_page: int = 1, last_page: int | None = None) -> Extracted:
  from pypdf import PdfReader
  reader = PdfReader(io.BytesIO(data))
  
  if reader.is_encrypted:
    try:
      if not reader.decrypt(""):
        raise ValueError("The PDF is password protected.")
    except Exception as exc:  
      raise ValueError("The PDF is password protected.") from exc
  
  total = len(reader.pages)
  if total > MAX_PDF_PAGES:
    raise ValueError(f"The PDF has {total} pages; the limit is {MAX_PDF_PAGES}.")
  stop = min(total, last_page or total)
  out = Extracted(pages=[], page_count=total)
  for n in range(max(1, first_page), stop + 1):
    page = reader.pages[n - 1]
    try:
      layout = page.extract_text(extraction_mode="layout") or ""
      plain = page.extract_text() or ""
      
    except Exception as exc:  
      out.failed_pages.append({"page": n, "error": str(exc)[:160]})
      layout = plain = ""
    lines = [ln.rstrip() for ln in layout.splitlines() if ln.strip()]
    
    if not lines:
      out.empty_text_pages.append(n)
    out.pages.append(lines)
    out.second_pass_tokens[n] = mp.number_tokens(plain.splitlines())
  return out

def extract_csv(data: bytes) -> Extracted:
  return Extracted(pages=[], page_count=0)
