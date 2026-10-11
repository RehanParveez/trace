import io
import pytest
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
pytest.importorskip("pypdf")
reportlab = pytest.importorskip("reportlab")
from app.modules.drawings_boq.pricing import mrs_extract as ex
from app.modules.drawings_boq.pricing import mrs_parse as mp

def _pdf(pages: list[list[str]]) -> bytes:
  buf = io.BytesIO()
  c = canvas.Canvas(buf, pagesize=A4)
  for lines in pages:
    y = 800
    for ln in lines:
      c.drawString(40, y, ln)
      y -= 16
    c.showPage()
  c.save()
  return buf.getvalue()

PAGES = [
  ["Chapter 2 TESTWORK", "1  Sample plain concrete work     cft     100.00", "2  Sample brick work     cft     200.00"],
  ["3  Sample plaster work     sft     30.50", "4  Sample paint work     sft     12.25"],
]

def test_extract_and_parse_roundtrip():
  out = ex.extract_pdf(_pdf(PAGES))
  assert out.page_count == 2 and not out.empty_text_pages
  rows, unparsed = mp.parse_pages(out.pages, mp.GENERIC)
  assert [r.item_no for r in rows] == ["1", "2", "3", "4"]
  assert [str(r.rate) for r in rows] == ["100.00", "200.00", "30.50", "12.25"]
  assert "100" in out.second_pass_tokens[1]

def test_blank_page_is_reported_not_guessed():
  out = ex.extract_pdf(_pdf([PAGES[0], []]))
  assert out.empty_text_pages == [2]

def test_garbage_is_an_error():
  with pytest.raises(Exception):
    ex.extract_pdf(b"not a pdf")