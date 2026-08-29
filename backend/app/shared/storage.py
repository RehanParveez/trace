from urllib.parse import urljoin
import boto3
from botocore.client import Config
from app.core.config import settings
import uuid
from uuid import UUID

def get_s3_client():
  scheme = "https" if settings.minio_secure else "http"
  endpoint = f"{scheme}://{settings.minio_endpoint}"
  return boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=settings.minio_access_key,
    aws_secret_access_key=settings.minio_secret_key,
    config=Config(signature_version = "s3v4"),
    region_name = "us-east-1",
  )

def ensure_bucket() -> None:
  client = get_s3_client()
  buckets = [item["Name"] for item in client.list_buckets().get("Buckets", [])]
  if settings.minio_bucket not in buckets:
    client.create_bucket(Bucket=settings.minio_bucket)
    
def build_storage_key(organization_id: UUID, project_id: UUID, filename: str) -> str:
  safe_name = filename.replace("/", "_").replace("\\", "_")
  return f"{organization_id}/{project_id}/drawings/{uuid.uuid4().hex}_{safe_name}"

def upload_fileobj(key: str, fileobj, content_type: str | None = None) -> None:
  client = get_s3_client()
  extra_args = {"ContentType": content_type} if content_type else {}
  client.upload_fileobj(fileobj, settings.minio_bucket, key, ExtraArgs=extra_args)

def download_to_path(key: str, destination_path: str) -> None:
  client = get_s3_client()
  client.download_file(settings.minio_bucket, key, destination_path)