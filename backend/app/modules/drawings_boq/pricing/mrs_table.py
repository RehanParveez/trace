from __future__ import annotations
import re
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass, field

LINE_TOL = 4.5
NUMBER = re.compile(r"^\d{1,3}(?:,\d{3})*(?:\.\d+)?$|^\d+(?:\.\d+)?$")
DASH = re.compile(r"^[-–—]{1,3}$")
LABEL = re.compile(r"^(\(?)\s*([A-Za-z]|[ivxIVX]{2,4}|\d{1,2})\s*\)\s*(.*)$")
FOOTER = re.compile(r"chap(?:ter)?\s*[-.]?\s*(\d+)\s*\(([^)]*)\)", re.I)
TRAILING_UNIT = re.compile(r"\s((?:\d[\d,]*\s*)?(?:Per\s+)?(?:Cft|Sft|Rft|Cum|Sqm|Nos|Each|Job|Km|Chain|Ton|Kg)s?\.?)$", re.I)
PAGE_CELL = re.compile(r"^Page\s+\d+$")
LEGEND = re.compile(r"^\*+\s")
CHAPTER_HEAD = re.compile(r"CHAPTER\s*NO\.?\s*(\d+)\s*\(([^)]*)\)", re.I)
ROMAN = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii"}

def to_decimal(text: str) -> Decimal | None:
  t = text.strip().replace(",", "")
  if not NUMBER.match(text.strip()):
    return None
  try:
    return Decimal(t)
  except InvalidOperation:
    return None

@dataclass
class Node:
  kind: str                 
  label: str | None
  text: list
  rated: bool = False
  item_no: str | None = None
  hint_b: list = field(default_factory=list)
  hint_m: list = field(default_factory=list)

  @property
  def joined(self) -> str:
    return re.sub(r"\s+", " ", " ".join(self.text)).strip()

@dataclass
class TableRow:
  page: int
  y: float
  chapter_no: int | None
  chapter: str | None
  item: str                  
  code: str                 
  path: list                 
  leaf: str
  unit_b: str | None = None
  labour_b: Decimal | None = None
  comp_b: Decimal | None = None
  unit_m: str | None = None
  labour_m: Decimal | None = None
  comp_m: Decimal | None = None
  spec_no: str = ""
  remarks: str = ""
  flags: list = field(default_factory=list)
  extra_text: list = field(default_factory=list)

  def flag(self, code: str) -> None:
    if code not in self.flags:
      self.flags.append(code)

  @property
  def description(self) -> str:
    parts = [p for p in [*self.path, self.leaf] if p]
    return " | ".join(parts)

@dataclass
class PageInfo:
  number: int
  table: bool
  chapter_no: int | None = None
  chapter: str | None = None
  rows: int = 0
  note: str = ""
  norms: bool = False

@dataclass
class Columns:
  unit_b: float
  lab_b: float
  comp_b: float
  unit_m: float
  lab_m: float
  comp_m: float
  desc_right: float
  spec_left: float
  header_bottom: float
  spec_edge: float = 595.0

  def bounds(self) -> list:
    cs = [self.unit_b, self.lab_b, self.comp_b, self.unit_m, self.lab_m, self.comp_m]
    return [(a + b) / 2 for a, b in zip(cs, cs[1:])]

  def column(self, cx: float) -> str | None:
    names = ["unit_b", "lab_b", "comp_b", "unit_m", "lab_m", "comp_m"]
    b = self.bounds()
    if cx < self.desc_right or cx >= self.spec_left:
      return None
    for i, edge in enumerate(b):
      if cx < edge:
        return names[i]
    return names[-1]

def _cx(c) -> float:
  return (c.x0 + c.x1) / 2

def _heading_pair(pc, pattern: str):
  hits = sorted((c for c in pc.cells if re.fullmatch(pattern, c.text) and c.y < 450), key=lambda c: (c.y, c.x0))
  
  for i in range(len(hits) - 1):
    if abs(hits[i].y - hits[i + 1].y) < 3 and hits[i + 1].x0 - hits[i].x0 > 60:
      return hits[i], hits[i + 1]
  return None

def find_columns(pc) -> Columns | None:
  lab, comp = _heading_pair(pc, "Labour"), _heading_pair(pc, "Composite")
  if lab is None or comp is None or abs(lab[0].y - comp[0].y) > 25:
    return None

  unit = _heading_pair(pc, r"Unit( of)?")
  ub = _cx(unit[0]) if unit else _cx(lab[0]) - 45
  um = _cx(unit[1]) if unit else _cx(lab[1]) - 45
  spec = [c for c in pc.cells if re.fullmatch(r"Spec\.?", c.text) and abs(c.y - lab[0].y) < 40]
  spec_left = (min(c.x0 for c in spec) - 6) if spec else (_cx(comp[1]) + 40)
  bottom = max(c.y for c in [*lab, *comp, *(unit or ())]) + 3
  return Columns(ub, _cx(lab[0]), _cx(comp[0]), um, _cx(lab[1]), _cx(comp[1]),
    desc_right=ub - 17, spec_left=spec_left, header_bottom=bottom, spec_edge=spec_left + 6 + 27)

def _clusters(values: list, gap: float) -> list:
  vals = sorted(values)
  out: list = []
  for v in vals:
    if out and v - out[-1][-1] <= gap:
      out[-1].append(v)
    else:
      out.append([v])
  return out

def infer_columns(pc, foot_y: float) -> Columns | None:
  nums = [c for c in pc.cells if (NUMBER.match(c.text) or DASH.match(c.text)) and 290 <= _cx(c) <= 575 and c.y < foot_y]
  groups = _clusters([_cx(c) for c in nums], 22)
  groups = [g for g in groups if len(g) >= 2]
  if len(groups) == 5:
    groups = groups[:4]
  if len(groups) != 4:
    return None
  centres = [sum(g) / len(g) for g in groups]
  right = max(c.x1 for c in nums if _cx(c) >= centres[3] - 15 and _cx(c) <= centres[3] + 25)
  return Columns(centres[0] - 45, centres[0], centres[1], centres[2] - 45, centres[2], centres[3],
    desc_right=centres[0] - 62, spec_left=right + 8, header_bottom=0.0, spec_edge=right + 8 + 33)

def _kind(label: str, sibling_letters: dict) -> str:
  if label.isdigit():
    return "NUM"
  if label.isupper():
    return "UPPER"
  low = label.lower()
  if low in ROMAN and len(low) > 1:
    return "ROMAN"
  if low in ("i", "v", "x"):
    if low == "i" and sibling_letters.get("LOWER") == "h":
      return "LOWER"
    if low == "v" and sibling_letters.get("LOWER") == "u":
      return "LOWER"
    if low == "x" and sibling_letters.get("LOWER") == "w":
      return "LOWER"
    return "ROMAN"
  return "LOWER"

def _follows(prev: str, new: str, base: str) -> bool:
  try:
    if base == "NUM":
      return int(new) == int(prev) + 1
    if base in ("LOWER", "UPPER"):
      return len(prev) == 1 and len(new) == 1 and ord(new.lower()) == ord(prev.lower()) + 1
    if base == "ROMAN":
      order = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii"]
      return order.index(new.lower()) == order.index(prev.lower()) + 1
  except ValueError:
    return False
  return False

class Reader:
  def __init__(self) -> None:
    self.stack: list = []
    self.rows: list = []
    self.item: str | None = None
    self.chapter_no: int | None = None
    self.chapter: str | None = None
    self.last_row: TableRow | None = None
    self.after_row = False
    self.pages: list = []
    self.sibling_letters: dict = {}
    self.item_blocks: list = []      
    self.notes: dict = {}            
    self.cols = None

  def feed(self, pc) -> PageInfo:
    info = PageInfo(pc.number, table=False)
    page_cells = [c for c in pc.cells if PAGE_CELL.match(c.text)]
    foot_y = (min(c.y for c in page_cells) - 3) if page_cells else pc.height + 1
    foot = [c for c in pc.cells if c.y >= foot_y]
    m = FOOTER.search(" ".join(c.text for c in sorted(foot, key=lambda c: c.x0)))
    
    if m:
      self._chapter(int(m.group(1)), m.group(2).strip())
    for c in pc.cells:
      h = CHAPTER_HEAD.search(c.text)
      if h and c.y < 80:
        self._chapter(int(h.group(1)), h.group(2).strip())
    if any(c.text.startswith("Dry Material Required") for c in pc.cells):
      info.chapter_no, info.chapter, info.norms, info.note = self.chapter_no, self.chapter, True, "material coefficient table (not rates)"
      self.pages.append(info)
      return info
  
    cols = find_columns(pc)
    headed = cols is not None
    if cols is None:
      cols = infer_columns(pc, foot_y)
    if cols is None and any(PAGE_CELL.match(c.text) is None and NUMBER.match(c.text) for c in pc.cells) and self.cols is not None:
      cols = self.cols
      info.note = "columns carried from the page before"
    if cols is None:
      lines = self._plain_lines(pc, foot)
      if self.chapter_no is not None:
        self.notes.setdefault(self.chapter_no, []).extend(lines)
      info.chapter_no, info.chapter, info.note = self.chapter_no, self.chapter, f"{len(lines)} lines of notes"
      self.pages.append(info)
      return info
  
    self.cols = cols
    info.table, info.chapter_no, info.chapter = True, self.chapter_no, self.chapter
    body = [c for c in pc.cells if cols.header_bottom < c.y < foot_y]
    if not headed:
      body = self._below_notes(body, cols)
    lines, side = self._lines(body, cols)
    before = len(self.rows)
    started = headed
    for ln in lines:
      rated = any(ln["figs"].get(k) for k in ("unit_b", "lab_b", "comp_b", "unit_m", "lab_m", "comp_m"))
      if not started and not (ln["srno"] or rated or LABEL.match(ln["desc"] or "")):
        continue
      started = True
      self._line(ln, pc.number)
      
    self._attach_side(side, pc.number, before, cols.spec_edge)
    info.rows = len(self.rows) - before
    self.pages.append(info)
    return info

  def _chapter(self, no: int, name: str) -> None:
    if no != self.chapter_no:
      self.stack, self.item, self.last_row, self.after_row = [], None, None, False
    self.chapter_no, self.chapter = no, name

  def _below_notes(self, body: list, cols: Columns) -> list:
    figs = [c for c in body if (NUMBER.match(c.text) or DASH.match(c.text)) and _cx(c) > cols.desc_right]
    first_fig = min((c.y for c in figs), default=1e9)
    notes = [c for c in body if c.y < first_fig and c.x0 < cols.desc_right and c.x1 > cols.desc_right + 12 and len(c.text) > 25]
    if not notes:
      return body
    cut = max(c.y for c in notes) + 4
    return [c for c in body if c.y > cut]

  def _plain_lines(self, pc, foot) -> list:
    out, cur, last = [], [], None
    skip = {id(c) for c in foot}
    for c in pc.cells:
      if id(c) in skip or c.text.startswith("MARKET RATES SYSTEM") or c.text.startswith("(01.") or c.text == "FINANCE DEPARTMENT":
        continue
      if last is not None and abs(c.y - last) > LINE_TOL:
        out.append(" ".join(cur))
        cur = []
      cur.append(c.text)
      last = c.y
    if cur:
      out.append(" ".join(cur))
    return [re.sub(r"\s+", " ", x).strip() for x in out if x.strip()]

  def _lines(self, body: list, cols: Columns):
    left, side = [], []
    for c in body:
      if _cx(c) >= cols.spec_left or c.x0 >= cols.spec_left:
        side.append(c)
      else:
        left.append(c)
        
    left.sort(key=lambda c: (c.y, c.x0))
    words = [c.x0 for c in left if c.x0 < cols.desc_right and not re.fullmatch(r"\d{1,3}", c.text) and len(c.text) > 3]
    srno_right = min(min(words) - 3, 45.0) if words else 29.0
    lines: list = []
    for c in left:
      if lines and abs(c.y - lines[-1]["y"]) <= LINE_TOL:
        ln = lines[-1]
        ln["cells"].append(c)
        ln["y"] = (ln["y"] * (len(ln["cells"]) - 1) + c.y) / len(ln["cells"])
      else:
        lines.append({"y": c.y, "cells": [c]})
        
    out = []
    for ln in lines:
      cells = sorted(ln["cells"], key=lambda c: c.x0)
      srno, desc, figs = None, [], {}
      for k, c in enumerate(cells):
        t = c.text
        if c.x1 <= srno_right and re.fullmatch(r"\d{1,3}", t):
          srno = t
          continue
        if re.fullmatch(r"\d{1,2}", t) and c.x0 < cols.desc_right and k + 1 < len(cells) and 0 <= cells[k + 1].x0 - c.x1 <= 25 and cells[k + 1].x0 < cols.desc_right:
          t = t + ")"           
        col = cols.column(_cx(c)) if c.x0 >= cols.desc_right else None
        if col is None and c.x1 > cols.desc_right + 6 and c.x0 < cols.desc_right:
          
          m = TRAILING_UNIT.search(t)
          
          if m:
            figs.setdefault("unit_b", []).append(m.group(1).strip())
            t = t[:m.start()].rstrip()
          else:
            parts = t.split(" ")
            span = (c.x1 - c.x0) / max(1, len(t))
            cut, pos, starts = len(parts), 0, []
            for w in parts:
              starts.append(c.x0 + pos * span)
              pos += len(w) + 1
            while cut > 1 and starts[cut - 1] >= cols.desc_right - 8:
              cut -= 1
            if cut < len(parts):
              figs.setdefault("unit_b", []).append(" ".join(parts[cut:]))
              t = " ".join(parts[:cut])
              
        if col is None and re.fullmatch(r"\d[\d,]*", t) and c.x0 > cols.desc_right - 45 and k + 1 < len(cells) and cols.column(_cx(cells[k + 1])) == "unit_b":
          figs.setdefault("unit_b", []).append(t)      
          continue
        if col is None:
          if t:
            desc.append(t)
        else:
          figs.setdefault(col, []).append(t)
      out.append({"y": ln["y"], "srno": srno, "desc": re.sub(r"\s+", " ", " ".join(desc)).strip(), "figs": figs})
    return out, side

  def _line(self, ln: dict, page: int) -> None:
    self._line_inner(ln, page)
    figs = ln["figs"]
    if not any(figs.get(k) for k in ("lab_b", "comp_b", "lab_m", "comp_m")) and self.stack:

      for key, att in (("unit_b", "hint_b"), ("unit_m", "hint_m")):
        if figs.get(key):
          getattr(self.stack[-1], att).append(" ".join(figs[key]))

  def _line_inner(self, ln: dict, page: int) -> None:
    figs, desc, srno = ln["figs"], ln["desc"], ln["srno"]
    rated = any(figs.get(k) for k in ("lab_b", "comp_b", "lab_m", "comp_m"))
    if srno is not None:
      self.item = srno
      self.stack = [Node("ITEM", None, [desc] if desc else [], item_no=srno)]
      self.sibling_letters = {}
      self.item_blocks.append((page, ln["y"], srno))
      self.after_row = False
      
      if rated:
        self._emit(ln, page, leaf_node=self.stack[-1])
      return
    if not self.stack:
      return
    m = LABEL.match(desc) if desc else None
    if m:
      opened, label, rest = m.group(1), m.group(2), m.group(3)
      base = _kind(label, self.sibling_letters)
      kind = base + ("P" if opened else "C")

      for i, node in enumerate(self.stack):
        if node.kind == kind or (i == len(self.stack) - 1 and node.kind[:-1] == base and node.kind[-1:] in "PC" and node.label and _follows(node.label, label, base)):
          del self.stack[i:]
          break
      if base == "LOWER":
        self.sibling_letters["LOWER"] = label.lower()
      node = Node(kind, label, [rest] if rest else [])
      self.stack.append(node)
      self.after_row = False
      
      if rated:
        self._emit(ln, page, leaf_node=node)
      return
    if rated:
      while self.stack and self.stack[-1].kind == "PLAIN" and self.stack[-1].rated:
        self.stack.pop()
      top = self.stack[-1]
      runs_on = bool(top.joined) and not top.rated and not re.search(r"[:;]\s*[-–—]?\s*$", top.joined)
      if runs_on:
        top.text.append(desc)
        self._emit(ln, page, leaf_node=top)
      else:
        node = Node("PLAIN", None, [desc] if desc else [])
        self.stack.append(node)
        self._emit(ln, page, leaf_node=node)
      self.after_row = True
      return
    if not desc or LEGEND.match(desc):
      return

    if self.after_row and self.last_row is not None and desc[:1].islower():
      self.last_row.leaf = f"{self.last_row.leaf} {desc}".strip()
      self.last_row.flag("WRAPPED_DESCRIPTION")
      self.stack[-1].text.append(desc)
      return
    if self.after_row:
      node = Node("PLAIN", None, [desc])
      while self.stack and self.stack[-1].kind == "PLAIN":
        self.stack.pop()
      self.stack.append(node)
      self.after_row = False
      return
    self.stack[-1].text.append(desc)

  def _unit(self, own: str | None, hints: list, which: str) -> str | None:
    hint = next((h for h in hints if h), None)
    
    if own and own.strip().lower().rstrip(".").replace(" ", "") in ("ditto", "do", "-do-", "-ditto-"):
      prev = self.last_row
      return (prev.unit_b if which == "unit_b" else prev.unit_m) if prev else own
    if own is None:
      return hint[0] if hint else None
    if hint and own.islower() and own.isalpha() and len(hint) >= 2:
      return f"{hint[-1]} {own}"        
    if hint and own[:1].islower() and hint[-1].lower().rstrip().endswith(" of"):
      return f"{hint[-1]} {own}"  
        
    prev = self.last_row
    attr = "unit_b" if which == "unit_b" else "unit_m"
    if prev is not None and re.match(r"of\s+\w", own) and getattr(prev, attr):
      joined = f"{getattr(prev, attr)} {own}"        
      setattr(prev, attr, joined)
      return joined
    return own

  def _emit(self, ln: dict, page: int, leaf_node: Node) -> None:
    figs = ln["figs"]
    
    anc = [n for n in self.stack if n is not leaf_node]
    code = (self.item or "?") + "".join(f"({n.label})" for n in anc if n.label) + (f"({leaf_node.label})" if leaf_node.label else "")
    row = TableRow(page=page, y=ln["y"], chapter_no=self.chapter_no, chapter=self.chapter, item=self.item or "?", code=code,
      path=[n.joined for n in anc if n.joined], leaf=leaf_node.joined)
    row.unit_b = self._unit(" ".join(figs.get("unit_b", [])) or None, [n.hint_b for n in reversed(self.stack)], "unit_b")
    row.unit_m = self._unit(" ".join(figs.get("unit_m", [])) or None, [n.hint_m for n in reversed(self.stack)], "unit_m")
    for key, attr in (("lab_b", "labour_b"), ("comp_b", "comp_b"), ("lab_m", "labour_m"), ("comp_m", "comp_m")):
      parts = figs.get(key, [])
      if not parts:
        continue
    
      joined = " ".join(parts)
      val = to_decimal(joined)
      if val is None and len(parts) > 1:
        val = to_decimal("".join(parts))        
      if val is not None:
        setattr(row, attr, val)
      elif not DASH.match(joined):
        row.flag("RATE_TEXT")
        row.extra_text.append(joined)
        
    leaf_node.rated = True
    self.rows.append(row)
    self.last_row = row
    self.after_row = True

  def _attach_side(self, side: list, page: int, first_row_index: int, edge: float) -> None:
    blocks = [(y, it) for pg, y, it in self.item_blocks if pg == page]
    prior = self.rows[first_row_index - 1].item if first_row_index > 0 else None
    cur_item = prior or (self.rows[first_row_index].item if first_row_index < len(self.rows) else None)
    rows_here = self.rows[first_row_index:]
    bag: dict = {}
    
    for c in sorted(side, key=lambda c: (c.y, c.x0)):
      item = cur_item
      for y, it in blocks:
        if y - 3 <= c.y:
          item = it
      if item is not None:
        bag.setdefault(item, []).append(c)
    for item, cells in bag.items():
      cells.sort(key=lambda c: (round(c.y / 3), c.x0))
      spec = " ".join(c.text for c in cells if c.x0 < edge)
      rem = " ".join(c.text for c in cells if c.x0 >= edge)
      for r in rows_here:
        if r.item == item:
          r.spec_no = (r.spec_no + " " + spec).strip()
          r.remarks = (r.remarks + " " + rem).strip()

def read_tables(pages: list) -> tuple[list, list, dict]:
  r = Reader()
  for pc in pages:
    r.feed(pc)
  return r.rows, r.pages, r.notes
