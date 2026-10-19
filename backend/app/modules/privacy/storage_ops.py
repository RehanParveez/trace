from __future__ import annotations
from uuid import UUID
from collections.abc import Iterator
from app.core.config import settings
from app.shared import storage

EXPORT_FOLDER = "privacy-exports"

def org_prefix(organization_id: UUID) -> str:
  return f"{organization_id}/"

def export_key(organization_id: UUID, job_id: UUID) -> str:
  return f"{organization_id}/{EXPORT_FOLDER}/{job_id}.zip"

def assert_key_in_org(organization_id: UUID, key: str) -> None:
  if not key.startswith(org_prefix(organization_id)) or ".." in key.split("/"):
    raise PermissionError("That file does not belong to this organization.")

class ObjectStore:

  def list_keys(self, prefix: str) -> Iterator[tuple[str, int]]:
    client = storage.get_s3_client()
    
    token = None
    while True:
      args = {"Bucket": settings.minio_bucket, "Prefix": prefix}
      if token:
        args["ContinuationToken"] = token
      page = client.list_objects_v2(**args)
      for item in page.get("Contents", []):
        yield item["Key"], int(item.get("Size", 0))
      if not page.get("IsTruncated"):
        return
      token = page.get("NextContinuationToken")

  def download_to_path(self, key: str, path: str) -> None:
    storage.download_to_path(key, path)

  def upload_path(self, key: str, path: str, content_type: str | None = None) -> None:
    with open(path, "rb") as handle:
      storage.upload_fileobj(key, handle, content_type)

  def delete(self, key: str) -> None:
    storage.delete_object(key)

  def delete_prefix(self, prefix: str) -> int:
    client = storage.get_s3_client()
    removed, batch = 0, []
    for key, _size in self.list_keys(prefix):
      batch.append({"Key": key})
      if len(batch) == 1000:
        client.delete_objects(Bucket=settings.minio_bucket, Delete={"Objects": batch, "Quiet": True})
        removed += len(batch)
        batch = []
        
    if batch:
      client.delete_objects(Bucket=settings.minio_bucket, Delete={"Objects": batch, "Quiet": True})
      removed += len(batch)
    return removed

  def presign(self, key: str, expires_in: int) -> str:
    return storage.generate_presigned_url(key, expires_in=expires_in)

default_store = ObjectStore()
