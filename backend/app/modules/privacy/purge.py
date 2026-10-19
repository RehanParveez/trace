from __future__ import annotations
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.privacy.storage_ops import ObjectStore, default_store, org_prefix
from uuid import UUID
import asyncio
from app.modules.privacy.tables import delete_plan
from sqlalchemy.exc import DBAPIError
from sqlalchemy import text
from app.core.crypto import keyring

logger = logging.getLogger("trace.privacy.purge")

_IDENTITY_STEPS = [
  ("refresh_tokens", "DELETE FROM refresh_tokens WHERE organization_id = :org"),
  ("organization_invitations", "DELETE FROM organization_invitations WHERE organization_id = :org"),
  ("organization_memberships", "DELETE FROM organization_memberships WHERE organization_id = :org"),
  ("users", "DELETE FROM users WHERE organization_id = :org"),
  ("roles", "DELETE FROM roles WHERE organization_id = :org"),
]

class OrgPurger:

  def __init__(self, session: AsyncSession, store: ObjectStore | None = None):
    self.session = session
    self.store = store or default_store

  async def _existing_tables(self) -> set[str]:
    rows = await self.session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"))
    return set(rows.scalars().all())

  async def purge(self, organization_id: UUID) -> dict:
    report: dict = {"files": 0, "rows": 0, "tables": {}}
    report["files"] = await asyncio.to_thread(self.store.delete_prefix, org_prefix(organization_id))

    present = await self._existing_tables()
    pending = [(name, sql) for name, sql in delete_plan() if name in present]
    for attempt in range(4):
      failed = []
      last_error = None
      
      for name, sql in pending:
        try:
          async with self.session.begin_nested():
            res = await self.session.execute(text(sql), {"org": organization_id})
          n = res.rowcount or 0
          if n:
            report["tables"][name] = report["tables"].get(name, 0) + n
            report["rows"] += n
        except DBAPIError as exc:
          failed.append((name, sql))
          last_error = exc
          
      if not failed:
        break
      pending = failed
    else:
      names = ", ".join(n for n, _ in failed)
      raise RuntimeError(f"Could not erase these tables: {names}. Last error: {str(last_error)[:300]}")

    for name, sql in _IDENTITY_STEPS:
      res = await self.session.execute(text(sql), {"org": organization_id})
      n = res.rowcount or 0
      if n:
        report["tables"][name] = n
        report["rows"] += n

    await self.session.execute(text("DELETE FROM organization_keys WHERE organization_id = :org"), {"org": organization_id})
    keyring.forget(organization_id)
    await self.session.execute(text("DELETE FROM organizations WHERE id = :org"), {"org": organization_id})
    await self.session.commit()
    logger.info("organization %s erased: %s rows, %s files", organization_id, report["rows"], report["files"])
    return report