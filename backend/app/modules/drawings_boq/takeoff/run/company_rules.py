from __future__ import annotations
from app.engine.catalogue import methods_qs as MQ
from app.engine.measure import rulebook as RB

def profile_rows(profile_id: str | None) -> list:
  if not profile_id or MQ.profile(profile_id) is None:
    return []
  return [{"id": f"{profile_id}:{r['id']}", "key": r["key"], "scope": dict(r["scope"]), "value": r["value"], "unit": None, "cls": RB.JUDGEMENT, "origin": RB.QS_WORKBOOK, "version": 1, "note": r["note"]}
    for r in MQ.rules(profile_id)]

def rows_of_book(book: dict | None) -> list:
  return [*((book or {}).get("rows") or []), *((book or {}).get("overrides") or [])]
