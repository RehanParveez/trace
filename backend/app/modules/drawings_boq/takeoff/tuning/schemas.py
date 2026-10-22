from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class _Out(BaseModel):
  model_config = ConfigDict(from_attributes=True)

class ParamOut(_Out):
  key: str
  name: str
  rule_id: str
  basis: str = Field(description="TUNED, STANDARD or DEFAULT, as the rule register says.")
  families: list[str] = Field(description="The kinds of member the rule decides. A judgement; a sweep records every kind that moves.")
  unit: str
  kind: str
  lo: float = Field(description="Lowest value a sweep tries.")
  hi: float = Field(description="Highest value a sweep tries.")
  hand: float = Field(description="The value when the register was made.")
  live: float = Field(description="The value the code has now.")
  stage: str = Field(description="READ (inside the sheet reader), GATE (before it) or POLICY (not a reading threshold).")
  status: str = Field(description="SWEEPABLE or NOT_SWEEPABLE.")
  calibratable: bool
  reasons: list[str]
  copies: list[str] = Field(description="Module-level copies of the constant that a sweep sets together with it.")
  files: list[str] = Field(description="Files that read the constant, with the line of the first read.")
  reads: int
  ledgered: bool = Field(description="A calibration is recorded for this constant in the ledger.")

class RuleOut(_Out):
  id: str
  label: str
  basis: str
  codes: list[str]
  params: list[str]
  families: list[str]
  sweepable: int
  calibratable: int

class UnregisteredModule(_Out):
  file: str
  count: int
  names: list[str]

class UnregisteredOut(_Out):
  total: int
  modules: list[UnregisteredModule]

class LedgerOut(_Out):
  entries: list[dict]
  drift: list[str]

class RegistryResponse(_Out):
  extract_version: int
  base_extract_version: int
  rules: list[RuleOut]
  params: list[ParamOut]
  unregistered: UnregisteredOut
  ledger: LedgerOut

class PlanRequest(BaseModel):
  rules: list[str] | None = Field(default=None, max_length=40, description="Rule ids; leave out for every constant a score may calibrate.")
  keys: list[str] | None = Field(default=None, max_length=80)
  ladder: str = Field(default="standard", pattern="^(narrow|standard|wide)$")
  include_unswept: bool = False
  control_seconds: float | None = Field(default=None, ge=0, le=100000, description="Seconds one run of the reader over all the labelled sheets takes, when known, to estimate the time.")
  copies: list[UUID] = Field(default_factory=list, max_length=12, description="Drawings that are perturbed copies of this one.")

class PlanResponse(_Out):
  drawing_id: UUID
  ladder: str
  constants: int
  n_cells: int
  cells: list[dict]
  left_out: list[dict]
  estimate_seconds: float | None
  labels: int
  complete_sheets: int
  warnings: list[str]
  command: str

class SweepItem(_Out):
  id: UUID
  drawing_id: UUID
  created_at: datetime
  extract_version: int
  stale: bool = Field(description="The code's EXTRACT_VERSION is not the one the sweep ran under.")
  ladder: str
  status: str
  constants: int
  cells: int
  changes: int
  label_count: int
  seconds: float
  note: str | None
  counts: dict

class PatchOut(_Out):
  hunks: list[dict]
  version: dict | None
  ledger_json: str | None
  markdown: str

class SweepDetail(SweepItem):
  result: dict
  decisions: dict
  patch: PatchOut

class SweepList(_Out):
  drawing_id: UUID
  current_extract_version: int
  sweeps: list[SweepItem]

class DecideRequest(BaseModel):
  min_gain: float | None = Field(default=None, ge=0, le=1)
  min_labels: int | None = Field(default=None, ge=1, le=100000)
  regression_tol: float | None = Field(default=None, ge=0, le=0.5)
  gate_min_units: int | None = Field(default=None, ge=1, le=10000)

class DecideResponse(_Out):
  sweep_id: UUID
  decisions: dict
  patch: PatchOut

class DeleteSweepResponse(_Out):
  deleted: int
