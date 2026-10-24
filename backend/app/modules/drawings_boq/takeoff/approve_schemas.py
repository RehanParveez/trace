from __future__ import annotations
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from app.modules.drawings_boq.takeoff.approve_pick import DEFAULT_BATCH, MAX_BATCH, TYPED_KEYS, ZERO_OK

class ApproveReadyRequest(BaseModel):
  accept_assumed: bool = Field(default=False, description="Also accept items whose size the reader paired, defaulted or found disputed on the drawing. They stay marked as assumed.")
  accept_warned: bool = Field(default=False, description="Also accept items the reader or a check between readers warns about.")
  accept_added: bool = Field(default=False, description="Also accept the items that only the sheet showing every plan has, not the floor's own sheet. Check them on the sheet first.")
  confirm: bool = Field(default=True, description="Confirm the measurements made from accepted items, so the calculation run uses them.")
  dry_run: bool = Field(default=False, description="Only count what would be done. Nothing is changed.")
  batch: int = Field(default=DEFAULT_BATCH, ge=1, le=MAX_BATCH, description="Items accepted in one call. The answer says how many remain.")
  exclude_ids: list[UUID] = Field(default_factory=list, max_length=5000, description="Items to leave out, e.g. the ones an earlier call could not accept.")
  typed: dict[str, Decimal] = Field(default_factory=dict, description="Sizes in millimetres for the whole drawing, used where the drawing does not print one: wall_height_mm, column_height_mm, slab_thickness_mm and the rest.")

  @field_validator("typed")
  @classmethod
  def _known_sizes(cls, value):
    bad = sorted(k for k in value if k not in TYPED_KEYS)
    if bad:
      raise ValueError(f"These are not sizes that can be typed here: {', '.join(bad[:5])}.")
    if any(v < 0 or (v == 0 and k not in ZERO_OK) for k, v in value.items()):
      raise ValueError("Sizes must be more than zero.")
    return value

class ApproveReadyResponse(BaseModel):
  drawing_id: UUID
  dry_run: bool = False
  floors_chosen: list[dict] = Field(default_factory=list)
  floors_pending: int = 0
  would_accept: int = 0
  would_confirm: int | None = None
  accepted: int = 0
  accept_failed: list[dict] = Field(default_factory=list)
  failed_ids: list[str] = Field(default_factory=list)
  failed_by_code: dict[str, int] = Field(default_factory=dict)
  confirmed: int = 0
  confirm_failed: list[dict] = Field(default_factory=list)
  already_decided: int = 0
  skipped_by_reason: dict[str, int] = Field(default_factory=dict)
  remaining: int = 0
  confirmed_total: int = 0
  draft_total: int = 0
