from __future__ import annotations
import re
from app.engine.measure import rule_registry as RR
from app.modules.drawings_boq.takeoff.extract import structure_tables as ST

RULE = "COLUMN_SCHEDULE_AXES"

SIZE_LABELS = ("SIZE", "SECTION", "DIMENSION", "DIMENSIONS")
STEEL_LABELS = ("STEEL", "REINFORCEMENT", "BARS", "MAIN", "VERTICAL")
LABELS = SIZE_LABELS + STEEL_LABELS
MIN_MARKS = 2

def _kind(text: str) -> str | None:
  t = text.upper().strip(":.")
  if t in SIZE_LABELS:
    return "SIZE"
  if t in STEEL_LABELS:
    return "STEEL"
  return None

def _groups(items: list, key, tol: float) -> list:
  out: list = []
  for it in sorted(items, key=key):
    if out and abs(key(it) - key(out[-1][-1])) <= tol:
      out[-1].append(it)
    else:
      out.append([it])
  return out

def _bands(pos: list) -> list:
  if len(pos) == 1:
    return [(pos[0] - 40.0, pos[0] + 40.0)]
  mids = [(pos[i] + pos[i + 1]) / 2 for i in range(len(pos) - 1)]
  lo = pos[0] - (mids[0] - pos[0])
  hi = pos[-1] + (pos[-1] - mids[-1])
  edges = [lo] + mids + [hi]
  return [(edges[i], edges[i + 1]) for i in range(len(pos))]

def _frame(words: list, orient: str):
  if orient == "ROWS":
    return lambda w: (w.vc, w.uc)
  return lambda w: (w.uc, w.vc)

def _layout(words: list, tol: float = 3.0) -> dict | None:
  marks = [w for w in words if w.turn == 0 and ST.MARK_RE.match(w.text.upper())]
  labels = [(w, _kind(w.text)) for w in words if w.turn == 0 and _kind(w.text)]
  if len(marks) < MIN_MARKS or not labels:
    return None
  best = None
  
  for orient in ("ROWS", "COLS"):
    f = _frame(words, orient)
    for grp in _groups(marks, lambda w: f(w)[1], tol):
      names = {w.text.upper() for w in grp}
      if len(grp) < MIN_MARKS or len(names) < len(grp):
        continue
      
      b = f(grp[0])[1]
      a_lo, a_hi = min(f(w)[0] for w in grp), max(f(w)[0] for w in grp)
      pick = []
      for lab, kind in labels:
        la, lb = f(lab)
        if (la < a_lo - 1.0 or la > a_hi + 1.0) and abs(lb - b) > tol:
          pick.append((lab, kind))
      for ag in _groups(pick, lambda p: f(p[0])[0], tol):
        kinds = {k for _, k in ag}
        if "SIZE" not in kinds or len(ag) < 1:
          continue
        score = (len(grp), len(kinds))
        if best is None or score > best[0]:
          best = (score, orient, grp, ag)
          
  if best is None:
    return None
  _, orient, grp, ag = best
  return {"orient": orient, "marks": grp, "labels": ag}

def read_words(words: list) -> dict | None:
  lay = _layout(words)
  if not lay:
    return None
  
  f = _frame(words, lay["orient"])
  marks = sorted(lay["marks"], key=lambda w: f(w)[0])
  labs = sorted(lay["labels"], key=lambda p: f(p[0])[1])
  m_bands = _bands([f(w)[0] for w in marks])
  l_bands = _bands([f(p[0])[1] for p in labs])
  used = {id(w) for w in marks} | {id(p[0]) for p in labs}
  cells: list = []
  
  for m, mb in zip(marks, m_bands):
    rec = {"mark": m.text.upper(), "floor": None, "state": "NONE", "why": "blank", "axes": lay["orient"]}
    texts: dict = {}
    for (lab, kind), lb in zip(labs, l_bands):
      hit = [w for w in words if w.turn == 0 and id(w) not in used and mb[0] <= f(w)[0] <= mb[1] and lb[0] <= f(w)[1] <= lb[1]]
      hit.sort(key=lambda w: (round(w.vc / 3.0), w.u0))
      texts.setdefault(kind, []).append(" ".join(w.text for w in hit))
    size = next((s for s in (ST.parse_size(t) for t in texts.get("SIZE", [])) if s), None)
    steel = next((s for s in (ST.parse_steel(t) for t in texts.get("STEEL", [])) if s), None)
    if size:
      rec.update(state="READ", why=None, size={"size_in": size}, steel=steel, mid=None, joint=None)
    cells.append(rec)
  if not any(c["state"] == "READ" for c in cells):
    return None
  return {"kind": "COLUMN_SCHEDULE", "cells": cells, "tables": 1, "reader": "AXES", "axes": lay["orient"]}

def read(raw) -> dict | None:
  if not RR.on(RULE):
    return None
  if not raw.words:
    return None
  words, _ = ST.upright_words(raw)
  return read_words(words)
