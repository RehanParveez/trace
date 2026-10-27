from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Any

class ProjectDrawing(BaseModel):
  drawing_id: UUID
  name: str
  sheets: int = 0
  current: bool = True

class ProjectFactsResponse(BaseModel):
  project_id: UUID
  drawings: list[ProjectDrawing]
  facts: dict[str, Any] = Field(description="What the PDFs of the project print, gathered over all of them: storey_heights, slab_values, spec_facts, beam_sections, tank_details, footing_sections, schedule, units. Every item that names pages also has sources: [{drawing_id, page_no}].")
