from __future__ import annotations
from dataclasses import dataclass, field
import math
import ctypes
import time
from array import array

IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
MAX_PATH_OBJECTS = 1_500_000
MAX_SEGMENTS = 400_000
MAX_RINGS = 40_000
MAX_RING_VERTICES = 400
MAX_WORDS = 40_000
MAX_FORM_DEPTH = 8
DEDUP_SCALE = 100.0  
CURVE_CHORD_PT = 2.0
MAX_CURVE_CHORDS = 12
DEFAULT_BUDGET_S = 40.0
ARROW_MAX_PT = 16.0

class PdfOpenError(Exception):
  def __init__(self, code: str, message: str):
    super().__init__(message)
    self.code = code
    self.message = message

@dataclass
class Word:
  text: str
  x0: float
  y0: float
  x1: float
  y1: float
  angle: float     
  size: float      
  cx: float
  cy: float
  length: float     
  height: float  

@dataclass
class Ring:
  pts: list         
  area: float       
  bbox: tuple       
  fill: bool
  curved: bool
  width: float

@dataclass
class RawPage:
  page_no: int
  width_pt: float
  height_pt: float
  rotation: int
  mediabox: tuple
  cropbox: tuple
  segs: array = field(default_factory=lambda: array("f"))     
  kinds: array = field(default_factory=lambda: array("B"))     
  rings: list = field(default_factory=list)
  words: list = field(default_factory=list)
  images: list = field(default_factory=list)                   
  stats: dict = field(default_factory=dict)

def _mul(m, n):
  a1, b1, c1, d1, e1, f1 = m
  a2, b2, c2, d2, e2, f2 = n
  return (a1 * a2 + b1 * c2, a1 * b2 + b1 * d2, c1 * a2 + d1 * c2, c1 * b2 + d1 * d2,
    e1 * a2 + f1 * c2 + e2, e1 * b2 + f1 * d2 + f2)

def _apply(m, x, y):
  return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])

def _matrix_of(obj) -> tuple:
  try:
    mat = obj.get_matrix()
    return tuple(float(v) for v in mat.get())
  except Exception:
    return IDENT

def _bezier(p0, p1, p2, p3, n):
  out = []
  for i in range(1, n + 1):
    t = i / n
    u = 1 - t
    out.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
      u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
  return out

def _shoelace(pts) -> float:
  s = 0.0
  for i in range(len(pts)):
    x1, y1 = pts[i]
    x2, y2 = pts[(i + 1) % len(pts)]
    s += x1 * y2 - x2 * y1
  return abs(s) / 2.0

def _rect_like(p) -> bool:
  if len(p) != 4:
    return False
  e = [(p[(i + 1) % 4][0] - p[i][0], p[(i + 1) % 4][1] - p[i][1]) for i in range(4)]
  ln = [math.hypot(*v) or 1e-9 for v in e]
  return all(abs((e[i][0] * e[(i + 1) % 4][0] + e[i][1] * e[(i + 1) % 4][1]) / (ln[i] * ln[(i + 1) % 4])) < 0.05 for i in range(4))

def open_document(contents: bytes):
  import pypdfium2 as pdfium
  try:
    return pdfium.PdfDocument(contents)
  except Exception as exc:  
    text = str(exc).lower()
    if "password" in text:
      raise PdfOpenError("PDF_ENCRYPTED", "This PDF is password protected.")
    raise PdfOpenError("PDF_UNREADABLE", "This PDF could not be read.")

def _text_words(page, stats: dict) -> list:
  import pypdfium2.raw as raw
  try:
    tp = page.get_textpage()
  except Exception:
    stats["text_error"] = True
    return []
  words: list = []
  
  try:
    n = tp.count_chars()
    stats["text_chars"] = 0
    mat = raw.FS_MATRIX()
    cur: list = []
    def flush():
      if not cur:
        return
      text = "".join(c[0] for c in cur)
      if text.strip():
        words.append(_make_word(text, cur))
      cur.clear()
    prev = None
    for i in range(n):
      u = raw.FPDFText_GetUnicode(tp.raw, i)
      ch = chr(u) if 0 < u < 0x110000 else ""
      generated = raw.FPDFText_IsGenerated(tp.raw, i)
      if not ch or ch.isspace() or generated and not ch.strip():
        flush()
        prev = None
        continue
    
      stats["text_chars"] += 1
      l, b, r, t = tp.get_charbox(i)
      if r <= l and t <= b:
        flush()
        prev = None
        continue
      raw.FPDFText_GetMatrix(tp.raw, i, ctypes.byref(mat))
      fs = raw.FPDFText_GetFontSize(tp.raw, i)
      scale = math.hypot(mat.a, mat.b) or 1.0
      size = abs(fs * scale) if fs else (t - b)
      angle = math.degrees(math.atan2(mat.b, mat.a)) % 360.0
      info = (ch, l, b, r, t, angle, size)
      if prev is not None:
        
        dx = (l + r) / 2 - (prev[1] + prev[3]) / 2
        dy = (b + t) / 2 - (prev[2] + prev[4]) / 2
        a = math.radians(prev[5])
        along = dx * math.cos(a) + dy * math.sin(a)
        across = -dx * math.sin(a) + dy * math.cos(a)
        da = abs((angle - prev[5] + 180) % 360 - 180)
        if da > 8 or along > 1.2 * max(prev[6], size) or along < -0.2 * prev[6] or abs(across) > 0.6 * max(prev[6], size):
          flush()
      cur.append(info)
      prev = info
      if len(words) >= MAX_WORDS:
        stats["words_truncated"] = True
        break
    flush()
  finally:
    try:
      tp.close()
    except Exception:
      pass
  return words

def _make_word(text: str, chars: list) -> Word:
  xs0 = min(c[1] for c in chars)
  ys0 = min(c[2] for c in chars)
  xs1 = max(c[3] for c in chars)
  ys1 = max(c[4] for c in chars)
  angle = chars[0][5]
  size = sorted(c[6] for c in chars)[len(chars) // 2]
  a = math.radians(angle)
  ux, uy = math.cos(a), math.sin(a)
  proj = []
  for c in chars:
    for px, py in ((c[1], c[2]), (c[3], c[2]), (c[3], c[4]), (c[1], c[4])):
      proj.append((px * ux + py * uy, -px * uy + py * ux))
  length = max(p[0] for p in proj) - min(p[0] for p in proj)
  height = max(p[1] for p in proj) - min(p[1] for p in proj)
  return Word(text=text, x0=xs0, y0=ys0, x1=xs1, y1=ys1, angle=angle, size=size, cx=(xs0 + xs1) / 2, cy=(ys0 + ys1) / 2,
    length=length, height=height)

def _subpaths(obj, matrix):
  
  import pypdfium2.raw as raw
  count = raw.FPDFPath_CountSegments(obj.raw)
  
  x = ctypes.c_float()
  y = ctypes.c_float()
  cur: list = []
  flags: list = []
  closed = False
  pending: list = []
  def emit():
    nonlocal cur, flags, closed
    if len(cur) >= 2:
      yield_list.append((cur, closed, flags))
    cur, flags, closed = [], [], False
  yield_list: list = []
  for i in range(count):
    seg = raw.FPDFPath_GetPathSegment(obj.raw, i)
    kind = raw.FPDFPathSegment_GetType(seg)
    raw.FPDFPathSegment_GetPoint(seg, ctypes.byref(x), ctypes.byref(y))
    pt = _apply(matrix, x.value, y.value)
    
    if kind == raw.FPDF_SEGMENT_MOVETO:
      emit()
      pending = []
      cur = [pt]
      flags = [0]
    elif kind == raw.FPDF_SEGMENT_LINETO:
      if not cur:
        cur, flags = [pt], [0]
      else:
        cur.append(pt)
        flags.append(0)
    elif kind == raw.FPDF_SEGMENT_BEZIERTO:
      pending.append(pt)
      
      if len(pending) == 3:
        if cur:
          chord = sum(math.dist(a, b) for a, b in zip([cur[-1]] + pending[:-1], pending))
          n = max(2, min(MAX_CURVE_CHORDS, int(chord / CURVE_CHORD_PT) + 1))
          pts = _bezier(cur[-1], pending[0], pending[1], pending[2], n)
          for k, p in enumerate(pts):
            cur.append(p)
            flags.append(1)
        else:
          cur, flags = [pending[2]], [0]
        pending = []
    if raw.FPDFPathSegment_GetClose(seg):
      closed = True
      emit()
      pending = []
  emit()
  return yield_list

def extract_page(doc, index: int, *, budget_s: float = DEFAULT_BUDGET_S) -> RawPage:
  import pypdfium2.raw as raw
  started = time.monotonic()
  page = doc[index]
  stats: dict = {"path_objects": 0, "form_objects": 0, "image_objects": 0, "text_chars": 0}
  
  try:
    crop = tuple(float(v) for v in page.get_cropbox())
    media = tuple(float(v) for v in page.get_mediabox())
    rotation = int(page.get_rotation() or 0) % 360
    out = RawPage(page_no=index + 1, width_pt=crop[2] - crop[0], height_pt=crop[3] - crop[1],
      rotation=rotation if rotation in (0, 90, 180, 270) else 0, mediabox=media, cropbox=crop)
    seen: set = set()
    chains: dict = {0: IDENT}
    total_image_area = 0.0
    deadline = started + budget_s
    for obj in page.get_objects(filter=[raw.FPDF_PAGEOBJ_PATH, raw.FPDF_PAGEOBJ_IMAGE, raw.FPDF_PAGEOBJ_FORM], max_depth=MAX_FORM_DEPTH):
      level = obj.level
      chain = chains.get(level, IDENT)
      kind = obj.type
      if kind == raw.FPDF_PAGEOBJ_FORM:
        stats["form_objects"] += 1
        chains[level + 1] = _mul(_matrix_of(obj), chain)
        continue
      if kind == raw.FPDF_PAGEOBJ_IMAGE:
        stats["image_objects"] += 1
        
        try:
          l, b, r, t = obj.get_bounds()
          corners = [_apply(chain, l, b), _apply(chain, r, b), _apply(chain, r, t), _apply(chain, l, t)] if level else [(l, b), (r, b), (r, t), (l, t)]
          bx0, bx1 = min(c[0] for c in corners), max(c[0] for c in corners)
          by0, by1 = min(c[1] for c in corners), max(c[1] for c in corners)
          px_w, px_h = obj.get_px_size()
          width_in = (bx1 - bx0) / 72.0
          dpi = (px_w / width_in) if width_in > 0 else 0.0
          out.images.append({"bbox": (bx0, by0, bx1, by1), "px_w": int(px_w), "px_h": int(px_h), "dpi": round(dpi, 1)})
        except Exception:
          pass
        continue
    
      stats["path_objects"] += 1
      if stats["path_objects"] > MAX_PATH_OBJECTS or time.monotonic() > deadline:
        stats["truncated"] = True
        break
      matrix = _mul(_matrix_of(obj), chain)
      fw = ctypes.c_float()
      try:
        raw.FPDFPageObj_GetStrokeWidth(obj.raw, ctypes.byref(fw))
        width = float(fw.value) * math.sqrt(abs(matrix[0] * matrix[3] - matrix[1] * matrix[2]))
      except Exception:
        width = 0.0
      fill_mode = ctypes.c_int()
      stroke = ctypes.c_int()
      
      try:
        raw.FPDFPath_GetDrawMode(obj.raw, ctypes.byref(fill_mode), ctypes.byref(stroke))
        filled = fill_mode.value != 0
      except Exception:
        filled = False
      for verts, closed, flags in _subpaths(obj, matrix):
        n = len(verts)
        curved = any(flags)
        ring_pts = None
        if closed and n >= 3:
          ring_pts = verts[:-1] if (len(verts) > 3 and math.dist(verts[0], verts[-1]) < 1e-6) else list(verts)
       
        arrow = bool(filled and ring_pts is not None and 3 <= len(ring_pts) <= 5 and not curved
          and max(max(p[0] for p in ring_pts) - min(p[0] for p in ring_pts),
            max(p[1] for p in ring_pts) - min(p[1] for p in ring_pts)) <= ARROW_MAX_PT and not _rect_like(ring_pts))
        
        for k in range(n - 1):
          _add_edge(out, seen, verts[k], verts[k + 1], width, 2 if arrow else flags[k + 1])
        if closed and n >= 3:
          if verts[0] != verts[-1]:
              
            _add_edge(out, seen, verts[-1], verts[0], width, 2 if arrow else 0)
          if len(ring_pts) >= 3 and len(ring_pts) <= MAX_RING_VERTICES and len(out.rings) < MAX_RINGS:
            area = _shoelace(ring_pts)
            xs = [p[0] for p in ring_pts]
            ys = [p[1] for p in ring_pts]
            
            if max(max(xs) - min(xs), max(ys) - min(ys)) >= 0.5:
              out.rings.append(Ring(pts=[(float(p[0]), float(p[1])) for p in ring_pts], area=area,
                bbox=(min(xs), min(ys), max(xs), max(ys)), fill=filled, curved=curved, width=width))
        if len(out.segs) // 5 >= MAX_SEGMENTS:
          stats["segments_truncated"] = True
      if stats.get("segments_truncated"):
        stats["truncated"] = True
        break
    out.words = _text_words(page, stats)
    stats["elapsed_s"] = round(time.monotonic() - started, 3)
    stats["segments"] = len(out.segs) // 5
    stats["rings"] = len(out.rings)
    stats["words"] = len(out.words)
    out.stats = stats
    return out
  finally:
    try:
      page.close()
    except Exception:
      pass

def _add_edge(out: RawPage, seen: set, a, b, width: float, kind: int) -> None:
  if len(out.segs) // 5 >= MAX_SEGMENTS:
    return
  dx, dy = b[0] - a[0], b[1] - a[1]
  if dx * dx + dy * dy < 1e-8:
    return
  ka = (round(a[0] * DEDUP_SCALE), round(a[1] * DEDUP_SCALE))
  kb = (round(b[0] * DEDUP_SCALE), round(b[1] * DEDUP_SCALE))
  key = (ka, kb) if ka <= kb else (kb, ka)
  if key in seen:
    return
  seen.add(key)
  out.segs.extend((a[0], a[1], b[0], b[1], width))
  out.kinds.append(kind)