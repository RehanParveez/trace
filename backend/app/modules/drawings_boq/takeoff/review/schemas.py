from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID

class ReviewLine(BaseModel):
  element: str
  name: str
  floor: str
  state: str
  quantity: float | None = None
  unit: str | None = None
  range: list[float] | None = None

class ReviewAction(BaseModel):
  action: str = Field(description="accept, correct or reject.")
  value: str | None = Field(default=None, description="The value the action stores when it is fixed; null when the person gives it (correct).")
  choices: list[str] = Field(default_factory=list, description="The values offered for a correction; empty when any value of the right kind is taken.")

class ReviewDecision(BaseModel):
  action: str
  value: str | None = None
  by: str | None = None
  at: str | None = None

class ReviewRow(BaseModel):
  id: str
  key: str = Field(description="The question key of a row that stores an answer, ai.<read>.<n> of an AI read, or fact.<drawing>.<decision> of a figure printed two ways.")
  kind: str = Field(description="AI_CANDIDATE, READING, CONFLICT or QUESTION.")
  item: str
  prompt: str
  floor: str | None = None
  floors: list[str] = Field(default_factory=list)
  page: int | None = None
  pages: list[int] = Field(default_factory=list)
  crop_url: str | None = Field(default=None, description="The crop of the page, under the takeoff routes; null when the row has no mark on a page to show.")
  quote: str | None = None
  source: str = Field(description="PRINTED, AI_READ or ASSUMED.")
  effect_rs: float | None = Field(default=None, description="The quantity on the lines the row changes times their rate; null when no rate is loaded, and then the order is by the number of lines.")
  lines: list[ReviewLine] = Field(default_factory=list)
  unquantified: int = Field(default=0, description="How many of the lines hold no quantity yet.")
  touches: list[str] = Field(default_factory=list, description="The catalogue items the row changes: the ones an action on it re-runs.")
  actions: list[ReviewAction] = Field(default_factory=list)
  reasons: dict[str, list[str]] = Field(default_factory=dict, description="For a row of an AI read: the reasons each action takes, so that a person can say why they corrected or left it out.")
  state: str = Field(description="OPEN or DECIDED.")
  decision: ReviewDecision | None = None
  default: dict | None = None
  unit: str | None = None
  affects: str | None = None
  read_id: str | None = None
  task: str | None = None
  drawing_id: str | None = None
  decision_id: str | None = None

class ReviewResponse(BaseModel):
  project_id: UUID
  has_ledger: bool = Field(description="False until a first run has stored the project's ledger; AI reads and printed conflicts are listed regardless.")
  rows: list[ReviewRow]
  open: int = 0
  by_kind: dict[str, int] = Field(default_factory=dict)
  rates_loaded: bool = False
  item: str | None = Field(default=None, description="The catalogue item the list was narrowed to, when it was.")

class ReviewActionRequest(BaseModel):
  action: str = Field(description="accept, correct, reject, or withdraw to take the decision back.")
  value: str | None = Field(default=None, description="The value of a correction.")
  reason: str | None = Field(default=None, description="Why a read was corrected or left out, one of the short list the action takes (WRONG_NUMBER, WRONG_UNIT, WRONG_NAME, WRONG_FLOOR for a correction; NOT_ON_DRAWING, ALREADY_COUNTED, NOT_FOR_THIS_JOB, DRAWING_IS_WRONG for leaving out; OTHER for either). Never needed. Only the review of an AI read keeps it.")

class ReviewActionResponse(ReviewResponse):
  key: str
  touched: list[str] = Field(default_factory=list, description="The catalogue items whose lines changed because of the action; no others.")
