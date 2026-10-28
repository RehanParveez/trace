from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Any

class ProjectDrawing(BaseModel):
  drawing_id: UUID
  name: str
  sheets: int = 0
  current: bool = True

class MarkRow(BaseModel):
  mark: str
  category: str = Field(description="COLUMN, FOOTING, BEAM, DOOR, WINDOW, WALL_SECTION, SECTION_REF, SLAB_PANEL or UNKNOWN.")
  basis: str = Field(description="SECTION_TITLE, SCHEDULE, LEGEND, SECTION_SYMBOL, DEFAULT or PERSON.")
  text: str | None = None
  page_no: int | None = None
  drawing_id: str | None = None
  drawing_name: str | None = None
  params: dict[str, Any] = Field(default_factory=dict)
  editable: bool = True
  conflict: dict[str, Any] | None = Field(default=None, description="The weaker reading of the same mark, when the drawings give it two meanings.")

class MarkDiscipline(BaseModel):
  discipline: str
  marks: list[MarkRow]

class ProjectMarksResponse(BaseModel):
  project_id: UUID
  drawings: int = 0
  categories: list[str] = Field(default_factory=list)
  disciplines: list[MarkDiscipline] = Field(default_factory=list)

class SetMarkRequest(BaseModel):
  discipline: str = Field(min_length=1, max_length=40)
  mark: str = Field(min_length=1, max_length=20)
  category: str | None = Field(default=None, description="What the mark is; null takes a person's setting back.")

class ProjectFactsResponse(BaseModel):
  project_id: UUID
  drawings: list[ProjectDrawing]
  facts: dict[str, Any] = Field(description="What the PDFs of the project print, gathered over all of them: storey_heights, slab_values, spec_facts, beam_sections, tank_details, footing_sections, schedule, units. Every item that names pages also has sources: [{drawing_id, page_no}].")
