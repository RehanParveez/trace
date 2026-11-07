from __future__ import annotations
import math
import re
from app.engine.catalogue import model as CM
from app.modules.drawings_boq.boq_logic import normalise_unit
from app.modules.drawings_boq.takeoff.prep import texts as TX

EDGE_SLACK = 0.001
NUMBER_RX = re.compile(r"(?<![\w.])\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.])\d+(?:\.\d+)?")
NAMES = ("quote_printed", "number_printed", "unit_parses", "value_in_range", "box_on_page", "choice_offered")

def result(name: str, passed: bool, detail: str) -> dict:
  return {"name": name, "passed": bool(passed), "detail": detail}

def squash(text) -> str:
  return re.sub(r"\s+", " ", re.sub(r"[^\w\s./'\"-]", " ", str(text or ""), flags=re.U)).strip().lower()

def quote_printed(quote, region_text: str | None) -> dict:
  if region_text is None:
    return result("quote_printed", False, "the page has no readable text layer in this region, so the quote cannot be checked")
  q, body = squash(quote), squash(region_text)
  if not q:
    return result("quote_printed", False, "the quote is empty")
  if q in body:
    return result("quote_printed", True, "the quote is printed in the region")
  have = set(body.split())
  missing = [w for w in q.split() if w not in have]
  if not missing:
    return result("quote_printed", True, "every word of the quote is printed in the region, in another order")
  return result("quote_printed", False, "not printed in the region: " + " ".join(missing[:6]))

def printed_numbers(region_text: str | None) -> set:
  return {float(m.group(0).replace(",", "")) for m in NUMBER_RX.finditer(region_text or "")}

def number_printed(value, region_text: str | None) -> dict:
  if region_text is None:
    return result("number_printed", False, "the page has no readable text layer in this region, so the number cannot be checked")
  try:
    number = float(str(value).replace(",", ""))
  except (TypeError, ValueError):
    return result("number_printed", False, "the value is not a number")
  if number in printed_numbers(region_text):
    return result("number_printed", True, "the number is printed in the region")
  return result("number_printed", False, "the number is not printed in the region")

def unit_parses(text) -> dict:
  raw = str(text or "").strip()
  if not raw:
    return result("unit_parses", False, "no unit given")
  unit = normalise_unit(raw)
  if unit in CM.INPUT_UNITS:
    return result("unit_parses", True, f"unit {unit}")
  readings = TX.parse_dimension(raw)
  if readings:
    return result("unit_parses", True, f"dimension in {readings[0].unit}")
  return result("unit_parses", False, f"{raw!r} is not a unit the catalogue or the dimension reader knows")

def value_in_range(value, low, high) -> dict:
  try:
    number = float(value)
  except (TypeError, ValueError):
    return result("value_in_range", False, "the value is not a number")
  if low is None or high is None:
    return result("value_in_range", False, "no range was given to check against")
  if low <= number <= high:
    return result("value_in_range", True, f"{number:g} is inside {low:g} to {high:g}")
  return result("value_in_range", False, f"{number:g} is outside {low:g} to {high:g}")

def box_on_page(box, page_pt) -> dict:
  try:
    x0, y0, x1, y1 = (float(v) for v in box)
    width, height = (float(v) for v in page_pt)
  except (TypeError, ValueError):
    return result("box_on_page", False, "the box or the page size is not four and two numbers")
  if not all(math.isfinite(v) for v in (x0, y0, x1, y1, width, height)):
    return result("box_on_page", False, "the box is not finite")
  slack = EDGE_SLACK * max(width, height)
  if x1 <= x0 or y1 <= y0:
    return result("box_on_page", False, "the box has no area")
  if x0 < -slack or y0 < -slack or x1 > width + slack or y1 > height + slack:
    return result("box_on_page", False, "the box leaves the page")
  return result("box_on_page", True, "the box is on the page")

def choice_offered(value, offered) -> dict:
  if value is None:
    return result("choice_offered", True, "the model chose none of the offered items")
  if str(value) in {str(o) for o in offered}:
    return result("choice_offered", True, f"{value} is one of the {len(list(offered))} offered items")
  return result("choice_offered", False, f"{value} is not one of the offered items")

def passed(results: list) -> bool:
  return bool(results) and all(r["passed"] for r in results)
