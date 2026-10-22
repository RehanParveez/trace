from __future__ import annotations
import re
from dataclasses import dataclass, field

REREADS = 3                      
MIN_AGREE = 3                    
RECHECK_CONF = 92.0              
MAX_CHECKS = 150                 
MAX_LISTED = 20                   

CONFUSABLE = set("68520O1oIl|SBZ")              
_DIM_PUNCT = set("'\"-.,/xX@+()")
_LETTER_TO_DIGIT = {"O": "0", "o": "0", "I": "1", "l": "1", "|": "1", "S": "5"}   
_SHAPE_LETTERS = {**_LETTER_TO_DIGIT, "B": "8", "Z": "2"}                        
_DIGIT_TO_LETTER = {"0": "O", "1": "I", "5": "S", "8": "B", "6": "G"}              
_TAG = re.compile(r"^[A-Za-z]{1,4}[-/]?\d{1,3}[A-Za-z]?$")                         
_FIGURE = re.compile(r"^\d[\d.,/'\"\-xX@+()]*$")                                   

@dataclass
class Verdict:
  kind: str                 
  text: str                  
  reads: list = field(default_factory=list)

def _real_digits(text: str) -> int:
  return sum(1 for ch in text if ch.isdigit())

def is_figure(text: str) -> bool:
  t = text.strip()
  if not t or _TAG.match(t):
    return False
  mapped = "".join(_SHAPE_LETTERS.get(ch, ch) for ch in t)
  if not _FIGURE.match(mapped):
    return False
  return _real_digits(t) >= 1

def repair_figure(text: str) -> str:
  t = text.strip()
  if not t or _TAG.match(t):
    return text
  letters = [ch for ch in t if ch in _LETTER_TO_DIGIT]
  if not letters:
    return text

  rest = [ch for ch in t if ch not in _LETTER_TO_DIGIT]
  if any(not (ch.isdigit() or ch in _DIM_PUNCT) for ch in rest):
    return text
  if _real_digits(t) < 2 or len(letters) > _real_digits(t):
    return text

  for i, ch in enumerate(t):
    if ch in _LETTER_TO_DIGIT:
      left = t[i - 1] if i > 0 else ""
      right = t[i + 1] if i + 1 < len(t) else ""
      if not (left.isdigit() or right.isdigit() or left in _DIM_PUNCT or right in _DIM_PUNCT):
        return text
    
  fixed = "".join(_LETTER_TO_DIGIT.get(ch, ch) for ch in t)
  return fixed if _FIGURE.match(fixed) else text

def repair_label(text: str, names) -> str:
  t = text.strip()
  upper = t.upper()
  
  if len(t) < 3 or upper in names:
    return text
  if not any(ch.isalpha() and ch not in "lI" for ch in t):
    return text

  mapped = "".join(_DIGIT_TO_LETTER.get(ch, "I" if ch in "l|" else ch) for ch in upper)
  if mapped != upper and mapped in names:
    return mapped
  return text

def worth_rereading(text: str, conf: float) -> bool:
  if not is_figure(text):
    return False
  if not any(ch in CONFUSABLE for ch in text):
    return False
  has_letter = any(ch.isalpha() for ch in text if ch not in "xX")
  return has_letter or conf < RECHECK_CONF

def plan(rows: list, max_checks: int = MAX_CHECKS) -> list:
  cand = [(rows[i]["conf"], i) for i in range(len(rows)) if worth_rereading(rows[i]["text"], rows[i]["conf"])]
  cand.sort()
  return [i for _, i in cand[:max_checks]]

def decide(first: str, rereads: list) -> Verdict:
  reads = [repair_figure(first)] + [repair_figure(r) for r in rereads if r]
  
  if len(reads) < MIN_AGREE:
    return Verdict("UNCHECKED", reads[0], reads)
  counts: dict = {}
  
  for r in reads:
    counts[r] = counts.get(r, 0) + 1
  best = max(counts.values())
  winners = [r for r, n in counts.items() if n == best]
  if best >= MIN_AGREE and len(winners) == 1:
    win = winners[0]
    return Verdict("SAME" if win == reads[0] and win == first.strip() else "REPAIRED", win, reads)
  return Verdict("SPLIT", reads[0], reads)

def apply(rows: list, verdicts: dict, names) -> tuple:
  kept: list = []
  
  report = {"checked": len(verdicts), "repaired": [], "split": [], "unchecked": 0, "label_repaired": 0, "figure_repaired": 0}
  for i, row in enumerate(rows):
    v = verdicts.get(i)
    text = row["text"]
    if v is not None:
      if v.kind == "SPLIT":
        report["split"].append({"reads": list(v.reads), "row": i})
        continue
    
      if v.kind == "UNCHECKED":
        report["unchecked"] += 1
      if v.text != text.strip():
        report["repaired"].append({"from": text, "to": v.text, "row": i})
      kept.append({**row, "text": v.text})
      continue
  
    fixed = repair_figure(text)
    if fixed == text:
      fixed = repair_label(text, names)
      if fixed != text:
        report["label_repaired"] += 1
    else:
      report["figure_repaired"] += 1
    kept.append({**row, "text": fixed} if fixed != text else row)
  return kept, report
