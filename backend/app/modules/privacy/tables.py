from __future__ import annotations
from sqlalchemy import Table
from app.core.database import Base

SKIP_EXPORT = {"refresh_tokens", "organization_keys", "data_export_jobs", "organization_deletion_requests"}
IDENTITY_TABLES = {"users", "roles", "organization_memberships", "refresh_tokens", "organization_invitations"}
SECRET_MARKERS = ("password", "hash", "secret", "token")

def load_models() -> None:

  import importlib
  import pkgutil
  import app
  for info in pkgutil.walk_packages(app.__path__, "app."):
    if info.name.endswith(".models"):
      importlib.import_module(info.name)
  importlib.import_module("app.engine.measure.models")

def _org_tables() -> list[Table]:
  load_models()
  return [t for t in Base.metadata.sorted_tables if "organization_id" in t.c]

def export_tables() -> list[Table]:
  return [t for t in _org_tables() if t.name not in SKIP_EXPORT]

def child_tables() -> list[tuple[Table, str, Table]]:
  load_models()
  out = []
  
  for t in Base.metadata.sorted_tables:
    if "organization_id" in t.c or t.name in {"organizations", "permissions", "plans", "platform_admins", "role_permissions", "measurement_conventions"}:
      continue
    for fk in t.foreign_keys:
      parent = fk.column.table
      if "organization_id" in parent.c and parent.name not in IDENTITY_TABLES:
        out.append((t, fk.parent.name, parent))
        break
  return out

def public_columns(table: Table) -> list[str]:
  return [c.name for c in table.c if not any(m in c.name.lower() for m in SECRET_MARKERS)]

def delete_plan() -> list[tuple[str, str]]:
  load_models()
  children = {t.name: (fk, parent) for t, fk, parent in child_tables()}
  plan = []
  
  for t in reversed(Base.metadata.sorted_tables):
    if t.name in IDENTITY_TABLES or t.name in {"organizations", "organization_keys", "organization_deletion_requests"}:
      continue
    if t.name in children:
      fk, parent = children[t.name]
      plan.append((t.name, f'DELETE FROM "{t.name}" WHERE "{fk}" IN (SELECT id FROM "{parent.name}" WHERE organization_id = :org)'))
    elif "organization_id" in t.c:
      plan.append((t.name, f'DELETE FROM "{t.name}" WHERE organization_id = :org'))
  return plan
