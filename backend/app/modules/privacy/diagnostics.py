from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.modules.privacy.schemas import SupportDiagnosticsResponse
from app.dependencies.tenancy import scope_session_as_support
from sqlalchemy import text
from app.core.exceptions import TraceException
from app.modules.audit.service import AuditLogService
from app.modules.audit.models import AuditEntityType, AuditAction
from app.modules.privacy.tables import export_tables

class SupportDiagnostics:

  def __init__(self, session: AsyncSession):
    self.session = session

  async def summary(self, organization_id: UUID, admin_user_id: UUID, admin_email: str, ip_address: str | None = None) -> SupportDiagnosticsResponse:
    await scope_session_as_support(self.session, organization_id)
    expires = (await self.session.execute(text(
      "SELECT max(expires_at) FROM support_access_grants g WHERE g.organization_id = :org AND g.revoked_at IS NULL AND g.starts_at <= now() AND g.expires_at > now()"),
      {"org": organization_id})).scalar()
    
    active = (await self.session.execute(text("SELECT support_grant_active(:org)"), {"org": organization_id})).scalar()
    if not active:
      await self.session.rollback()
      raise TraceException("This company has not granted support access, or the access has ended.", status_code=403, code="SUPPORT_ACCESS_NOT_GRANTED")

    counts: dict[str, int] = {}
    present = set((await self.session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))).scalars().all())
    for table in export_tables():
      if table.name not in present or table.name in {"support_access_grants", "audit_log"}:
        continue
    
      n = (await self.session.execute(text(f'SELECT count(*) FROM "{table.name}" WHERE organization_id = :org'), {"org": organization_id})).scalar() or 0
      if n:
        counts[table.name] = int(n)
    runs = (await self.session.execute(text(
      "SELECT id, status, error_code, created_at FROM calculation_runs WHERE organization_id = :org AND status = 'FAILED' ORDER BY created_at DESC LIMIT 20"),
      {"org": organization_id})).mappings().all()
    
    exports = (await self.session.execute(text(
      "SELECT id, status, error_code, created_at FROM export_jobs WHERE organization_id = :org AND status = 'FAILED' ORDER BY created_at DESC LIMIT 20"),
      {"org": organization_id})).mappings().all()
    sub = (await self.session.execute(text("SELECT status::text FROM subscriptions WHERE organization_id = :org LIMIT 1"), {"org": organization_id})).scalar()

    await AuditLogService(self.session).log(organization_id, admin_user_id, AuditEntityType.SUPPORT_ACCESS, None, AuditAction.UPDATE,
      f"Vendor support ({admin_email}) viewed the support diagnostics", {"viewed": "diagnostics"}, ip_address, commit=True)
    
    return SupportDiagnosticsResponse(
      organization_id=organization_id, grant_expires_at=expires, subscription_status=sub, table_counts=counts,
      failed_runs=[{"id": str(r["id"]), "status": r["status"], "error_code": r["error_code"], "created_at": r["created_at"].isoformat()} for r in runs],
      failed_exports=[{"id": str(r["id"]), "status": r["status"], "error_code": r["error_code"], "created_at": r["created_at"].isoformat()} for r in exports])