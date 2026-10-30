from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.prep.details import norm_mark

SIZE_AGREE_MM = 1.0

MARK_WITHOUT_DETAIL = "MARK_WITHOUT_DETAIL"
DETAIL_WITHOUT_MARK = "DETAIL_WITHOUT_MARK"
DETAIL_MARK_CLASH = "DETAIL_MARK_CLASH"
DETAIL_SIZE_UNREAD = "DETAIL_SIZE_UNREAD"

class MarkJoinError(ValueError):
  def __init__(self, issue: dict):
    super().__init__(f"{issue['code']}: {issue['message']}")
    self.issue = issue

def norm(mark) -> str:
  return norm_mark(str(mark or ""))

def _same(a, b) -> bool:
  return all(abs(x - y) <= SIZE_AGREE_MM for x, y in zip(a, b))

def _issue(code: str, mark: str, kind: str, message: str, **extra) -> dict:
  return {"code": code, "mark": mark, "kind": kind, "message": message, **extra}

def sizes(views: list) -> dict:
  by: dict = {}
  for v in views:
    if v.get("size_mm"):
      by.setdefault(norm(v.get("mark")), []).append(v["size_mm"])
  return {m: tuple(ss[0]) for m, ss in by.items() if m and all(_same(ss[0], s) for s in ss[1:])}

def join(layout_marks: dict, views: list, kind: str = "FOOTING", strict: bool = False) -> dict:
  wanted = {norm(m): int(n or 0) for m, n in layout_marks.items() if norm(m)}
  by: dict = {}
  for v in views:
    by.setdefault(norm(v.get("mark")), []).append(v)
  issues: list = []
  joined: dict = {}

  def fail(issue: dict) -> None:
    if strict:
      raise MarkJoinError(issue)
    issues.append(issue)

  for mark in sorted(by, key=lambda m: (re.sub(r"\d+", "", m), int(re.sub(r"\D", "", m) or 0))):
    vs = by[mark]
    sized = [v for v in vs if v.get("size_mm")]
    pages = sorted({v.get("page_no") for v in vs if v.get("page_no") is not None})
    if sized and any(not _same(sized[0]["size_mm"], v["size_mm"]) for v in sized[1:]):
      shown = sorted({" x ".join(f"{x:g}" for x in v["size_mm"]) + " mm" for v in sized})
      fail(_issue(DETAIL_MARK_CLASH, mark, kind, f"{len(vs)} detail views of {kind.lower()} {mark} print different sizes ({'; '.join(shown)}), so none is used.", pages=pages))
      size = None
    else:
      size = list(sized[0]["size_mm"]) if sized else None
    if mark in wanted:
      joined[mark] = {"size_mm": size, "pages": pages, "count": wanted[mark]}
      if size is None and not any(i["code"] == DETAIL_MARK_CLASH and i["mark"] == mark for i in issues):
        fail(_issue(DETAIL_SIZE_UNREAD, mark, kind, f"The view of {kind.lower()} {mark} prints no size that could be read.", pages=pages))
    else:
      fail(_issue(DETAIL_WITHOUT_MARK, mark, kind, f"A detail view is captioned {mark}, and no {kind.lower()} on the layout plans carries that mark.", pages=pages))
  for mark in sorted(wanted):
    if mark not in by:
      joined.setdefault(mark, {"size_mm": None, "pages": [], "count": wanted[mark]})
      fail(_issue(MARK_WITHOUT_DETAIL, mark, kind, f"{kind.title()} {mark} is on the layout plan and no detail view carries that mark.", count=wanted[mark]))
  return {"joined": joined, "issues": issues}
