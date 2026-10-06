from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.standards.service import StandardsService
from app.modules.identity.models import User
from uuid import UUID
from app.modules.identity.enums import PermissionKey
from app.modules.drawings_boq.standards.schemas import (RuleSetCreateRequest, ConventionResponse, FormulaResponse, PublishResponse, RecipeUpsertRequest, RuleSetDetailResponse, RuleSetDraftUpdateRequest, RuleSetResponse, 
  ValidationResponse, WorkItemCreateRequest, WorkItemResponse, WorkItemUpdateRequest,
)
from typing import Any
from datetime import date
from app.engine.measure.formulas import FORMULAS
from app.modules.drawings_boq.standards.finish_validation import finish_options

router = APIRouter()

def _svc(session: AsyncSession) -> StandardsService:
  return StandardsService(session)

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.get("/rule-sets", response_model=list[RuleSetResponse])
async def list_rule_sets(
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _svc(session).list_rule_sets(_org(current_user))

@router.post("/rule-sets", response_model=RuleSetDetailResponse, status_code=201)
async def create_rule_set_draft(
  payload: RuleSetCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.RULESET_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _svc(session).create_draft(_org(current_user), current_user.id, payload)

@router.get("/rule-sets/{rule_set_id}", response_model=RuleSetDetailResponse)
async def get_rule_set(
  rule_set_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _svc(session).get_detail(_org(current_user), rule_set_id)

@router.put("/rule-sets/{rule_set_id}", response_model=RuleSetDetailResponse)
async def update_rule_set_draft(
  rule_set_id: UUID,
  payload: RuleSetDraftUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.RULESET_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _svc(session).update_draft(_org(current_user), current_user.id, rule_set_id, payload)

@router.post("/rule-sets/{rule_set_id}/clone", response_model=RuleSetDetailResponse, status_code=201)
async def clone_rule_set(
  rule_set_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.RULESET_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _svc(session).clone(_org(current_user), current_user.id, rule_set_id)

@router.post("/rule-sets/{rule_set_id}/validate", response_model=ValidationResponse)
async def validate_rule_set(
  rule_set_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.RULESET_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  issues = await _svc(session).validate(_org(current_user), rule_set_id)
  return {"valid": not any(i["severity"] == "error" for i in issues), "issues": issues}

@router.post("/rule-sets/{rule_set_id}/publish", response_model=PublishResponse)
async def publish_rule_set(
  rule_set_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.RULESET_PUBLISH)),
  session: AsyncSession = Depends(get_db),
):
  rule_set, warnings = await _svc(session).publish(_org(current_user), current_user.id, rule_set_id)
  return {"rule_set": rule_set, "warnings": warnings}

@router.post("/rule-sets/{rule_set_id}/recipes", response_model=RuleSetDetailResponse, status_code=201)
async def upsert_recipe(
  rule_set_id: UUID,
  payload: RecipeUpsertRequest,
  current_user: User = Depends(require_permission(PermissionKey.RULESET_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _svc(session).upsert_recipe(_org(current_user), current_user.id, rule_set_id, payload)

@router.delete("/rule-sets/{rule_set_id}/recipes/{recipe_id}", status_code=204)
async def delete_recipe(
  rule_set_id: UUID,
  recipe_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.RULESET_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  await _svc(session).delete_recipe(_org(current_user), current_user.id, rule_set_id, recipe_id)

@router.get("/standards/resolved", response_model=dict[str, Any])
async def get_resolved_standards(
  code: str | None = Query(default=None, max_length=50),
  as_of: date | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  profile = await _svc(session).resolve_profile(_org(current_user), code, as_of)
  return profile.to_dict()

@router.get("/formulas", response_model=list[FormulaResponse])
async def list_formulas(
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
):
  return [
    {"code": f.code, "output_unit": f.output_unit, "description": f.description,
     "input_unit": f.input_unit, "needs_kernel": f.needs_kernel}
    for f in FORMULAS.values()
  ]

@router.get("/conventions", response_model=list[ConventionResponse])
async def list_conventions(
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _svc(session).list_conventions()

@router.get("/work-items", response_model=list[WorkItemResponse])
async def list_work_items(
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _svc(session).list_work_items(_org(current_user))

@router.post("/work-items", response_model=WorkItemResponse, status_code=201)
async def create_work_item(
  payload: WorkItemCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.RULESET_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _svc(session).create_work_item(_org(current_user), current_user.id, payload)

@router.patch("/work-items/{work_item_id}", response_model=WorkItemResponse)
async def update_work_item(
  work_item_id: UUID,
  payload: WorkItemUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.RULESET_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _svc(session).update_work_item(_org(current_user), current_user.id, work_item_id, payload)

@router.get("/finish-options")
async def get_finish_options(current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ))):
  return finish_options()