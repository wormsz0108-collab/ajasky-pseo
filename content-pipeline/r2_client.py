"""Cloudflare R2 S3-compat 클라이언트.

R2_ACCOUNT_ID + R2_ACCESS_KEY_ID + R2_SECRET_ACCESS_KEY 환경변수 필요.
GitHub Actions에선 secrets로 주입.
"""
from __future__ import annotations

import os
from io import BytesIO

import boto3
from botocore.config import Config


_BUCKET = "ajasky-media"


def _client():
    account_id = os.environ.get("R2_ACCOUNT_ID")
    key_id = os.environ.get("R2_ACCESS_KEY_ID")
    secret = os.environ.get("R2_SECRET_ACCESS_KEY")
    if not (account_id and key_id and secret):
        raise RuntimeError("R2_ACCOUNT_ID / R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY env vars missing")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=key_id,
        aws_secret_access_key=secret,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def get_object(key: str) -> bytes:
    obj = _client().get_object(Bucket=_BUCKET, Key=key)
    return obj["Body"].read()


def put_object(key: str, data: bytes, content_type: str = "image/jpeg") -> None:
    _client().put_object(
        Bucket=_BUCKET,
        Key=key,
        Body=BytesIO(data),
        ContentType=content_type,
        CacheControl="public, max-age=2592000, immutable",
    )
