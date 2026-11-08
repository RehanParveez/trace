from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class ShadowRunRequest(BaseModel):
  mode: str = Field(default="WEAK", description="WEAK reads only the sheets the rules are blind on; ALL reads every sheet, to measure the two readers against each other.")
  limit: int = Field(default=3, ge=1, le=10, description="Most sheets read in one request. Each is one AI request. Call again for the rest; a sheet already read is skipped.")
  task: str = Field(default="SHEET", description="SHEET reads the title block and the page; NOTE_FACT reads the printed notes and specifications of the pages that carry them; SCHEDULE_ROW reads the rows of the column, beam and finish schedules of the pages that carry them; LEGEND_ENTRY reads the symbol rows of the electrical legends, one picture for each row, and in the mode WEAK only the rows the rules could not place.")
  force: bool = Field(default=False, description="Read again a sheet that was already read with this prompt version.")

class ShadowComparison(BaseModel):
  fact_key: str
  rule_value: str | None = None
  ai_value: str | None = None
  agreement: str
  quote: str | None = None
  vote: dict | None = None

class ShadowValidator(BaseModel):
  name: str
  passed: bool
  detail: str

class ShadowReadItem(BaseModel):
  id: UUID
  sheet_id: UUID
  page_no: int
  status: str
  mode: str
  prompt_version: str
  confidence: str | None = None
  comparison: list[ShadowComparison]
  totals: dict[str, int]
  problems: list[str]
  validators: list[ShadowValidator] = []
  model: str | None = None
  error: str | None = None
  created_at: datetime

class ShadowRunResponse(BaseModel):
  drawing_id: UUID
  mode: str
  read: int
  failed: int
  remaining: int
  items: list[ShadowReadItem]

class ShadowCost(BaseModel):
  requests: int = 0
  with_tokens: int = 0
  input_tokens: int = 0
  output_tokens: int = 0
  seconds: float = 0.0
  usd: float = 0.0
  pkr: float = 0.0
  unpriced_models: list[str] = []

class ShadowSummaryResponse(BaseModel):
  drawing_id: UUID
  enabled: bool
  sheets_total: int
  sheets_read: int
  totals: dict[str, int]
  by_fact: dict[str, dict[str, int]]
  items: list[ShadowReadItem]
  note: str
  consent: str = "OFF"
  cost: ShadowCost = ShadowCost()