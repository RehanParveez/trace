from __future__ import annotations
from pydantic import BaseModel, Field

class PreparedOut(BaseModel):
  prepared: dict = Field(description="Trace's own bar bending schedule: sheets in the order a quantity surveyor lays them out, each with its rows, totals per bar size, and the members that could not be worked out.")
  comparison: dict | None = Field(default=None, description="The same schedule set against an audited supplied schedule, row by row with the finding that explains each difference; null without a document_id.")
