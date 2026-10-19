from __future__ import annotations
import logging
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from app.modules.privacy.models import ExportStatus, DataExportJob
from decimal import Decimal
import base64
import enum
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.privacy.storage_ops import EXPORT_FOLDER, ObjectStore, default_store, export_key, org_prefix
import tempfile
from sqlalchemy import select
import asyncio
import os
import zipfile
from app.modules.identity.models import Organization
from app.core.config import settings
from app.modules.privacy.tables import child_tables, export_tables, public_columns

logger = logging.getLogger("trace.privacy.export")
_BATCH = 1000

def _json_default(value):
  if isinstance(value, (datetime, date, time)):
    return value.isoformat()
  if isinstance(value, (UUID, Decimal)):
    return str(value)
  if isinstance(value, (bytes, bytearray, memoryview)):
    return {"base64": base64.b64encode(bytes(value)).decode()}
  if isinstance(value, enum.Enum):
    return value.value
  if isinstance(value, (set, frozenset)):
    return sorted(value, key=str)
  return str(value)

def _line(row: dict) -> bytes:
  return (json.dumps(row, default=_json_default, ensure_ascii=False) + "\n").encode("utf-8")

class OrgExporter:

  def __init__(self, session: AsyncSession, store: ObjectStore | None = None):
    self.session = session
    self.store = store or default_store

  async def run(self, job_id: UUID) -> DataExportJob:
    job = (await self.session.execute(select(DataExportJob).where(DataExportJob.id == job_id))).scalar_one()
    org_id = job.organization_id
    try:
      with tempfile.TemporaryDirectory() as tmp:
        zip_path = os.path.join(tmp, "export.zip")
        summary = await self._build(org_id, zip_path, tmp)
        key = export_key(org_id, job.id)
        await asyncio.to_thread(self.store.upload_path, key, zip_path, "application/zip")
        size = os.path.getsize(zip_path)
        
      job.status = ExportStatus.COMPLETED.value
      job.storage_key = key
      job.size_bytes = size
      job.table_count = summary["tables"]
      job.row_count = summary["rows"]
      job.file_count = summary["files"]
      job.error_message = None
      job.finished_at = datetime.now(timezone.utc)
      job.expires_at = job.finished_at + timedelta(hours=int(settings.data_export_retention_hours))
      await self.session.commit()
      
    except Exception as exc:
      logger.exception("data export %s failed", job_id)
      await self.session.rollback()
      job = (await self.session.execute(select(DataExportJob).where(DataExportJob.id == job_id))).scalar_one()
      job.status = ExportStatus.FAILED.value
      job.error_message = str(exc)[:900]
      job.finished_at = datetime.now(timezone.utc)
      await self.session.commit()
    return job

  async def _dump(self, zf: zipfile.ZipFile, name: str, stmt) -> int:
    count, out = 0, None
    
    try:
      stream = await self.session.stream(stmt)
      async for part in stream.partitions(_BATCH):
        for row in part:
          if out is None:
            out = zf.open(f"data/{name}.ndjson", "w", force_zip64=True)
          out.write(_line(dict(row._mapping)))
          count += 1
    finally:
      if out is not None:
        out.close()
    return count

  async def _build(self, org_id: UUID, zip_path: str, tmp: str) -> dict:
    tables_done: dict[str, int] = {}
    files: list[str] = []
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
      org = (await self.session.execute(select(Organization).where(Organization.id == org_id))).scalar_one()
      zf.writestr("data/organization.json", json.dumps({"id": str(org.id), "name": org.name, "slug": org.slug, "currency": org.currency}, ensure_ascii=False))

      for table in export_tables():
        cols = [table.c[name] for name in public_columns(table)]
        count = await self._dump(zf, table.name, select(*cols).where(table.c.organization_id == org_id))
        if count:
          tables_done[table.name] = count
          
      for child, fk, parent in child_tables():
        cols = [child.c[name] for name in public_columns(child)]
        sub = select(parent.c.id).where(parent.c.organization_id == org_id)
        count = await self._dump(zf, child.name, select(*cols).where(child.c[fk].in_(sub)))
        if count:
          tables_done[child.name] = count

      prefix = org_prefix(org_id)
      skip = f"{prefix}{EXPORT_FOLDER}/"
      keys = await asyncio.to_thread(lambda: [(k, s) for k, s in self.store.list_keys(prefix) if not k.startswith(skip)])
      
      for key, _size in keys:
        local = os.path.join(tmp, "dl.bin")
        await asyncio.to_thread(self.store.download_to_path, key, local)
        zf.write(local, arcname="files/" + key[len(prefix):], compress_type=zipfile.ZIP_STORED)
        os.remove(local)
        files.append(key[len(prefix):])

      zf.writestr("manifest.json", json.dumps({
        "organization_id": str(org_id),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "format": "One NDJSON file per table under data/ (one JSON object per line); stored files under files/.",
        "tables": tables_done,
        "files": len(files),
        "left_out": "Passwords, password hashes, sign-in tokens and encryption keys are never exported.",
      }, indent=2, ensure_ascii=False))
    return {"tables": len(tables_done), "rows": sum(tables_done.values()), "files": len(files)}
