"""Настройка MEDIA: локально, Railway Volume или S3-совместимое хранилище."""
from __future__ import annotations

import os
from pathlib import Path


def _get(settings, key, default=None):
    if isinstance(settings, dict):
        return settings.get(key, default)
    return getattr(settings, key, default)


def _set(settings, key, value):
    if isinstance(settings, dict):
        settings[key] = value
    else:
        setattr(settings, key, value)


def configure_media(settings) -> None:
    base_dir = Path(_get(settings, "BASE_DIR"))

    bucket = os.environ.get("AWS_STORAGE_BUCKET_NAME", "").strip()
    _set(settings, "USE_S3_MEDIA", bool(bucket))

    if _get(settings, "USE_S3_MEDIA"):
        installed = list(_get(settings, "INSTALLED_APPS"))
        if "storages" not in installed:
            _set(settings, "INSTALLED_APPS", [*installed, "storages"])

        region = os.environ.get("AWS_S3_REGION_NAME", "us-east-1")
        endpoint = os.environ.get("AWS_S3_ENDPOINT_URL", "").strip() or None
        custom_domain = os.environ.get("AWS_S3_CUSTOM_DOMAIN", "").strip() or None

        _set(settings, "AWS_STORAGE_BUCKET_NAME", bucket)
        _set(settings, "AWS_ACCESS_KEY_ID", os.environ.get("AWS_ACCESS_KEY_ID", ""))
        _set(settings, "AWS_SECRET_ACCESS_KEY", os.environ.get("AWS_SECRET_ACCESS_KEY", ""))
        _set(settings, "AWS_S3_REGION_NAME", region)
        _set(settings, "AWS_S3_ENDPOINT_URL", endpoint)
        _set(settings, "AWS_S3_CUSTOM_DOMAIN", custom_domain)
        _set(settings, "AWS_DEFAULT_ACL", None)
        _set(settings, "AWS_QUERYSTRING_AUTH", False)
        _set(settings, "AWS_S3_FILE_OVERWRITE", False)
        _set(settings, "AWS_S3_OBJECT_PARAMETERS", {"CacheControl": "max-age=86400"})

        s3_options = {
            "bucket_name": bucket,
            "region_name": region,
            "file_overwrite": False,
            "default_acl": None,
            "querystring_auth": False,
        }
        if endpoint:
            s3_options["endpoint_url"] = endpoint
        if custom_domain:
            s3_options["custom_domain"] = custom_domain

        storages = dict(_get(settings, "STORAGES"))
        storages["default"] = {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": s3_options,
        }
        _set(settings, "STORAGES", storages)

        if custom_domain:
            _set(settings, "MEDIA_URL", f"https://{custom_domain}/")
        elif endpoint:
            _set(settings, "MEDIA_URL", f"{endpoint.rstrip('/')}/{bucket}/")
        else:
            _set(settings, "MEDIA_URL", f"https://{bucket}.s3.{region}.amazonaws.com/")
        return

    media_root = os.environ.get("MEDIA_ROOT", "").strip()
    if not media_root and (
        os.environ.get("RAILWAY_PROJECT_ID")
        or os.environ.get("RAILWAY_ENVIRONMENT")
        or os.environ.get("RAILWAY_ENVIRONMENT_NAME")
    ):
        media_root = "/data/media"

    media_path = Path(media_root) if media_root else base_dir / "media"
    media_path.mkdir(parents=True, exist_ok=True)
    _set(settings, "MEDIA_ROOT", media_path)
    _set(settings, "MEDIA_URL", "/media/")
