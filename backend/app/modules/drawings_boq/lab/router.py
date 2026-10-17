from __future__ import annotations
from fastapi import APIRouter, HTTPException, UploadFile, Body, Depends, File, Form
import json
from uuid import UUID
from app.modules.identity.models import User
from app.modules.identity.enums import PermissionKey
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from fastapi.responses import Response
from app.modules.drawings_boq.lab.service import BillCompareService, export_comparison

router = APIRouter(prefix="/drawings-boq", tags=["Drawings & BOQ"])

def _json_field(raw: str | None, what: str) -> dict | None:
  if not raw:
    return None
  try:
    v = json.loads(raw)
  except ValueError:
    raise HTTPException(422, {"code": "BAD_JSON", "message": f"{what} must be valid JSON."})
  if not isinstance(v, dict):
    raise HTTPException(422, {"code": "BAD_JSON", "message": f"{what} must be an object."})
  return v

@router.post("/calculation-runs/{run_id}/compare-bill")
async def compare_bill(
  run_id: UUID,
  file: UploadFile = File(...),
  tolerance_pct: float | None = Form(default=None),
  overrides: str | None = Form(default=None),
  classes: str | None = Form(default=None),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  data = await file.read()
  return await BillCompareService(session).compare_bill(
    current_user.active_membership.organization_id, run_id, data, tolerance_pct,
    _json_field(overrides, "overrides"), _json_field(classes, "classes"))

@router.post("/calculation-runs/{run_id}/compare-steel")
async def compare_steel(
  run_id: UUID,
  file: UploadFile = File(...),
  tolerance_pct: float | None = Form(default=None),
  classes: str | None = Form(default=None),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  data = await file.read()
  return await BillCompareService(session).compare_steel(
    current_user.active_membership.organization_id, run_id, data, tolerance_pct, _json_field(classes, "classes"))

@router.post("/compare-bill/export")
async def export_compare_bill(
  result: dict = Body(...),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
):
  data = export_comparison(result)
  return Response(content=data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    headers={"Content-Disposition": 'attachment; filename="bill-comparison.xlsx"'})
