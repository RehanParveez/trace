from __future__ import annotations
from uuid import UUID
from pydantic import BaseModel, Field

class TankSizeRequest(BaseModel):
  kind: str = Field(pattern="^(OHWT|UGWT|SEPTIC)$", description="The tank: OHWT, UGWT or SEPTIC.")
  value: str | None = Field(default=None, max_length=80, description="Two sizes in mm (length x width, outside) or four (length x width x height x wall thickness). Empty takes the typed size off again.")

class DrawingPassesResponse(BaseModel):
  drawing_id: UUID
  ran: bool = Field(description="False until a sheet of the drawing has been read.")
  tanks: list[dict] = Field(default_factory=list, description="One record per water tank or septic tank: its sizes, where each size came from, and whether the plan was taken from a sibling tank or a seed.")
  electrical: dict | None = Field(default=None, description="The legend rows of the electrical drawing, how many of each were counted on each plan page, and the reason for every row with none.")
  wall_steel: dict | None = None
  typed: dict = Field(default_factory=dict, description="The tank sizes typed for this drawing, by tank.")
