from __future__ import annotations
import pypdfium2 as pdfium
from app.modules.drawings_boq.takeoff.profile import pages as PG
from app.modules.drawings_boq.takeoff.profile import convention as CVN

def facts_of_pdf(path: str, shift: int = 0) -> list:
  doc = pdfium.PdfDocument(path)
  out = []
  
  try:
    for i in range(len(doc)):
      page = doc[i]
      try:
        out.append(PG.facts(page, i + 1 + shift))
      finally:
        page.close()
  finally:
    doc.close()
  return out

def profile_pdfs(paths: list, register: list | None = None, shift: int = 1000) -> dict:
  pages: list = []
  
  for n, path in enumerate(paths):
    pages.extend(facts_of_pdf(path, n * shift))
  return {**CVN.build(pages, register), "page_facts": pages}

def summary(profile: dict) -> dict:
  return {k: {"value": v["value"], "confidence": v["confidence"]} for k, v in profile["points"].items()}
