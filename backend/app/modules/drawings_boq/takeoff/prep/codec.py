from __future__ import annotations
import zlib
import json
import struct
from app.modules.drawings_boq.takeoff.prep.spatial import VectorIndex
from array import array
import sys
from app.modules.drawings_boq.takeoff.prep.extract import Ring, Word

MAGIC = b"TKI1"

def _blob(data: bytes) -> bytes:
  z = zlib.compress(data, 6)
  return struct.pack("<I", len(z)) + z

def encode_index(index: VectorIndex) -> bytes:
  segs = array("f", index.segs)
  if sys.byteorder == "big":
    segs.byteswap()
  rings = [[[round(c, 3) for p in r.pts for c in p], round(r.area, 3), int(r.fill), int(r.curved), round(r.width, 3)] for r in index.rings]
  words = [[w.text, round(w.cx, 3), round(w.cy, 3), round(w.x0, 3), round(w.y0, 3), round(w.x1, 3), round(w.y1, 3), round(w.angle, 2),
            round(w.size, 3), round(w.length, 3), round(w.height, 3)] for w in index.words]
  meta = {"bbox": list(index.bbox)}
  return (MAGIC + _blob(json.dumps(meta).encode()) + _blob(segs.tobytes()) + _blob(bytes(index.kinds))
    + _blob(json.dumps(rings, separators=(",", ":")).encode()) + _blob(json.dumps(words, separators=(",", ":")).encode()))

def decode_index(data: bytes) -> VectorIndex:
  if data[:4] != MAGIC:
    raise ValueError("Unknown takeoff index format.")
  pos = 4
  blobs = []
  for _ in range(5):
    (n,) = struct.unpack_from("<I", data, pos)
    pos += 4
    blobs.append(zlib.decompress(data[pos:pos + n]))
    pos += n
  meta = json.loads(blobs[0])
  segs = array("f")
  segs.frombytes(blobs[1])
  if sys.byteorder == "big":
    segs.byteswap()
  kinds = array("B")
  kinds.frombytes(blobs[2])
  rings = []
  for flat, area, fill, curved, width in json.loads(blobs[3]):
    pts = [(flat[i], flat[i + 1]) for i in range(0, len(flat), 2)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    rings.append(Ring(pts=pts, area=area, bbox=(min(xs), min(ys), max(xs), max(ys)), fill=bool(fill), curved=bool(curved), width=width))
  words = [Word(text=t, x0=x0, y0=y0, x1=x1, y1=y1, angle=ang, size=size, cx=cx, cy=cy, length=length, height=height)
    for t, cx, cy, x0, y0, x1, y1, ang, size, length, height in json.loads(blobs[4])]
  return VectorIndex(segs, kinds, rings, words, tuple(meta["bbox"]))
