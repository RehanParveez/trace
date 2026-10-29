from __future__ import annotations
import json
from app.modules.drawings_boq.models import Rule, ProjectRuleOverride, CompanyConvention, RuleBook
from app.engine.measure import rulebook as RB
from app.engine.measure import rule_formulas as RF
from app.core.exceptions import TraceException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID, uuid4
from datetime import datetime, timezone
from app.engine.measure import company as CO

BOOK_NAME = "Company rules"
FORMULA_PREFIX = "formula."
DRAFT_PREFIX = "draft:"

def _scope_key(scope) -> str:
  return json.dumps(scope or {}, sort_keys=True)

def row_of(r: Rule) -> dict:
  return {"id": str(r.id), "key": r.key, "scope": dict(r.scope or {}), "value": r.value, "unit": r.unit, "cls": r.cls, "origin": r.origin, "version": r.version}

def override_row(o: ProjectRuleOverride) -> dict:
  return {"id": str(o.id), "key": o.key, "scope": dict(o.scope or {}), "value": o.value, "unit": o.unit, "cls": RB.JUDGEMENT, "origin": RB.PROJECT, "version": 1}

def checked_value(key: str, raw, scope=None):
  if key.startswith("finish."):
    from app.modules.drawings_boq.takeoff.extract import finish_rules as FR
    try:
      return FR.checked(key, scope, raw)
    except ValueError as exc:
      raise TraceException(str(exc), status_code=422, code="FINISH_RULE_REFUSED")
  if key.startswith("stage."):
    from app.engine.measure import stages as STG
    try:
      return STG.checked_rule(key, raw)
    except ValueError as exc:
      raise TraceException(str(exc), status_code=422, code="STAGE_RULE_REFUSED")
  if key.startswith(FORMULA_PREFIX):
    try:
      return RF.checked(raw)
    except ValueError as exc:
      raise TraceException(str(exc), status_code=422, code="RULE_FORMULA_REFUSED")
  from app.modules.drawings_boq import company_conventions as CCV
  return CCV.checked(key, raw)

async def active_book(session: AsyncSession, organization_id: UUID) -> RuleBook | None:
  return (await session.execute(select(RuleBook).where(RuleBook.organization_id == organization_id, RuleBook.is_active.is_(True)))).scalar_one_or_none()

async def rules_of(session: AsyncSession, book_id: UUID, drafts: bool = False) -> list:
  rows = list((await session.execute(select(Rule).where(Rule.book_id == book_id))).scalars().all())
  return rows if drafts else [r for r in rows if not r.key.startswith(DRAFT_PREFIX)]

async def overrides_of(session: AsyncSession, project_id: UUID) -> list:
  return list((await session.execute(select(ProjectRuleOverride).where(ProjectRuleOverride.project_id == project_id))).scalars().all())

async def snapshot(session: AsyncSession, organization_id: UUID, project_id: UUID | None = None) -> dict | None:
  book = await active_book(session, organization_id)
  over = await overrides_of(session, project_id) if project_id else []
  if book is None and not over:
    return None
  rules = sorted((r for r in (await rules_of(session, book.id) if book else []) if r.value is not None), key=lambda r: (r.key, _scope_key(r.scope)))
  return {"book": {"id": str(book.id), "name": book.name, "version": book.version} if book else None, "rows": [row_of(r) for r in rules],
    "overrides": [override_row(o) for o in sorted(over, key=lambda o: (o.key, _scope_key(o.scope)))]}

def _unit_of(key: str) -> str | None:
  from app.engine.measure import readings as QS
  return next((r["unit"] for r in QS.registry() if r["key"] == key), None)

def _same(a, b) -> bool:
  return _scope_key(a) == _scope_key(b) if isinstance(a, (dict, list)) or isinstance(b, (dict, list)) else RB._same(a, b)

async def publish(session: AsyncSession, organization_id: UUID, changes: list, *, note: str | None = None) -> RuleBook:
  old = await active_book(session, organization_id)
  if old is not None:
    old_rules = {(r.key, _scope_key(r.scope)): r for r in await rules_of(session, old.id, drafts=True) if r.value is not None}
    old.is_active = False
    await session.flush()
  else:
    legacy = (await session.execute(select(CompanyConvention).where(CompanyConvention.organization_id == organization_id))).scalars().all()
    old_rules = {(c.key, "{}"): Rule(id=uuid4(), book_id=None, key=c.key, scope={}, value=c.value, unit=c.unit, cls=RB.JUDGEMENT, origin=c.origin, note=c.evidence, version=1) for c in legacy}
  book = RuleBook(id=uuid4(), organization_id=organization_id, name=BOOK_NAME, version=(old.version + 1) if old is not None else 1, is_active=True)
  session.add(book)
  
  await session.flush()
  done: set = set()
  for ch in changes:
    k = (ch["key"], _scope_key(ch.get("scope")))
    prev = old_rules.get(k)
    value = ch.get("value")
    done.add(k)
    if value is None and prev is None:
      continue
    if prev is not None and value is not None and _same(prev.value, value) and (ch.get("origin") or prev.origin) == prev.origin:
      done.discard(k)
      continue
  
    version = (prev.version + 1) if prev is not None else 1
    session.add(Rule(id=uuid4(), book_id=book.id, key=ch["key"], scope=dict(ch.get("scope") or {}), value=value, unit=ch.get("unit") or (prev.unit if prev else _unit_of(ch["key"])),
      cls=ch.get("cls") or (prev.cls if prev else RB.JUDGEMENT), origin=ch.get("origin") or CO.COMPANY, note=ch.get("note") or note, version=version,
      supersedes_id=prev.id if prev is not None and old is not None else None))
  for k, prev in old_rules.items():
    if k in done:
      continue
    session.add(Rule(id=uuid4(), book_id=book.id, key=prev.key, scope=dict(prev.scope or {}), value=prev.value, unit=prev.unit, cls=prev.cls, origin=prev.origin, note=prev.note, version=prev.version,
      supersedes_id=prev.id if old is not None else None))
  await session.flush()
  return book

def scoped_row(o: ProjectRuleOverride) -> dict:
  return {"key": o.key, "scope": dict(o.scope or {}), "value": o.value}

async def set_scoped(session: AsyncSession, project_id: UUID, user_id: UUID | None, items: list, note: str | None) -> list:
  """Set (a value) or clear (None) the scoped rules a project holds: items [{"key", "scope", "value"}], each checked with its scope as the screen checks it. Returns the project's scoped rules after."""
  mine = {(o.key, _scope_key(o.scope)): o for o in await overrides_of(session, project_id)}
  now = datetime.now(timezone.utc)
  
  for it in items:
    key, scope = it["key"], dict(it.get("scope") or {})
    row = mine.get((key, _scope_key(scope)))
    if it.get("value") is None:
      if row is not None:
        await session.delete(row)
        mine.pop((key, _scope_key(scope)))
      continue
    value = checked_value(key, it["value"], scope)
    if row is None:
      row = ProjectRuleOverride(id=uuid4(), project_id=project_id, key=key, scope=scope, value=value, unit=None, note=note, set_by=user_id, set_at=now)
      session.add(row)
      mine[(key, _scope_key(scope))] = row
    else:
      row.value, row.note, row.set_by, row.set_at = value, note or row.note, user_id, now
  await session.flush()
  return [scoped_row(o) for o in sorted(mine.values(), key=lambda o: (o.key, _scope_key(o.scope))) if o.scope or o.key.startswith("finish.")]

async def set_overrides(session: AsyncSession, project_id: UUID, user_id: UUID | None, values: dict, note: str | None) -> None:
  mine = {(o.key, _scope_key(o.scope)): o for o in await overrides_of(session, project_id)}
  now = datetime.now(timezone.utc)
  for key, raw in values.items():
    row = mine.get((key, "{}"))
    
    if raw is None:
      if row is not None:
        await session.delete(row)
      continue
    value = checked_value(key, raw)
    if row is None:
      session.add(ProjectRuleOverride(id=uuid4(), project_id=project_id, key=key, scope={}, value=value, unit=_unit_of(key), note=note, set_by=user_id, set_at=now))
    else:
      row.value, row.unit, row.note, row.set_by, row.set_at = value, _unit_of(key), note or row.note, user_id, now
  await session.flush()
