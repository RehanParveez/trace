from urllib.parse import urljoin
import boto3
from botocore.client import Config
from app.core.config import settings

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