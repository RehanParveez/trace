from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID, uuid4
from app.modules.drawings_boq.models import CompanyConvention, TakeoffExtraction
from app.engine.measure import readings as QS
from sqlalchemy import delete, select
from app.core.exceptions import TraceException
from app.engine.measure import company as CO
from app.engine.measure import rulebook as RB
from app.modules.drawings_boq import rule_book_service as RBS
from app.modules.projects.repository import ProjectRepository

class ScopedRule(BaseModel):
  scope: dict
  value: object
  cls: str
  origin: str
  version: int
  rule_id: str

class ProjectOverride(BaseModel):
  value: object
  note: str | None = None
  set_at: datetime | None = None

class BookRef(BaseModel):
  id: str
  name: str
  version: int

class ConventionRow(BaseModel):
  key: str
  group: str
  label: str
  kind: str = Field(description="NUMBER, SWITCH (1 or 0) or CHOICE.")
  unit: str | None = None
  default: float | str | None = Field(default=None, description="The figure the software starts from.")
  value: float | str | None = Field(default=None, description="The figure in force for this company.")
  origin: str = Field(description="COMPANY, QS_WORKBOOK or CODE_DEFAULT_ASSUMED.")
  origin_text: str
  low: float
  high: float
  options: list[dict] = Field(default_factory=list)
  editable: bool
  why_fixed: str | None = None
  set_by: str | None = None
  set_at: datetime | None = None
  evidence: str | None = None
  sheets_read_with_other_value: int = Field(default=0, description="Sheets whose last read used another figure than the one in force now.")
  cls: str = Field(default="JUDGEMENT", description="PRINTED, STANDARD or JUDGEMENT.")
  version: int | None = Field(default=None, description="The version of the rule in the company's book; None while the figure is the software's own.")
  rule_id: str | None = None
  scope: dict = Field(default_factory=dict, description="Where the rule applies; {} is everywhere.")
  scoped: list[ScopedRule] = Field(default_factory=list, description="Rules of the same key that apply to a narrower scope.")
  project_override: ProjectOverride | None = Field(default=None, description="The figure the project holds in place of the company's, when a project was asked for.")

class CompanyConventionsResponse(BaseModel):
  rows: list[ConventionRow]
  sheets_read: int
  assumed: int = Field(description="Editable conventions the company has set nothing for: the software's own figure is used and shown as assumed.")
  qs_name: str
  qs_answered_on: str
  book: BookRef | None = Field(default=None, description="The version of the company's rule book in force.")
  project_id: str | None = None

class CompanyConventionsUpdate(BaseModel):
  values: dict[str, float | str | bool | None] = Field(default_factory=dict,
    description="Key to figure. A null figure removes the company's figure, so the software's own applies again and is shown as assumed.")
  evidence: str | None = Field(default=None, max_length=500, description="Why, in a few words: stored with every figure of this save.")

def _same(a, b) -> bool:
  if isinstance(a, str) or isinstance(b, str):
    return str(a) == str(b)
  try:
    return abs(float(a) - float(b)) <= 1e-9
  except (TypeError, ValueError):
    return False

def _spec(key: str) -> dict:
  for row in QS.registry():
    if row["key"] == key:
      return row
  raise TraceException(f"Unknown convention '{key}'.", status_code=422, code="UNKNOWN_COMPANY_CONVENTION")

def checked(key: str, raw):
  spec = _spec(key)
  if not spec["editable"]:
    raise TraceException(f"{spec['label']} cannot be set here. {spec['why_fixed']}", status_code=422, code="COMPANY_CONVENTION_NOT_EDITABLE")
  if spec["kind"] == "CHOICE":
    if str(raw) not in {o["value"] for o in spec["options"]}:
      raise TraceException(f"{spec['label']} must be one of {', '.join(o['value'] for o in spec['options'])}.", status_code=422, code="COMPANY_CONVENTION_OUT_OF_RANGE")
    return str(raw)

  if isinstance(raw, str):
    try:
      raw = float(raw)
    except ValueError:
      raise TraceException(f"{spec['label']} must be a number.", status_code=422, code="COMPANY_CONVENTION_OUT_OF_RANGE")
  if spec["kind"] == "SWITCH":
    if isinstance(raw, bool):
      return 1.0 if raw else 0.0
    if float(raw) not in (0.0, 1.0):
      raise TraceException(f"{spec['label']} is a switch: 1 for yes, 0 for no.", status_code=422, code="COMPANY_CONVENTION_OUT_OF_RANGE")
    return float(raw)
  value = float(raw)
  if value != value or not (spec["low"] <= value <= spec["high"]):
    raise TraceException(f"{spec['label']} must be between {spec['low']:g} and {spec['high']:g} {spec['unit'] or ''}.".replace(" .", "."), status_code=422, code="COMPANY_CONVENTION_OUT_OF_RANGE")
  return value

def _layer(rows) -> dict:
  editable = {r["key"] for r in QS.registry() if r["editable"]}
  return {r.key: {"value": r.value, "origin": r.origin} for r in rows if r.key in editable}

async def in_force(session: AsyncSession, organization_id: UUID) -> dict:
  book = await RBS.active_book(session, organization_id)
  if book is not None:
    editable = {r["key"] for r in QS.registry() if r["editable"]}
    return {r.key: {"value": r.value, "origin": r.origin} for r in await RBS.rules_of(session, book.id) if r.value is not None and not (r.scope or {}) and r.key in editable}
  rows = (await session.execute(select(CompanyConvention).where(CompanyConvention.organization_id == organization_id))).scalars().all()
  return _layer(rows)

class CompanyConventionsService:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def _rows(self, organization_id: UUID) -> dict:
    rows = (await self.session.execute(select(CompanyConvention).where(CompanyConvention.organization_id == organization_id))).scalars().all()
    return {r.key: r for r in rows}

  async def _stamps(self, organization_id: UUID) -> list:
    return [s or {} for (s,) in (await self.session.execute(select(TakeoffExtraction.stats["company"]).where(TakeoffExtraction.organization_id == organization_id))).all()]

  async def view(self, organization_id: UUID, project_id: UUID | None = None) -> CompanyConventionsResponse:
    stored = await self._rows(organization_id)
    stamps = await self._stamps(organization_id)
    book = await RBS.active_book(self.session, organization_id)
    book_rules = await RBS.rules_of(self.session, book.id) if book is not None else []
    base = {r.key: r for r in book_rules if not (r.scope or {}) and r.value is not None}
    
    scoped: dict = {}
    for r in book_rules:
      if (r.scope or {}) and r.value is not None:
        scoped.setdefault(r.key, []).append(ScopedRule(scope=dict(r.scope), value=r.value, cls=r.cls, origin=r.origin, version=r.version, rule_id=str(r.id)))
    over = {o.key: o for o in await RBS.overrides_of(self.session, project_id) if not (o.scope or {})} if project_id else {}

    out: list = []
    for spec in QS.registry():
      key, default = spec["key"], spec["default"]
      row = stored.get(key) if spec["editable"] else None
      brow = base.get(key) if spec["editable"] else None
      value = brow.value if brow is not None else (row.value if row is not None else default)
      held_origin = brow.origin if brow is not None else (row.origin if row is not None else None)
      origin = (held_origin if held_origin in CO.STORED_ORIGINS else CO.COMPANY) if held_origin is not None else CO.CODE_DEFAULT_ASSUMED
      other = sum(1 for s in stamps if not _same(s.get(key, default), value)) if spec["editable"] else 0
      seed = RB.SEED.get(key)
      o = over.get(key)
      
      out.append(ConventionRow(**{k: spec[k] for k in ("key", "group", "label", "kind", "unit", "default", "low", "high", "editable", "why_fixed")}, options=spec.get("options", []),
        value=value, origin=origin if spec["editable"] else CO.CODE_DEFAULT_ASSUMED, origin_text=CO.ORIGIN_TEXT[origin if spec["editable"] else CO.CODE_DEFAULT_ASSUMED],
        set_by=str(row.set_by_user_id) if row is not None and row.set_by_user_id else None, set_at=row.set_at if row is not None else None,
        evidence=row.evidence if row is not None else (brow.note if brow is not None else None), sheets_read_with_other_value=other,
        cls=brow.cls if brow is not None else (seed.cls if seed is not None else RB.JUDGEMENT), version=brow.version if brow is not None else None,
        rule_id=str(brow.id) if brow is not None else None, scope={}, scoped=scoped.get(key, []),
        project_override=ProjectOverride(value=o.value, note=o.note, set_at=o.set_at) if o is not None else None))
      
    return CompanyConventionsResponse(rows=out, sheets_read=len(stamps), assumed=sum(1 for r in out if r.editable and r.origin == CO.CODE_DEFAULT_ASSUMED),
      qs_name=QS.qs()["name"], qs_answered_on=QS.qs()["answered_on"], book=BookRef(id=str(book.id), name=book.name, version=book.version) if book is not None else None, project_id=str(project_id) if project_id else None)

  async def update(self, organization_id: UUID, user_id: UUID | None, payload: CompanyConventionsUpdate) -> CompanyConventionsResponse:
    todo = {key: (None if raw is None else checked(key, raw)) for key, raw in payload.values.items()}
    stored = await self._rows(organization_id)
    now = datetime.now(timezone.utc)
    for key, value in todo.items():
      if value is None:
        if key in stored:
          await self.session.execute(delete(CompanyConvention).where(CompanyConvention.organization_id == organization_id, CompanyConvention.key == key))
        continue

      row = stored.get(key)
      if row is None:
        self.session.add(CompanyConvention(id=uuid4(), organization_id=organization_id, key=key, value=value, unit=_spec(key)["unit"], origin=CO.COMPANY,
          set_by_user_id=user_id, set_at=now, evidence=payload.evidence))
      elif not _same(row.value, value) or row.origin != CO.COMPANY or payload.evidence:
        row.value, row.origin, row.set_by_user_id, row.set_at = value, CO.COMPANY, user_id, now
        row.evidence = payload.evidence or row.evidence
    await self.session.flush()
    await RBS.publish(self.session, organization_id, [{"key": key, "scope": {}, "value": value, "origin": CO.COMPANY, "unit": _spec(key)["unit"]} for key, value in todo.items()], note=payload.evidence)
    await self.session.commit()
    return await self.view(organization_id)

  async def update_project(self, organization_id: UUID, user_id: UUID | None, project_id: UUID, values: dict, note: str | None) -> CompanyConventionsResponse:
    """Set or clear the rules of one project (a figure the project holds in place of the company's)."""
    if await ProjectRepository(self.session).get_by_id_and_org(project_id, organization_id) is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")
    await RBS.set_overrides(self.session, project_id, user_id, {key: (None if raw is None else raw) for key, raw in values.items()}, note)
    await self.session.commit()
    return await self.view(organization_id, project_id)

  async def adopt_qs(self, organization_id: UUID, user_id: UUID | None) -> CompanyConventionsResponse:
    stored = await self._rows(organization_id)
    now = datetime.now(timezone.utc)
    why = f"Taken from the answers of {QS.qs()['name']} ({QS.qs()['answered_on']}) and the figures of his workbook as the software holds them. His workbook file itself was not read."
    added = []
    for spec in QS.registry():
      if spec["editable"] and spec["key"] not in stored and spec["default"] is not None:
        self.session.add(CompanyConvention(id=uuid4(), organization_id=organization_id, key=spec["key"], value=spec["default"], unit=spec["unit"], origin=CO.QS_WORKBOOK,
          set_by_user_id=user_id, set_at=now, evidence=why))
        added.append({"key": spec["key"], "scope": {}, "value": spec["default"], "origin": CO.QS_WORKBOOK, "unit": spec["unit"]})
    await self.session.flush()
    await RBS.publish(self.session, organization_id, added, note=why)
    await self.session.commit()
    return await self.view(organization_id)
