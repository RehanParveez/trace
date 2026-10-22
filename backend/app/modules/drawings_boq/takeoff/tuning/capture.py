from __future__ import annotations
from types import SimpleNamespace
from app.modules.drawings_boq.takeoff.reading_score import labels as L
from app.modules.drawings_boq.takeoff.extract.pipeline import run_extraction
from app.modules.drawings_boq.takeoff.tuning.sweep import Case, SweepSheet
from uuid import UUID
from app.modules.drawings_boq.takeoff.reading_score import reading_score as S
from app.modules.drawings_boq.takeoff.tuning import override as O
from app.modules.drawings_boq.takeoff.reading_score import service as RS

class _Catch:
  def __init__(self):
    self.call = None

  def __call__(self, *args, **kwargs):
    self.call = (args, kwargs)
    return SimpleNamespace(candidates=[])

def reader_for(args: tuple, kwargs: dict):
  def read() -> list:
    res = run_extraction(*args, **kwargs)
    return [u for c in res.candidates for u in L.units_of_candidate(c, ref=c.key)]
  return read

async def capture_case(session, org: UUID, drawing_id: UUID, *, name: str, role: str, rule: S.MatchRule, label_drawing_id: UUID | None = None,
  budget_s: float = 60.0, sheet_ids: set | None = None) -> tuple:
  if not O.is_isolated():
    raise O.NotIsolated("Captured reads are run again with constants set, so this runs only in the sweep tool's own process.")
  svc = RS.ReadingScoreService(session)
  
  await svc._drawing(org, drawing_id)
  label_drawing = label_drawing_id or drawing_id
  if label_drawing != drawing_id:
    await svc._drawing(org, label_drawing)
  rows = await svc.store.labels(org, label_drawing)
  sheets = await svc.core.repo.sheets(org, drawing_id)
  label_sheets = sheets if label_drawing == drawing_id else await svc.core.repo.sheets(org, label_drawing)
  page_of = {s.id: s.page_no for s in label_sheets}
  by_page: dict = {}
  for r in rows:
    by_page.setdefault(page_of.get(r.sheet_id), []).append(RS._label_dict(r))
  case = Case(name=name, role=role, rule=rule, drawing_id=str(drawing_id), label_drawing_id=None if label_drawing == drawing_id else str(label_drawing))
  
  cannot = []
  catch, real = _Catch(), RS.run_extraction
  RS.run_extraction = catch
  
  try:
    for sheet in sheets:
      mine = by_page.get(sheet.page_no)
      if sheet_ids is not None and sheet.id not in sheet_ids:
        continue
      if not mine:
        cannot.append({"page_no": sheet.page_no, "reason": "NO_LABELS", "detail": RS.NOT_JUDGED["NO_LABELS"]})
        continue
      catch.call = None
      try:
        await svc._dry_read(org, sheet, budget_s)
      except RS.Unreadable as e:
        cannot.append({"page_no": sheet.page_no, "reason": e.code, "detail": RS.NOT_JUDGED.get(e.code, e.code)})
        continue
      if catch.call is None:
        cannot.append({"page_no": sheet.page_no, "reason": "READ_FAILED", "detail": RS.NOT_JUDGED["READ_FAILED"]})
        continue
      case.sheets.append(SweepSheet(page_no=sheet.page_no, labels=mine, read=reader_for(*catch.call), title=getattr(sheet, "label", None)))
  finally:
    RS.run_extraction = real
  return case, cannot
