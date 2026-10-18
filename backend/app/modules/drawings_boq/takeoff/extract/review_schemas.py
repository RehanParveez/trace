from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID

POLICY_KINDS = ("SLAB_THICKNESS", "BEAM_SECTION", "SOURCE_COUNT")
POLICIES = ("STRUCTURAL", "ARCHITECTURAL", "LARGER", "SMALLER", "AS_READ")

class ConflictSource(BaseModel):
  discipline: str = Field(description="STRUCTURAL, ARCHITECTURAL or UNKNOWN: the kind of sheet that prints this value.")
  page_no: int | None = None
  basis: str

class ConflictValue(BaseModel):
  value_mm: float | None = None
  count: int | None = None
  label: str
  mark: str | None = None
  steel_text: str | None = None
  sources: list[ConflictSource] = Field(default_factory=list)
  quantity: float | None = Field(default=None, description="The quantity this value gives (m3, or nos for a count).")
  governing: bool = False
  delta: float | None = None
  delta_pct: float | None = None

class Conflict(BaseModel):
  id: str
  kind: str
  subject: str
  floor: str | None = None
  attribute: str
  unit: str
  item_ids: list[str]
  decision: str
  used_mm: float | None = None
  page_no: int | None = None
  values: list[ConflictValue]
  governing_index: int | None = Field(default=None, description="Which value is in force: the one chosen, the one the policy picks, or the one the reader used. None when none can be named.")
  governing_by: str | None = Field(default=None, description="CHOSEN, POLICY or AS_READ.")
  policy: str
  spread: float = 0.0
  spread_pct: float = 0.0

class ConflictsResponse(BaseModel):
  drawing_id: UUID
  conflicts: list[Conflict]
  policy: dict[str, str]
  by_kind: dict[str, int]
  undecided: int = 0

class ResolveConflictsRequest(BaseModel):
  policy: dict[str, str] | None = Field(default=None, description="Policy per kind of conflict: STRUCTURAL, ARCHITECTURAL, LARGER, SMALLER or AS_READ.")
  choices: dict[str, float] | None = Field(default=None, max_length=500, description="The value chosen per conflict id: millimetres, or a count for a source count.")
  apply_policy: bool = Field(default=False, description="Write the policy's pick to every open item whose conflict has none chosen.")

class ResolveConflictsResponse(BaseModel):
  resolved: int = 0
  items: list[dict] = Field(default_factory=list)
  skipped: list[dict] = Field(default_factory=list)
  conflicts: ConflictsResponse

class LinkItem(BaseModel):
  id: str
  group: str
  tag: str | None = None
  label: str | None = None
  floor: str | None = None
  decision: str
  status: str
  detail: str | None = None
  how: str | None = None
  needs: list[str] = Field(default_factory=list)
  reason: str | None = None

class LinkGroup(BaseModel):
  group: str
  total: int
  linked: int
  choice: int
  partly: int
  not_linked: int

class LinksResponse(BaseModel):
  drawing_id: UUID
  groups: list[LinkGroup]
  items: list[LinkItem]
  truncated: bool = False
  open: int = 0

class SteelRollupResponse(BaseModel):
  drawing_id: UUID
  ran: bool
  kg: float
  conventions: dict[str, float]
  conventions_assumed: bool
  convention_note: str
  by_family: dict[str, dict]
  by_diameter: dict[str, dict]
  marks: list[dict]
  without_steel: dict
  without_size: int = 0
