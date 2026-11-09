from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID

class FactIn(BaseModel):
  kind: str = Field(description="TOTAL, COUNT, ROOM_AREA, SLAB_AREA or SCHEDULE.")
  category: str | None = None
  tag: str | None = None
  floor: str | None = None
  count: int | None = Field(default=None, ge=0)
  name: str | None = None
  area_m2: float | None = Field(default=None, gt=0)
  mark: str | None = None
  width_mm: float | None = Field(default=None, gt=0)
  height_mm: float | None = Field(default=None, gt=0)
  tolerance_pct: float | None = Field(default=None, ge=0, le=100)

class FactsCheckRequest(BaseModel):
  facts: list[FactIn] = Field(min_length=1, max_length=200)

class FactResult(BaseModel):
  index: int
  text: str
  status: str = Field(description="PASS (read as you say), FAIL (read, but differently) or MISSING (nothing of the kind was read).")
  expected: object | None = None
  found: object | None = None
  message: str
  pages: list[int] = Field(default_factory=list)

class FactsCheckResponse(BaseModel):
  drawing_id: UUID
  results: list[FactResult]
  passed: int = 0
  failed: int = 0
  missing: int = 0

class TraceRule(BaseModel):
  id: str
  label: str
  basis: str = Field(description="TUNED (thresholds set by looking at one drawing), STANDARD (a standard or common practice) or DEFAULT (a value used because the drawing prints none).")
  items: int = 0
  notes: int = 0
  codes: list[str] = Field(default_factory=list)
  examples: list[str] = Field(default_factory=list)
  thresholds: dict = Field(default_factory=dict)

class TraceScale(BaseModel):
  agreement: str | None = None
  support: int = 0
  trust: float | None = None
  gate: str | None = None
  decided_by: str

class TraceRegion(BaseModel):
  kind: str = Field(description="VIEW, SCHEDULE, LEGEND, NOTES, SECTION_PICTURE or TITLE_BLOCK.")
  box: list[float] = Field(description="x0, y0, x1, y1 in page points of the PDF page.")
  title: str = ""
  confidence: float = 1.0
  source: str = Field(default="", description="The finder that made it.")
  words: int = 0
  text_type: str = Field(default="NONE", description="What the words in it came from: TEXT, OUTLINED, RASTER, MIXED, or NONE when it holds no word.")

class TraceNotRead(BaseModel):
  reason: str = Field(description="OCR_BUDGET (the time for reading ran out) or REGION_LIMIT (more outlined clusters than the page may read).")
  left: int = Field(default=0, description="How many regions were left unread.")
  what: str = ""

class TraceText(BaseModel):
  by_source: dict[str, int] = Field(default_factory=dict, description="Words per source: NATIVE (text layer), OUTLINED_OCR, IMAGE_OCR.")
  low: int = Field(default=0, description="Words whose confidence is below the low-confidence setting.")
  mean_confidence: dict[str, float] = Field(default_factory=dict)
  turned: int = Field(default=0, description="Words read after turning the picture of their letters.")
  stroked: int = Field(default=0, description="Words read from lettering drawn as pen strokes, which has no outline and no text layer.")
  not_read: list[TraceNotRead] = Field(default_factory=list)

class TraceAiTask(BaseModel):
  accepted: int = 0
  review: int = Field(default=0, description="Answers kept for a person to look at: the two readings disagreed, or a check failed.")
  escalated: int = Field(default=0, description="Answers that went once to the stronger model.")
  examples: int = Field(default=0, description="Checked answers from other drawings shown to the model on this sheet.")
  support: dict[str, int] = Field(default_factory=dict, description="Accepted answers by what backed them: TEXT_LAYER, or OCR_AND_GLYPHS (an OCR reading agrees and the ink clusters fit).")

class TraceProposedRefusal(BaseModel):
  kind: str
  why: str

class TraceProposed(BaseModel):
  given: int = 0
  accepted: int = 0
  refused: list[TraceProposedRefusal] = Field(default_factory=list)

class TraceAi(BaseModel):
  tasks: dict[str, TraceAiTask] = Field(default_factory=dict)
  proposed: TraceProposed | None = Field(default=None, description="Boxes a model proposed for schedules and section pictures, and what the page model made of them.")

class TraceSheet(BaseModel):
  sheet_id: UUID
  page_no: int
  scale: TraceScale
  rules: list[TraceRule]
  silent: list[str] = Field(default_factory=list)
  regions: list[TraceRegion] = Field(default_factory=list)
  regions_by_kind: dict[str, int] = Field(default_factory=dict, description="How many regions of each kind were found, callouts included.")
  regions_state: str = Field(default="NOT_READ", description="READ, FAILED or NOT_READ (the sheet was read before regions were found).")
  regions_ms: float | None = None
  text: TraceText | None = Field(default=None, description="Where the sheet's words came from; None for a sheet read before the words layer existed.")
  ai: TraceAi | None = Field(default=None, description="What the AI readers did on the sheet; None when none read it.")

class TraceSummary(BaseModel):
  sheets: int = 0
  tuned_rules_fired: list[str] = Field(default_factory=list)
  default_rules_fired: list[str] = Field(default_factory=list)
  tuned_items: int = 0

class TraceResponse(BaseModel):
  drawing_id: UUID
  sheets: list[TraceSheet]
  summary: TraceSummary