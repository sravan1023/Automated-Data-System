"""
AutoDocs AI - S3 Storage Service

Handles file uploads, downloads, and presigned URLs.
"""
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from typing import Optional
import mimetypes

from server.config import settings


def get_s3_client():
    """Get configured S3 client."""
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4"),
    )


async def upload_to_s3(
    content: bytes,
    key: str,
    content_type: Optional[str] = None,
) -> str:
    """
    Upload file content to S3.
    
    Args:
        content: File bytes
        key: S3 object key
        content_type: MIME type (auto-detected if not provided)
    
    Returns:
        S3 URL of uploaded file
    """
    client = get_s3_client()
    
    if not content_type:
        content_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
    
    try:
        client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
        
        return f"s3://{settings.s3_bucket_name}/{key}"
    
    except ClientError as e:
        raise Exception(f"Failed to upload to S3: {e}")


async def download_from_s3(key: str) -> bytes:
    """
    Download file content from S3.
    
    Args:
        key: S3 object key
    
    Returns:
        File bytes
    """
    client = get_s3_client()
    
    try:
        response = client.get_object(
            Bucket=settings.s3_bucket_name,
            Key=key,
        )
        return response["Body"].read()
    
    except ClientError as e:
        raise Exception(f"Failed to download from S3: {e}")


async def delete_from_s3(url: str) -> bool:
    """
    Delete file from S3.
    
    Args:
        url: S3 URL (s3://bucket/key)
    
    Returns:
        True if deleted, False if not found
    """
    client = get_s3_client()
    
    # Parse S3 URL
    if url.startswith("s3://"):
        _, _, bucket_key = url.partition("s3://")
        bucket, _, key = bucket_key.partition("/")
    else:
        key = url
        bucket = settings.s3_bucket_name
    
    try:
        client.delete_object(
            Bucket=bucket,
            Key=key,
        )
        return True
    
    except ClientError:
        return False


async def generate_presigned_url(
    url: str,
    expires_in: int = 3600,
) -> str:
    """
    Generate presigned URL for direct download.
    
    Args:
        url: S3 URL (s3://bucket/key)
        expires_in: URL expiration in seconds
    
    Returns:
        Presigned download URL
    """
    # Use public endpoint for presigned URLs (so browser can access)
    public_endpoint = settings.s3_public_endpoint or settings.s3_endpoint
    
    client = boto3.client(
        "s3",
        endpoint_url=public_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4"),
    )
    
    # Parse S3 URL
    if url.startswith("s3://"):
        _, _, bucket_key = url.partition("s3://")
        bucket, _, key = bucket_key.partition("/")
    else:
        key = url
        bucket = settings.s3_bucket_name
    
    try:
        presigned_url = client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": bucket,
                "Key": key,
            },
            ExpiresIn=expires_in,
        )
        return presigned_url
    
    except ClientError as e:
        raise Exception(f"Failed to generate presigned URL: {e}")


async def list_objects(prefix: str) -> list[dict]:
    """
    List objects with given prefix.
    
    Args:
        prefix: S3 key prefix
    
    Returns:
        List of object metadata dicts
    """
    client = get_s3_client()
    
    try:
        response = client.list_objects_v2(
            Bucket=settings.s3_bucket_name,
            Prefix=prefix,
        )
        
        return [
            {
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"],
            }
            for obj in response.get("Contents", [])
        ]
    
    except ClientError as e:
        raise Exception(f"Failed to list objects: {e}")


def ensure_bucket_exists():
    """Create S3 bucket if it doesn't exist (for development)."""
    client = get_s3_client()
    
    try:
        client.head_bucket(Bucket=settings.s3_bucket_name)
    except ClientError:
        client.create_bucket(Bucket=settings.s3_bucket_name)
