from __future__ import annotations
import re
import hashlib

TYPE_MIX = {"a": "1:1:2", "b": "1:1.5:3", "c": "1:2:4"}
_FRAC = r"(?:1\s*[-\s]?\s*1\s*/\s*2|1\s*½|1½|1\.5|\d+(?:\.\d+)?)"
_MIX3 = re.compile(rf"(?<![\d.:/])(\d+(?:\.\d+)?)\s*:\s*({_FRAC})\s*:\s*(\d+(?:\.\d+)?)(?![\d])")
_MIX2 = re.compile(rf"(?<![\d.:/])(1)\s*:\s*({_FRAC})(?![\d:])")
_TYPE = re.compile(r"\btype\s+([abc])\b", re.I)
_PSI = re.compile(r"\b(\d{4})\s*psi\b", re.I)
_GRADE = re.compile(r"\bgrade[\s-]*(\d{2})\b", re.I)
_THICK_UP = re.compile(r"\b(?:up\s*to|upto|not more than)\s*(\d+)\s*(?:\"|in\b|inch)", re.I)
_THICK_OVER = re.compile(r"\b(?:more than|above|over|exceeding)\s*(\d+)\s*(?:\"|in\b|inch)\s*(?:thick)?", re.I)

def _frac(s: str) -> str:
  s = re.sub(r"\s+", "", s)
  if s in ("1½", "11/2", "1-1/2"):
    return "1.5"
  return s.replace("½", ".5").replace("1-1/2", "1.5")

def mix_of(text: str) -> str | None:
  t = text.replace("½", " 1/2 ").replace("¼", " 1/4 ")
  t = re.sub(r"(\d)\s+1/2", r"\1-1/2", t)
  m = _MIX3.search(t)
  if m:
    return f"{m.group(1)}:{_frac(m.group(2))}:{m.group(3)}"
  m = _MIX2.search(t)
  if m:
    return f"{m.group(1)}:{_frac(m.group(2))}"
  return None

def member_of(path_text: str) -> str | None:
  t = path_text.lower()
  if "concrete" not in t and "r.c.c" not in t and "rcc" not in t:
    return None
  if "precast" in t and "laid in situ" not in t:
    return "precast"

  if re.search(r"reinforced|r\.c\.c|rcc|prestressed", t):
    if re.search(r"pile cap|raft|strip foundation|footing|base slab|horizontal shuttering", t):
      return "foundation"
    if re.search(r"retaining|shear wall", t):
      return "wall"
    if re.search(r"roof slab|beams|columns|lintel|girder", t):
      return "frame"
    if re.search(r"\bpile\b|bored", t):
      return "pile"
    return None

  if re.search(r"\bplain\b", t):
    return "plain"
  if "ballast" in t:
    return "ballast"
  return None

def part_of(path_text: str) -> str | None:
  t = path_text.lower()
  if not re.search(r"brick|masonry|stone|plaster|pointing", t):
    return None
  for pat, name in ((r"foundation and plinth|foundation & plinth|in foundation", "foundation"), (r"ground floor", "ground"), (r"first floor", "first"),
      (r"second floor", "second"), (r"third floor", "third"), (r"other than building", "other_than_building"), (r"boundary wall", "boundary_wall"),
      (r"in buildings", "building")):
    if re.search(pat, t):
      return name
  return None

def facts_of(path: list, leaf: str) -> dict:
  levels = [leaf, *reversed(path)]
  out: dict = {}
  
  for text in levels:
    mix = mix_of(text)
    if mix:
      out["mix"] = mix
      break
    t = _TYPE.search(text)
    if t:
      out["mix"] = TYPE_MIX[t.group(1).lower()]
      break
  for text in levels:
    p = _PSI.search(text)
    if p:
      out["psi"] = p.group(1)
      break
  for text in levels:
    g = _GRADE.search(text)
    if g:
      out["grade"] = g.group(1)
      break
  for text in levels:
    u, o = _THICK_UP.search(text), _THICK_OVER.search(text)
    if u:
      out["thick"] = f"<={u.group(1)}in"
      break
    if o:
      out["thick"] = f">{o.group(1)}in"
      break
  
  whole = " ".join([*path, leaf])
  mem = member_of(" ".join(path))
  if mem:
    out["member"] = mem
  part = part_of(whole)
  if part:
    out["part"] = part
  return out

def spec_key(path: list, leaf: str) -> str | None:
  facts = facts_of(path, leaf)
  order = ("member", "part", "mix", "psi", "grade", "thick")
  parts = [f"{k}={facts[k]}" for k in order if k in facts]
  return ";".join(parts) or None

CODE_CHARS = 50

def compose_code(base: str, spec: str | None) -> str:
  if not spec:
    return base
  tail = "@" + spec
  if len(base) + len(tail) <= CODE_CHARS:
    return base + tail

  digest = hashlib.sha1(spec.encode()).hexdigest()[:6]
  tail = "@" + spec[: max(8, CODE_CHARS - len(base) - 8)] + "~" + digest
  if len(base) + len(tail) > CODE_CHARS:
    base = base[: max(1, CODE_CHARS - len(tail))]
  return (base + tail)[:CODE_CHARS]
