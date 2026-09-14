from __future__ import annotations
from pypdf import PdfReader
from decimal import Decimal, InvalidOperation
from io import BytesIO

MAX_EXTRACTED_TEXT_CHARS = 12_000

def extract_pdf_text(contents: bytes) -> str:
  """
  Pulls whatever machine-readable text is embedded in the PDF -- the
  normal case for schedules/tables exported from CAD/BIM tools, since
  those are almost always drawn as live text/table annotations rather
  than rasterized images. A scanned/rasterized PDF will yield little
  or no text here -- that's an honest signal there's nothing to
  extract, not a bug to work around with OCR (out of scope for now).
  """
  reader = PdfReader(BytesIO(contents))
  pages_text = []
  for page in reader.pages:
    try:
      pages_text.append(page.extract_text() or "")
    except Exception:
      continue
  full_text = "\n".join(pages_text).strip()
  return full_text[:MAX_EXTRACTED_TEXT_CHARS]

def build_schedule_extraction_prompt(drawing_text: str) -> str:
  return (
    "You are reading raw text extracted from a construction drawing PDF "
    "(architectural, structural or MEP). The text may include a title "
    "block, general notes, and one or more SCHEDULE TABLES (for example: "
    "door schedule, window schedule, finishes schedule, bar bending "
    "schedule, sanitary fixture schedule).\n\n"
    "Your only job is to find rows that belong to an explicit schedule "
    "table and report the quantity exactly as written. Do NOT estimate, "
    "infer or calculate any quantity that is not literally stated as a "
    "number in the text (for example, never guess a wall area or length "
    "from room dimensions -- only report numbers that already appear "
    "as a stated quantity/count/length in a schedule row).\n\n"
    "If you cannot find any schedule table in the text, return an empty "
    "items array -- do not invent rows.\n\n"
    "Respond with strict JSON only, no markdown, in this exact shape:\n"
    '{"items": [{"description": "...", "unit": "...", "quantity": <number>, '
    '"category": "..." or null, "confidence": "high" | "medium" | "low"}]}\n\n'
    "Extracted drawing text:\n"
    f"{drawing_text}"
  )

def parse_schedule_extraction_response(raw_output: dict | None) -> list[dict]:
  if not raw_output:
    return []

  raw_items = raw_output.get("items")
  if not isinstance(raw_items, list):
    return []

  parsed: list[dict] = []
  for row in raw_items:
    if not isinstance(row, dict):
      continue

    description = str(row.get("description") or "").strip()
    unit = str(row.get("unit") or "").strip()
    if not description or not unit:
      continue
    try:
      quantity = Decimal(str(row.get("quantity")))
    except (InvalidOperation, TypeError, ValueError):
      continue
  
    if quantity <= 0:
      continue
    category = row.get("category")
    category = str(category).strip() if category else None

    parsed.append(
      {
        "description": description,
        "unit": unit,
        "quantity": quantity,
        "category": category,
        "confidence": row.get("confidence"),
      }
    )

  return parsed