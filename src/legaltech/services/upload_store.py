"""Evidence document storage.

When DATA_BUCKET is set, files are persisted to S3 under uploads/<file_id>
so they survive restarts and re-deploys.  Falls back to in-memory for dev.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from dataclasses import dataclass, field

_logger = logging.getLogger(__name__)

_TTL_SECONDS = 3600 * 24 * 30  # 30 days (was 1 hour — way too short)

_DATA_BUCKET: str | None = os.getenv("DATA_BUCKET")
_S3_PREFIX = "uploads/"
_s3 = None


def _get_s3():
    global _s3
    if _s3 is None:
        import boto3
        _s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION", "ap-south-1"))
    return _s3


@dataclass
class StoredFile:
    file_id: str
    filename: str
    content_type: str
    data: bytes
    created_at: float = field(default_factory=time.time)

    @property
    def size(self) -> int:
        return len(self.data)

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > _TTL_SECONDS

    def is_image(self) -> bool:
        return self.content_type.startswith("image/")


class UploadStore:
    """File store backed by S3 (prod) or in-memory dict (dev)."""

    def __init__(self) -> None:
        self._files: dict[str, StoredFile] = {}

    # ── public API ───────────────────────────────────────────────────

    def store(self, filename: str, content_type: str, data: bytes) -> StoredFile:
        self._cleanup()
        file_id = uuid.uuid4().hex[:12]
        sf = StoredFile(file_id=file_id, filename=filename, content_type=content_type, data=data)
        self._files[file_id] = sf
        self._put_s3(sf)
        return sf

    def get(self, file_id: str) -> StoredFile | None:
        sf = self._files.get(file_id)
        if sf and sf.is_expired():
            del self._files[file_id]
            return None
        if sf:
            return sf
        # Cache miss — try S3
        return self._fetch_s3(file_id)

    def get_many(self, file_ids: list[str]) -> list[StoredFile]:
        return [sf for fid in file_ids if (sf := self.get(fid)) is not None]

    def delete(self, file_id: str) -> bool:
        removed = self._files.pop(file_id, None) is not None
        self._delete_s3(file_id)
        return removed

    # ── S3 helpers ───────────────────────────────────────────────────

    def _put_s3(self, sf: StoredFile) -> None:
        if not _DATA_BUCKET:
            return
        import json
        try:
            meta = json.dumps({"filename": sf.filename, "content_type": sf.content_type,
                               "created_at": sf.created_at})
            _get_s3().put_object(
                Bucket=_DATA_BUCKET,
                Key=_S3_PREFIX + sf.file_id,
                Body=sf.data,
                ContentType=sf.content_type,
                Metadata={"info": meta},
            )
        except Exception:
            _logger.exception("S3 put failed for upload %s", sf.file_id)

    def _fetch_s3(self, file_id: str) -> StoredFile | None:
        if not _DATA_BUCKET:
            return None
        import json
        try:
            resp = _get_s3().get_object(Bucket=_DATA_BUCKET, Key=_S3_PREFIX + file_id)
            meta = json.loads(resp["Metadata"].get("info", "{}"))
            data = resp["Body"].read()
            sf = StoredFile(
                file_id=file_id,
                filename=meta.get("filename", "file"),
                content_type=meta.get("content_type", resp.get("ContentType", "application/octet-stream")),
                data=data,
                created_at=meta.get("created_at", time.time()),
            )
            self._files[file_id] = sf  # cache locally
            return sf
        except Exception:
            return None

    def _delete_s3(self, file_id: str) -> None:
        if not _DATA_BUCKET:
            return
        try:
            _get_s3().delete_object(Bucket=_DATA_BUCKET, Key=_S3_PREFIX + file_id)
        except Exception:
            pass

    # ── housekeeping ─────────────────────────────────────────────────

    def _cleanup(self) -> None:
        expired = [k for k, v in self._files.items() if v.is_expired()]
        for k in expired:
            del self._files[k]


upload_store = UploadStore()
