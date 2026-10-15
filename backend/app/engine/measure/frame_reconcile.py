from __future__ import annotations
import math
from dataclasses import dataclass
from app.engine.measure import frame as FR

MATCHED, UNMATCHED = "MATCHED", "UNMATCHED"

@dataclass(frozen=True)
class Pair:
  pdf: object
  model: object
  distance_mm: float

@dataclass(frozen=True)
class Reconciliation:
  status: str
  grade: str
  method: str
  dx_mm: float
  dy_mm: float
  supporters: int
  compared: int
  pairs: tuple
  pdf_only: tuple
  model_only: tuple
  size_differs: tuple

  @property
  def agrees(self) -> bool:
    return self.status == MATCHED and not self.pdf_only and not self.model_only and not self.size_differs

def reconcile(pdf_points: list, model_points: list, *, offset: tuple | None = None, tol: float = FR.MAX_RESIDUAL_MM, **vote_params) -> Reconciliation:
  """offset is (dx, dy) taking PDF positions onto the model, as a person confirmed it; without it the vote decides. tol is the farthest a pair may be apart."""
  pdf = sorted(pdf_points, key=lambda p: (p.x, p.y))
  model = sorted(model_points, key=lambda p: (p.x, p.y))
  if offset is not None:
    dx, dy, method, grade, support = float(offset[0]), float(offset[1]), "GIVEN", FR.CONFIRMED, 0
  else:
    v = FR.vote_offset(model, pdf, **vote_params) if pdf and model else None
    if v is None:
      return Reconciliation(UNMATCHED, FR.ASSUMED, FR.UNALIGNED, 0.0, 0.0, 0, min(len(pdf), len(model)), (), tuple(p.ref for p in pdf), tuple(p.ref for p in model), ())
    dx, dy, method, grade, support = round(v["dx"], 2), round(v["dy"], 2), FR.COLUMN_MATCH, FR.ASSUMED, v["supporters"]
  pairs = FR._match(model, pdf, dx, dy, tol)
  used_pdf = {i for i, _, _ in pairs}
  used_model = {j for _, j, _ in pairs}
  out = tuple(Pair(pdf[i].ref, model[j].ref, round(d, 2)) for i, j, d in sorted(pairs, key=lambda t: (pdf[t[0]].x, pdf[t[0]].y)))
  left_pdf = [i for i in range(len(pdf)) if i not in used_pdf]
  left_model = [j for j in range(len(model)) if j not in used_model]
  differs, taken = [], set()
  
  for i in left_pdf:
    best = None
    for j in left_model:
      if j in taken:
        continue
      d = math.hypot(model[j].x - (pdf[i].x + dx), model[j].y - (pdf[i].y + dy))
      if d <= tol and (best is None or d < best[0]):
        best = (d, j)
    if best is not None:
      taken.add(best[1])
      differs.append((pdf[i].ref, model[best[1]].ref, pdf[i].size, model[best[1]].size))
  differing_pdf = {r[0] for r in differs}
  differing_model = {r[1] for r in differs}
  return Reconciliation(
    MATCHED, grade, method, dx, dy, support or len(out), min(len(pdf), len(model)), out,
    tuple(pdf[i].ref for i in left_pdf if pdf[i].ref not in differing_pdf), tuple(model[j].ref for j in left_model if model[j].ref not in differing_model), tuple(differs))
