from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID

class AnswerRecord(BaseModel):
  value: str
  by: str | None = None
  at: str | None = None

class QuestionOption(BaseModel):
  value: str
  label: str
  text: str = ""
  is_default: bool = False
  effect: str | None = None

class QuestionDefault(BaseModel):
  value: float | str
  unit: str | None = None
  range: list[float] | None = None
  rule: str | None = None
  source: str | None = None
  switched_on: bool = False

class QuestionItem(BaseModel):
  key: str = Field(description="storeys.ALL.ftf_mm, inputs.<input>, reading.<class>, conflict.<class>.<mark>, method.<id>, choice.<card>, site.<input>, sets.<set> or sheets.<kind>.")
  kind: str = Field(description="INPUT, CONFIRM, CONFLICT, METHOD, SUPPLY, CHOICE or SITE.")
  prompt: str
  why: str
  unit: str | None = None
  default: QuestionDefault | None = None
  options: list[QuestionOption] = Field(default_factory=list)
  blocks: list[str] = Field(default_factory=list, description="Catalogue items that wait on this answer.")
  floors: list[str] = Field(default_factory=list)
  members: int = 0
  money: float | None = Field(default=None, description="Blocked quantity times rate; null when no rates are loaded, and then the order is by item count.")
  state: str = Field(description="OPEN, ANSWERED, or RETIRED (answered and no longer asked; kept).")
  answer: AnswerRecord | None = None

class QuestionsResponse(BaseModel):
  project_id: UUID
  has_ledger: bool = Field(description="False until a first run has stored the project's ledger; then there is nothing to ask.")
  questions: list[QuestionItem]
  open: int = 0
  by_state: dict[str, int] = Field(default_factory=dict)

class AnswerRequest(BaseModel):
  value: str | None = Field(default=None, description="The answer: a number for an input, an option's value otherwise. Null withdraws the answer.")
