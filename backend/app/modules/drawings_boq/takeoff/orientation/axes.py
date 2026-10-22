from __future__ import annotations
import math

BIN_PER_DEG = 10
BAND_DEG = 1.5
MIN_LEAD = 0.5
SQUARE_DEG = 0.35

def wrap_axis(deg: float) -> float:
  d = (deg + 45.0) % 90.0 - 45.0
  return 45.0 if d == -45.0 else d

def lead(bins: dict, total: float) -> tuple:
  if total <= 0.0 or not bins:
    return 0.0, 0.0

  width, period = int(BAND_DEG * BIN_PER_DEG), 90 * BIN_PER_DEG
  best, best_w = 0, 0.0
  for b in bins:
    w = sum(bins.get((b + d) % period, 0.0) for d in range(-width, width + 1))
    if w > best_w:
      best, best_w = b, w
  return wrap_axis(best / BIN_PER_DEG + 0.5 / BIN_PER_DEG), best_w / total

def add(bins: dict, angle_deg: float, weight: float) -> None:
  b = int((angle_deg % 90.0) * BIN_PER_DEG) % (90 * BIN_PER_DEG)
  bins[b] = bins.get(b, 0.0) + weight

def axes(items) -> float:
  bins: dict = {}
  
  total = 0.0
  for a, w in items:
    if w > 0.0:
      add(bins, a, w)
      total += w
  angle, share = lead(bins, total)
  return 0.0 if share < MIN_LEAD or abs(angle) < SQUARE_DEG else angle

def _bins_of_lines(lines) -> tuple:
  import numpy as np
  if len(lines) == 0:
    return {}, 0.0

  dx, dy = lines[:, 2] - lines[:, 0], lines[:, 3] - lines[:, 1]
  length = np.hypot(dx, dy)
  keep = length > 1e-9
  
  if not keep.any():
    return {}, 0.0
  ang = np.degrees(np.arctan2(dy[keep], dx[keep])) % 90.0
  b = (ang * BIN_PER_DEG).astype(int) % (90 * BIN_PER_DEG)
  hist = np.bincount(b, weights=length[keep], minlength=90 * BIN_PER_DEG)
  return {int(i): float(v) for i, v in enumerate(hist) if v > 0.0}, float(length[keep].sum())

def axes_of_lines(lines) -> float:
  bins, total = _bins_of_lines(lines)
  angle, share = lead(bins, total)
  return 0.0 if share < MIN_LEAD or abs(angle) < SQUARE_DEG else angle

def directions_of_lines(lines, min_share: float = 0.1, most: int = 3) -> list:
  bins, total = _bins_of_lines(lines)
  out = []
  
  period, width = 90 * BIN_PER_DEG, int(BAND_DEG * BIN_PER_DEG)
  for _ in range(most):
    angle, share = lead(bins, total)
    if share < min_share:
      break
    centre = int(round((angle % 90.0) * BIN_PER_DEG - 0.5)) % period
    for d in range(-2 * width, 2 * width + 1):
      bins.pop((centre + d) % period, None)
    if abs(angle) >= SQUARE_DEG:
      out.append(angle)
  return out

def turn(x: float, y: float, deg: float) -> tuple:
  a = math.radians(deg)
  c, s = math.cos(a), math.sin(a)
  return c * x - s * y, s * x + c * y
