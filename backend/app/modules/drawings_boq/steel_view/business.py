from __future__ import annotations
from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.modules.drawings_boq.models import CalculationRun, QuantityLedger, BuildingLevel, DrawingElement
from app.modules.drawings_boq.steel_view import summary as S
from fastapi.responses import Response
from app.modules.identity.models import User
from app.modules.identity.enums import PermissionKey
from sqlalchemy import select
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.core.exceptions import TraceException
from app.modules.drawings_boq.steel_view import allowances as A
from app.modules.drawings_boq.steel_view import export as X

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAX_WASTAGE_PCT = 15.0

class SteelViewService:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def rows(self, org: UUID, run_id: UUID) -> list:
    run = (await self.session.execute(select(CalculationRun.id).where(CalculationRun.id == run_id, CalculationRun.organization_id == org))).scalar_one_or_none()
    if run is None:
      raise TraceException("Calculation run not found.", status_code=404, code="RUN_NOT_FOUND")
    q = (select(QuantityLedger.id, QuantityLedger.formula_code, QuantityLedger.quantity_net, QuantityLedger.trace, QuantityLedger.warnings, BuildingLevel.name, DrawingElement.name)
      .outerjoin(BuildingLevel, BuildingLevel.id == QuantityLedger.level_id)
      .outerjoin(DrawingElement, DrawingElement.id == QuantityLedger.element_id)
      .where(QuantityLedger.run_id == run_id, QuantityLedger.organization_id == org, QuantityLedger.work_item_code == S.STEEL_ITEM, QuantityLedger.formula_code.in_(S.STEEL_FORMULAS)))
    return [{"id": str(i), "formula": formula, "quantity": kg, "trace": trace, "warnings": list(warnings or []), "level": level, "element": element}
      for i, formula, kg, trace, warnings, level, element in (await self.session.execute(q)).all()]

  async def allowance_rows(self, org: UUID, run_id: UUID) -> list:
    q = (select(QuantityLedger.work_item_code, QuantityLedger.quantity_net)
      .where(QuantityLedger.run_id == run_id, QuantityLedger.organization_id == org, QuantityLedger.work_item_code.in_(A.ITEMS)))
    return [{"code": code, "quantity": kg} for code, kg in (await self.session.execute(q)).all()]

  async def summary(self, org: UUID, run_id: UUID, wastage_pct: float | None) -> dict:
    out = S.summarise(await self.rows(org, run_id), wastage_pct, await self.allowance_rows(org, run_id))
    out["run_id"] = str(run_id)
    return out

router = APIRouter(prefix="/drawings-boq", tags=["steel-summary"])

@router.get("/calculation-runs/{run_id}/steel-summary")
async def steel_summary(run_id: UUID, wastage_pct: float | None = Query(default=None, ge=0, le=MAX_WASTAGE_PCT),
    current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  return await SteelViewService(session).summary(current_user.active_membership.organization_id, run_id, wastage_pct)

@router.post("/steel-summary/export")
async def export_steel_summary(result: dict = Body(...), current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ))):
  return Response(content=X.steel_xlsx(result), media_type=XLSX, headers={"Content-Disposition": 'attachment; filename="steel-summary.xlsx"'})
