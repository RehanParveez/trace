from __future__ import annotations
from fastapi import APIRouter, Depends
from app.core.exceptions import TraceException
from app.dependencies.permissions import require_permission
from app.engine.catalogue import loader as CL
from app.engine.catalogue import tolerances as TOL
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User

router = APIRouter(prefix="/catalogue", tags=["catalogue"])

@router.get("")
async def list_catalogue(current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ))):
  rows = [i.as_dict() for i in CL.items()]
  return {"count": len(rows), "items": rows}

@router.get("/{item_id}")
async def get_catalogue_item(item_id: str, current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ))):
  item = CL.get(item_id)
  if item is None:
    raise TraceException("Catalogue item not found.", status_code=404, code="CATALOGUE_ITEM_NOT_FOUND")
  return item.as_dict()
