from __future__ import annotations
import math
import re
from app.engine.catalogue import model as CM
from app.modules.drawings_boq.boq_logic import normalise_unit
from app.modules.drawings_boq.takeoff.prep import texts as TX
from app.modules.drawings_boq.takeoff import scale as SC

EDGE_SLACK = 0.001
NUMBER_RX = re.compile(r"(?<![\w.])\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.])\d+(?:\.\d+)?")
GLYPH_FRACTION = {"\u00bd": 0.5, "\u00bc": 0.25, "\u00be": 0.75, "\u215b": 0.125, "\u215c": 0.375, "\u215d": 0.625, "\u215e": 0.875}
FRACTION_RX = re.compile(r"(?<![\w.])(?:(?P<w>\d{1,3})\s*)?(?:(?P<n>\d{1,2})\s*/\s*(?P<d>\d{1,2})|(?P<g>[\u00bd\u00bc\u00be\u215b\u215c\u215d\u215e]))(?![\w.])")
OCR_MIN_CONF = 60.0
CONFUSED = str.maketrans({"O": "0", "I": "1", "S": "5"})
GLYPH_SLACK_SHARE = 0.2
GLYPH_SLACK_MIN = 2
WORD_GAP_TIMES = 2.2
MIN_GAPS_FOR_WORDS = 3
BOX_PAD_SHARE = 0.25
TEXT_LAYER, OCR_AND_GLYPHS = "TEXT_LAYER", "OCR_AND_GLYPHS"
SUPPORTS = (TEXT_LAYER, OCR_AND_GLYPHS)
NAMES = ("quote_supported", "ocr_agrees", "glyphs_match", "quote_printed", "number_printed", "unit_parses", "value_in_range", "box_on_page", "choice_offered", "scale_parses", "value_in_quote", "fields_given", "cells_in_quote", "mark_in_vocab", "floor_known", "size_parses", "size_in_range", "meaning_given", "symbol_present", "meaning_not_contradicted")

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
  text = region_text or ""
  found = {float(m.group(0).replace(",", "")) for m in NUMBER_RX.finditer(text)}
  for m in FRACTION_RX.finditer(text):
    if m.group("g"):
      part = GLYPH_FRACTION[m.group("g")]
    elif int(m.group("d")):
      part = int(m.group("n")) / int(m.group("d"))
    else:
      continue
    found.add(round(float(m.group("w") or 0) + part, 6))
  return found

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

def scale_parses(text) -> dict:
  raw = str(text or "").strip()
  if not raw:
    return result("scale_parses", False, "no scale text given")
  if SC.is_not_to_scale(raw):
    return result("scale_parses", True, "the text says the view is not to scale")
  ratio = SC.parse_scale_text(raw)
  if ratio is None:
    return result("scale_parses", False, f"{raw!r} is not a scale the scale reader knows")
  return result("scale_parses", True, f"a scale of 1 to {ratio:g}")

def value_in_quote(value, quote) -> dict:
  v, q = squash(value), squash(quote)
  if not v:
    return result("value_in_quote", False, "the value is empty")
  if v in q:
    return result("value_in_quote", True, "the value is inside its quote")
  return result("value_in_quote", False, "the value is not inside its quote")

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

def canon(token) -> str:
  """A token as OCR may confuse it: capitals, with O read as 0, I as 1 and S as 5 on both sides."""
  text = str(token or "").replace("\u201d", '"').replace("\u2033", '"').replace("''", '"').replace("\u00d7", "X").upper()
  return re.sub(r"[^A-Z0-9./'\"#@+-]", "", text).translate(CONFUSED)

def ocr_agrees(quote, ocr_words) -> dict:
  """Every word of the quote is among the words an OCR engine read in the same picture (sure enough, each used once, 0/O 1/I 5/S taken as one). The detail names the box of the words that agreed, which is where the quote stands."""
  tokens = [t for t in str(quote or "").split() if canon(t)]
  if not tokens:
    return result("ocr_agrees", False, "the quote is empty")
  if not ocr_words:
    return result("ocr_agrees", False, "no word was read from the picture of the region")
  free = [w for w in ocr_words if float(w.get("conf", 0.0)) >= OCR_MIN_CONF]
  used, boxes, missing = set(), [], []
  for t in tokens:
    c = canon(t)
    hit = next((i for i, w in enumerate(free) if i not in used and canon(w["text"]) == c), None)
    if hit is None:
      missing.append(t)
    else:
      used.add(hit)
      boxes.append(free[hit]["box"])
  if missing:
    return {**result("ocr_agrees", False, "not read from the picture: " + " ".join(missing[:6])), "box": None}
  box = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
  return {**result("ocr_agrees", True, f"all {len(tokens)} words of the quote were read from the picture"), "box": box}

def _lines_of(boxes: list) -> list:
  lines: list = []
  for b in sorted(boxes, key=lambda b: (b[1] + b[3]) / 2):
    for ln in lines:
      lo, hi = ln["span"]
      if min(hi, b[3]) - max(lo, b[1]) > 0.5 * (b[3] - b[1]):
        ln["boxes"].append(b)
        ln["span"] = (min(lo, b[1]), max(hi, b[3]))
        break
    else:
      lines.append({"boxes": [b], "span": (b[1], b[3])})
  return [sorted(ln["boxes"], key=lambda b: b[0]) for ln in lines]

def glyph_words(clusters: list) -> int:
  total = 0
  for line in _lines_of(clusters):
    gaps = [max(0.0, b[0] - a[2]) for a, b in zip(line, line[1:])]
    if len(gaps) < MIN_GAPS_FOR_WORDS:
      total += 1
      continue
    med = sorted(gaps)[len(gaps) // 2]
    total += 1 + sum(1 for g in gaps if g > WORD_GAP_TIMES * max(med, 1.0))
  return total

def glyphs_match(quote, clusters, box) -> dict:
  chars = [c for c in str(quote or "") if not c.isspace()]
  tokens = [t for t in str(quote or "").split() if canon(t)]
  if not chars:
    return result("glyphs_match", False, "the quote is empty")
  if not clusters or box is None:
    return result("glyphs_match", False, "no ink clusters or no box to count them in")
  x0, y0, x1, y1 = box
  
  px, py = BOX_PAD_SHARE * (y1 - y0), BOX_PAD_SHARE * (y1 - y0)
  inside = [c for c in clusters if x0 - px <= (c[0] + c[2]) / 2 <= x1 + px and y0 - py <= (c[1] + c[3]) / 2 <= y1 + py]
  slack = max(GLYPH_SLACK_MIN, int(round(GLYPH_SLACK_SHARE * len(chars))))
  if abs(len(inside) - len(chars)) > slack:
    return result("glyphs_match", False, f"{len(inside)} ink clusters in the box, {len(chars)} characters in the quote (allowed difference {slack})")
  words = glyph_words(inside)
  word_slack = 1 if len(tokens) <= 5 else max(1, int(round(GLYPH_SLACK_SHARE * len(tokens))))
  if abs(words - len(tokens)) > word_slack:
    return result("glyphs_match", False, f"the ink falls into {words} words, the quote has {len(tokens)} (allowed difference {word_slack})")
  return result("glyphs_match", True, f"{len(inside)} ink clusters in {words} words fit {len(chars)} characters in {len(tokens)} words")

def quote_supported(quote, region_text: str | None, ocr_words=None, clusters=None) -> dict:
  printed = quote_printed(quote, region_text)
  
  if printed["passed"]:
    return {**result("quote_supported", True, printed["detail"]), "support": TEXT_LAYER}
  if ocr_words is None or clusters is None:
    return {**result("quote_supported", False, printed["detail"] + "; no second source was read"), "support": None}
  agreed = ocr_agrees(quote, ocr_words)
  if not agreed["passed"]:
    return {**result("quote_supported", False, "the text layer does not show it and " + agreed["detail"]), "support": None}
  fit = glyphs_match(quote, clusters, agreed.get("box"))
  if not fit["passed"]:
    return {**result("quote_supported", False, "an OCR reading agrees, but " + fit["detail"]), "support": None}
  return {**result("quote_supported", True, "not in the text layer; the OCR reading agrees and " + fit["detail"]), "support": OCR_AND_GLYPHS}

def passed(results: list) -> bool:
  return bool(results) and all(r["passed"] for r in results)
