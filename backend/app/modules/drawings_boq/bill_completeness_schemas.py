from __future__ import annotations
from uuid import UUID
from pydantic import BaseModel

class CompletenessFinding(BaseModel):
  code: str
  severity: str
  title: str
  detail: str
  fix: str | None = None
  operator_note: str | None = None

class CompletenessFamily(BaseModel):
  family: str
  label: str
  present: bool
  rows: int
  codes: list[str]

class CompletenessSkipped(BaseModel):
  stage: str
  reason: str
  lost: str | None = None
  fix: str | None = None
  operator_note: str | None = None

class CompletenessFunnel(BaseModel):
  confirmed: int
  draft: int
  undecided: int

class CompletenessStep(BaseModel):
  step: str
  label: str
  family: str | None = None
  enabled: bool
  ran: bool
  rows: int
  reason: str | None = None
  reason_text: str | None = None
  gap: bool
  fix: str | None = None

class BillCompletenessResponse(BaseModel):
  run_id: UUID
  verdict: str
  ledger_rows: int
  families: list[CompletenessFamily]
  skipped_stages: list[CompletenessSkipped]
  funnel: CompletenessFunnel
  held_by_reason: dict[str, int]
  derived_steps: list[CompletenessStep] = []
  boq_error: str | None = None
  findings: list[CompletenessFinding]
  note: str
