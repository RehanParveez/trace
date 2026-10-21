from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class LabelSheetRow(BaseModel):
  sheet_id: UUID
  page_no: int
  title: str | None = None
  positive: int = 0
  negative: int = 0
  complete: bool = False
  sources: list[str] = Field(default_factory=list)

class LabelFamilyRow(BaseModel):
  family: str
  positive: int = 0
  negative: int = 0

class LabelsSummaryResponse(BaseModel):
  drawing_id: UUID
  labels: int = 0
  positive: int = 0
  negative: int = 0
  stamp: str | None = None
  sheets: list[LabelSheetRow] = Field(default_factory=list)
  families: list[LabelFamilyRow] = Field(default_factory=list)
  unlabelled_sheets: list[int] = Field(default_factory=list, description="Sheet numbers with no label: a score cannot judge them.")

class LabelTemplateResponse(BaseModel):
  columns: list[str]
  csv: str
  families: list[str]

class DeriveLabelsResponse(BaseModel):
  drawing_id: UUID
  added: int = 0
  updated: int = 0
  unchanged: int = 0
  revoked: int = Field(default=0, description="Labels taken back because the item they came from is no longer accepted or rejected by a person.")
  report: dict = Field(default_factory=dict)
  summary: LabelsSummaryResponse

class ImportLabelsRequest(BaseModel):
  format: str = Field(description="CSV or JSON; the columns are in the template.")
  content: str = Field(min_length=1, max_length=8_000_000)
  replace_imported: bool = Field(default=False, description="Delete the labels imported earlier for this drawing first.")

class ImportLabelsResponse(BaseModel):
  drawing_id: UUID
  added: int = 0
  deleted: int = 0
  sheets: int = 0
  summary: LabelsSummaryResponse

class DeleteLabelsResponse(BaseModel):
  drawing_id: UUID
  deleted: int
  summary: LabelsSummaryResponse

class RunScoreRequest(BaseModel):
  mode: str = Field(default="DRY_RUN", description="DRY_RUN reads the sheets again, without storing anything, and scores that read. STORED scores the candidates now stored; if the labels came from the same register that is circular.")
  rule: dict | None = Field(default=None, description="Match rule values (position_tol_pt, positions, size_tol_pct, size_tol_mm, regression_tol, gate_min_units, max_listed); any left out take the default.")
  sheet_ids: list[UUID] | None = Field(default=None, max_length=500, description="Score only these sheets. The score is then partial and is never used as a baseline.")
  label_drawing_id: UUID | None = Field(default=None, description="Score this drawing against the labels of another drawing (a turned, rescaled or cropped copy of it); sheets are paired by sheet number.")
  budget_seconds: float = Field(default=25.0, ge=5.0, le=120.0, description="Time the reader may take for one sheet.")
  max_total_seconds: float = Field(default=100.0, ge=10.0, le=600.0, description="Time for the whole run; sheets not reached are listed as not judged and the score is partial.")
  note: str | None = Field(default=None, max_length=500)

class ScoreTotals(BaseModel):
  labels: int = 0
  found: int = 0
  tp: int = 0
  fp: int = 0
  fn: int = 0
  precision: float | None = None
  recall: float | None = None
  f1: float | None = None

class ScoreListItem(BaseModel):
  id: UUID
  drawing_id: UUID
  label_drawing_id: UUID | None = None
  created_at: datetime
  mode: str
  status: str
  extract_version: int | None = None
  analysis_version: int | None = None
  label_count: int = 0
  partial: bool = False
  rule_hash: str
  labels_stamp: str
  totals: ScoreTotals
  note: str | None = None

class ScoreListResponse(BaseModel):
  drawing_id: UUID
  current_extract_version: int
  best_id: UUID | None = None
  scores: list[ScoreListItem]

class ScoreResponse(ScoreListItem):
  result: dict
  baseline: dict | None = None

class CompareResponse(BaseModel):
  drawing_id: UUID
  a: ScoreListItem
  b: ScoreListItem
  comparison: dict
