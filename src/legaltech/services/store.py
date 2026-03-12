"""Lightweight JSON-file store for notices and admin settings.

Stores data under <project_root>/data/. Not a database — this is for
MVP/demo purposes. Replace with Postgres/Mongo in production.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
_NOTICES_FILE = _DATA_DIR / "notices.json"
_LAWYER_FILE = _DATA_DIR / "lawyer.json"


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _write_json(path: Path, data: Any) -> None:
    _ensure_dir()
    path.write_text(json.dumps(data, indent=2, default=str))


# ── Lawyer settings ──────────────────────────────────────────────────

def get_lawyer() -> dict | None:
    _ensure_dir()
    data = _read_json(_LAWYER_FILE)
    return data if data else None


def save_lawyer(data: dict) -> dict:
    _ensure_dir()
    _write_json(_LAWYER_FILE, data)
    return data


# ── Notices ──────────────────────────────────────────────────────────

def save_notice(
    complainant_name: str,
    complainant_email: str,
    company_name: str,
    tier: str,
    legal_notice: str,
    full_result: dict | None = None,
) -> str:
    """Save a generated notice. Returns the notice_id."""
    notices = _read_json(_NOTICES_FILE)
    notice_id = uuid.uuid4().hex[:8]
    notices[notice_id] = {
        "id": notice_id,
        "status": "pending_review" if tier == "lawyer" else "delivered",
        "tier": tier,
        "complainant_name": complainant_name,
        "complainant_email": complainant_email,
        "company_name": company_name,
        "legal_notice": legal_notice,
        "created_at": datetime.utcnow().isoformat(),
        "reviewed_at": None,
        "reviewer_notes": None,
    }
    _write_json(_NOTICES_FILE, notices)
    return notice_id


def get_all_notices() -> list[dict]:
    notices = _read_json(_NOTICES_FILE)
    return sorted(notices.values(), key=lambda n: n.get("created_at", ""), reverse=True)


def get_notice(notice_id: str) -> dict | None:
    notices = _read_json(_NOTICES_FILE)
    return notices.get(notice_id)


def update_notice_status(notice_id: str, status: str, reviewer_notes: str | None = None) -> dict | None:
    notices = _read_json(_NOTICES_FILE)
    if notice_id not in notices:
        return None
    notices[notice_id]["status"] = status
    notices[notice_id]["reviewed_at"] = datetime.utcnow().isoformat()
    if reviewer_notes:
        notices[notice_id]["reviewer_notes"] = reviewer_notes
    _write_json(_NOTICES_FILE, notices)
    return notices[notice_id]
