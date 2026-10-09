from urllib.parse import urljoin
import boto3
from botocore.client import Config
from app.core.config import settings
import uuid
from uuid import UUID

MAX_UPLOAD_BYTES = 200 * 1024 * 1024

def format_bytes(value: int | None) -> str:
  if value is None:
    return "unlimited"
  size = float(value)
  for unit in ("B", "KB", "MB", "GB"):
    if size < 1024:
      return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
    size /= 1024
  return f"{size:.1f} TB"

def _build_s3_client(endpoint_host: str, secure: bool):
  scheme = "https" if secure else "http"
  return boto3.client(
    "s3",
    endpoint_url=f"{scheme}://{endpoint_host}",
    aws_access_key_id=settings.minio_access_key,
    aws_secret_access_key=settings.minio_secret_key,
    config=Config(signature_version = "s3v4"),
    region_name = "us-east-1",
  )

def get_s3_client():
  return _build_s3_client(settings.minio_endpoint, settings.minio_secure)

def get_public_s3_client():
  public_host = (settings.minio_public_endpoint or "").strip()
  if not public_host:
    return get_s3_client()
  secure = settings.minio_secure if settings.minio_public_secure is None else settings.minio_public_secure
  return _build_s3_client(public_host, secure)

def ensure_bucket() -> None:
  client = get_s3_client()
  buckets = [item["Name"] for item in client.list_buckets().get("Buckets", [])]
  if settings.minio_bucket not in buckets:
    client.create_bucket(Bucket=settings.minio_bucket)
    
def build_storage_key(organization_id: UUID, project_id: UUID, filename: str) -> str:
  safe_name = filename.replace("/", "_").replace("\\", "_")
  return f"{organization_id}/{project_id}/drawings/{uuid.uuid4().hex}_{safe_name}"

def build_site_photo_storage_key(organization_id: UUID, filename: str, project_id: UUID | None = None,
) -> str:
  safe_name = filename.replace("/", "_").replace("\\", "_")
  folder = str(project_id) if project_id is not None else "unassigned"
  return f"{organization_id}/site-photos/{folder}/{uuid.uuid4().hex}_{safe_name}"

def upload_fileobj(key: str, fileobj, content_type: str | None = None) -> None:
  client = get_s3_client()
  extra_args = {"ContentType": content_type} if content_type else {}
  client.upload_fileobj(fileobj, settings.minio_bucket, key, ExtraArgs=extra_args)

def delete_object(key: str) -> None:
  client = get_s3_client()
  client.delete_object(Bucket=settings.minio_bucket, Key=key)

def download_to_path(key: str, destination_path: str) -> None:
  client = get_s3_client()
  client.download_file(settings.minio_bucket, key, destination_path)
  
def download_bytes(key: str) -> bytes:
  client = get_s3_client()
  response = client.get_object(Bucket=settings.minio_bucket, Key=key)
  return response["Body"].read()
  
def object_exists(key: str) -> bool:
  from botocore.exceptions import ClientError
  client = get_s3_client()
  try:
    client.head_object(Bucket=settings.minio_bucket, Key=key)
    return True
  except ClientError as exc:
    status = str(exc.response.get("Error", {}).get("Code", ""))
    if status in {"404", "NoSuchKey", "NotFound"}:
      return False
    raise

def generate_presigned_url(key: str, expires_in: int | None = None) -> str:
  client = get_public_s3_client()
  if expires_in is None:
    expires_in = settings.site_photo_url_ttl_seconds
  return client.generate_presigned_url(
    "get_object",
    Params={"Bucket": settings.minio_bucket, "Key": key},
    ExpiresIn=expires_in,
  )