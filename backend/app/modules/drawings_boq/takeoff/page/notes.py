from __future__ import annotations
from app.modules.drawings_boq.takeoff.page import lines as LN
from app.modules.drawings_boq.takeoff.page import settings as S
from app.modules.drawings_boq.takeoff.page.model import NOTES, Region

def _lines(ctx, taken: list) -> list:
  free = [(i, w) for i, w in enumerate(ctx.words) if w.turn == 0 and not any(t[0] <= (w.u0 + w.u1) / 2 <= t[2] and t[1] <= (w.v0 + w.v1) / 2 <= t[3] for t in taken)]
  return LN.runs(free, ctx.h)

def find(ctx, taken: list) -> list:
  gap = S.get("notes", "line_gap") * ctx.h
  align = S.get("notes", "align") * ctx.h
  rows = _lines(ctx, taken)
  rows.sort(key=lambda r: (round(r["u0"] / max(align, 1e-6)), -r["y"]))
  blocks: list = []
  
  for r in rows:
    for b in blocks:
      last = b[-1]
      if abs(last["u0"] - r["u0"]) <= align and 0 < last["y"] - r["y"] <= gap:
        b.append(r)
        break
    else:
      blocks.append([r])
  out = []
  
  for b in blocks:
    n_words = sum(len(r["words"]) for r in b)
    sentence = sum(1 for r in b for _i, w in r["words"] if sum(1 for ch in w.text if ch.isalpha()) >= 3)
    if len(b) < S.get("notes", "min_lines") or n_words < S.get("notes", "min_words"):
      if not (sentence >= S.get("notes", "min_sentence_words") and sentence >= 0.6 * n_words):
        continue
    ws = [w for r in b for _i, w in r["words"]]
    ids = [i for r in b for i, _w in r["words"]]
    box = (min(w.u0 for w in ws), min(w.v0 for w in ws), max(w.u1 for w in ws), max(w.v1 for w in ws))
    out.append(Region(NOTES, ctx.user_box(box), " ".join(w.text for _i, w in b[0]["words"])[:80], ids, lines=len(b), rings=0, turn=ctx.turn, confidence=0.7, source="notes.lines"))
  return out
