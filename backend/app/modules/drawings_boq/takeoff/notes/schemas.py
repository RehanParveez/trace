from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID

class NoteRow(BaseModel):
  kind: str
  text: str | None = None
  pages: list[int] = Field(default_factory=list)
  count: int = 1
  value_mm: float | None = None
  value: float | None = None
  scope: str | None = None
  heading: str | None = None
  fate: str = Field(description="USED, GRADE, CHECKED, LISTED, CONFLICT or NOT_MADE.")
  param: str | None = None
  param_text: str | None = None
  why: str
  layer: str | None = None
  material: str | None = None

class NoteContradiction(BaseModel):
  code: str
  severity: str = Field(description="warning or info.")
  title: str
  message: str
  pages: list[int] = Field(default_factory=list)

class NotesResponse(BaseModel):
  drawing_id: UUID
  sheets_read: int = 0
  sheets_total: int = 0
  rows: list[NoteRow] = Field(default_factory=list)
  contradictions: list[NoteContradiction] = Field(default_factory=list)
  summary: dict = Field(default_factory=dict)
