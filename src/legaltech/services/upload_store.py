"""Temporary in-memory storage for uploaded evidence documents."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

_TTL_SECONDS = 3600  # 1 hour


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
    """Simple in-memory file store.  Production should use S3."""

    def __init__(self) -> None:
        self._files: dict[str, StoredFile] = {}

    def store(self, filename: str, content_type: str, data: bytes) -> StoredFile:
        self._cleanup()
        file_id = uuid.uuid4().hex[:12]
        sf = StoredFile(file_id=file_id, filename=filename, content_type=content_type, data=data)
        self._files[file_id] = sf
        return sf

    def get(self, file_id: str) -> StoredFile | None:
        sf = self._files.get(file_id)
        if sf and sf.is_expired():
            del self._files[file_id]
            return None
        return sf

    def get_many(self, file_ids: list[str]) -> list[StoredFile]:
        return [sf for fid in file_ids if (sf := self.get(fid)) is not None]

    def delete(self, file_id: str) -> bool:
        return self._files.pop(file_id, None) is not None

    def _cleanup(self) -> None:
        expired = [k for k, v in self._files.items() if v.is_expired()]
        for k in expired:
            del self._files[k]


upload_store = UploadStore()
