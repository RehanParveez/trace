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

class CompanyConventionsResponse(BaseModel):
  rows: list[ConventionRow]
  sheets_read: int
  assumed: int = Field(description="Editable conventions the company has set nothing for: the software's own figure is used and shown as assumed.")
  qs_name: str
  qs_answered_on: str

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

  async def view(self, organization_id: UUID) -> CompanyConventionsResponse:
    stored = await self._rows(organization_id)
    stamps = await self._stamps(organization_id)

    out: list = []
    for spec in QS.registry():
      key, default = spec["key"], spec["default"]
      row = stored.get(key) if spec["editable"] else None
      value = row.value if row is not None else default
      origin = (row.origin if row.origin in CO.STORED_ORIGINS else CO.COMPANY) if row is not None else CO.CODE_DEFAULT_ASSUMED
      other = sum(1 for s in stamps if not _same(s.get(key, default), value)) if spec["editable"] else 0
      
      out.append(ConventionRow(**{k: spec[k] for k in ("key", "group", "label", "kind", "unit", "default", "low", "high", "editable", "why_fixed")}, options=spec.get("options", []),
        value=value, origin=origin if spec["editable"] else CO.CODE_DEFAULT_ASSUMED, origin_text=CO.ORIGIN_TEXT[origin if spec["editable"] else CO.CODE_DEFAULT_ASSUMED],
        set_by=str(row.set_by_user_id) if row is not None and row.set_by_user_id else None, set_at=row.set_at if row is not None else None,
        evidence=row.evidence if row is not None else None, sheets_read_with_other_value=other))
    return CompanyConventionsResponse(rows=out, sheets_read=len(stamps), assumed=sum(1 for r in out if r.editable and r.origin == CO.CODE_DEFAULT_ASSUMED),
      qs_name=QS.QS_NAME, qs_answered_on=QS.ANSWERED_ON)

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
    await self.session.commit()
    return await self.view(organization_id)

  async def adopt_qs(self, organization_id: UUID, user_id: UUID | None) -> CompanyConventionsResponse:
    stored = await self._rows(organization_id)
    now = datetime.now(timezone.utc)
    why = f"Taken from the answers of {QS.QS_NAME} ({QS.ANSWERED_ON}) and the figures of his workbook as the software holds them. His workbook file itself was not read."
    for spec in QS.registry():
      if spec["editable"] and spec["key"] not in stored and spec["default"] is not None:
        self.session.add(CompanyConvention(id=uuid4(), organization_id=organization_id, key=spec["key"], value=spec["default"], unit=spec["unit"], origin=CO.QS_WORKBOOK,
          set_by_user_id=user_id, set_at=now, evidence=why))
    await self.session.commit()
    return await self.view(organization_id)
