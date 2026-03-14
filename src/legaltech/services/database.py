"""SQLite database for persisting users, notices, analysis outputs, and activity.

Uses aiosqlite for async access. The DB file is stored at <project_root>/data/lawly.db.
All existing JSON-file store functionality is preserved — this adds structured persistence
for the full pipeline output including all interim model results.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
_DB_PATH = _DATA_DIR / "lawly.db"

_db: aiosqlite.Connection | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_db() -> aiosqlite.Connection:
    """Return the singleton DB connection, creating tables on first call."""
    global _db
    if _db is None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(str(_DB_PATH))
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
        await _init_tables(_db)
    return _db


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None


# ── Schema ───────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    full_name     TEXT NOT NULL,
    email         TEXT NOT NULL,
    phone         TEXT,
    address       TEXT,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

CREATE TABLE IF NOT EXISTS analyses (
    id                  TEXT PRIMARY KEY,
    user_id             TEXT REFERENCES users(id),
    complaint_json      TEXT NOT NULL,
    case_strength       TEXT,
    case_strength_reasoning TEXT,
    ready_to_generate   INTEGER,
    questions_json      TEXT,
    company_name_found  TEXT,
    company_domain      TEXT,
    contacts_found_json TEXT,
    respondent_cin      TEXT,
    respondent_name     TEXT,
    respondent_office   TEXT,
    grievance_email     TEXT,
    policies_found_json TEXT,
    created_at          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notices (
    id                  TEXT PRIMARY KEY,
    user_id             TEXT REFERENCES users(id),
    analysis_id         TEXT REFERENCES analyses(id),
    company_name        TEXT,
    tier                TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'pending_review',
    legal_notice_text   TEXT,
    pdf_stored          INTEGER DEFAULT 0,
    created_at          TEXT NOT NULL,
    reviewed_at         TEXT,
    reviewer_notes      TEXT,

    -- Complaint snapshot
    complaint_json      TEXT,

    -- Company & contacts
    company_json        TEXT,
    contacts_json       TEXT,

    -- Interim model outputs (structured JSON)
    bare_act_refs_json          TEXT,
    claim_elements_json         TEXT,
    respondent_identity_json    TEXT,
    evidence_score_json         TEXT,
    limitation_json             TEXT,
    arbitration_json            TEXT,
    jurisdiction_json           TEXT,
    cure_period_json            TEXT,
    tc_counters_json            TEXT,
    policy_evidence_json        TEXT,
    escalation_json             TEXT,

    -- Delivery
    delivery_json       TEXT,

    -- Customer controls
    customer_controls_json TEXT,

    -- Follow-up answers snapshot
    follow_up_answers_json TEXT,

    -- Full packet (fallback blob for anything not captured above)
    full_packet_json    TEXT,

    generated_at        TEXT
);
CREATE INDEX IF NOT EXISTS idx_notices_user ON notices(user_id);
CREATE INDEX IF NOT EXISTS idx_notices_status ON notices(status);
CREATE INDEX IF NOT EXISTS idx_notices_created ON notices(created_at);

CREATE TABLE IF NOT EXISTS documents (
    id              TEXT PRIMARY KEY,
    notice_id       TEXT REFERENCES notices(id),
    user_id         TEXT REFERENCES users(id),
    filename        TEXT,
    content_type    TEXT,
    size_bytes      INTEGER,
    uploaded_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS generated_pdfs (
    id              TEXT PRIMARY KEY,
    notice_id       TEXT REFERENCES notices(id) UNIQUE,
    filename        TEXT,
    content_type    TEXT DEFAULT 'application/pdf',
    size_bytes      INTEGER,
    pdf_data        BLOB,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_genpdf_notice ON generated_pdfs(notice_id);

CREATE TABLE IF NOT EXISTS activity_log (
    id          TEXT PRIMARY KEY,
    action      TEXT NOT NULL,
    details     TEXT,
    entity_type TEXT,
    entity_id   TEXT,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_log(created_at);
"""


async def _init_tables(db: aiosqlite.Connection) -> None:
    await db.executescript(_SCHEMA)
    # Migration: add generated_pdfs table if upgrading from old schema
    # (handled by CREATE TABLE IF NOT EXISTS in _SCHEMA)
    await db.commit()


# ── Users ────────────────────────────────────────────────────────────

async def upsert_user(full_name: str, email: str, phone: str | None = None, address: str | None = None) -> str:
    """Create user if email doesn't exist, else update name/phone/address. Returns user_id."""
    db = await get_db()
    row = await (await db.execute("SELECT id FROM users WHERE email = ?", (email,))).fetchone()
    if row:
        user_id = row["id"]
        await db.execute(
            "UPDATE users SET full_name=?, phone=?, address=? WHERE id=?",
            (full_name, phone, address, user_id),
        )
        await db.commit()
        return user_id
    user_id = uuid.uuid4().hex[:12]
    await db.execute(
        "INSERT INTO users (id, full_name, email, phone, address, created_at) VALUES (?,?,?,?,?,?)",
        (user_id, full_name, email, phone, address, _now()),
    )
    await db.commit()
    return user_id


async def get_user(user_id: str) -> dict | None:
    db = await get_db()
    row = await (await db.execute("SELECT * FROM users WHERE id=?", (user_id,))).fetchone()
    return dict(row) if row else None


async def get_user_by_email(email: str) -> dict | None:
    db = await get_db()
    row = await (await db.execute("SELECT * FROM users WHERE email=?", (email,))).fetchone()
    return dict(row) if row else None


async def get_all_users(limit: int = 100, offset: int = 0) -> list[dict]:
    db = await get_db()
    rows = await (await db.execute(
        "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)
    )).fetchall()
    return [dict(r) for r in rows]


# ── Analyses (Phase 1 results) ──────────────────────────────────────

async def save_analysis(
    user_id: str | None,
    complaint: dict,
    result: dict,
) -> str:
    """Persist a Phase 1 /notice/analyze result."""
    db = await get_db()
    aid = uuid.uuid4().hex[:12]
    await db.execute(
        """INSERT INTO analyses
           (id, user_id, complaint_json, case_strength, case_strength_reasoning,
            ready_to_generate, questions_json, company_name_found, company_domain,
            contacts_found_json, respondent_cin, respondent_name, respondent_office,
            grievance_email, policies_found_json, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            aid,
            user_id,
            json.dumps(complaint, default=str),
            result.get("case_strength"),
            result.get("case_strength_reasoning"),
            1 if result.get("ready_to_generate") else 0,
            json.dumps(result.get("questions", []), default=str),
            result.get("company_name_found"),
            result.get("company_domain"),
            json.dumps(result.get("contacts_found", []), default=str),
            result.get("respondent_cin"),
            result.get("respondent_registered_name"),
            result.get("respondent_registered_office"),
            result.get("grievance_officer_email"),
            json.dumps(result.get("policies_found", []), default=str),
            _now(),
        ),
    )
    await db.commit()
    return aid


# ── Notices (Phase 2 — full generation) ─────────────────────────────

async def save_notice_full(
    user_id: str,
    company_name: str,
    tier: str,
    packet: dict,
    customer_controls: dict | None = None,
    follow_up_answers: dict | None = None,
    analysis_id: str | None = None,
) -> str:
    """Persist a full NoticePacket with every interim model output."""
    db = await get_db()
    nid = uuid.uuid4().hex[:12]
    status = "pending_review" if tier == "lawyer" else "delivered"

    await db.execute(
        """INSERT INTO notices
           (id, user_id, analysis_id, company_name, tier, status,
            legal_notice_text, complaint_json, company_json, contacts_json,
            bare_act_refs_json, claim_elements_json, respondent_identity_json,
            evidence_score_json, limitation_json, arbitration_json,
            jurisdiction_json, cure_period_json, tc_counters_json,
            policy_evidence_json, delivery_json,
            customer_controls_json, follow_up_answers_json,
            full_packet_json, created_at, generated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            nid,
            user_id,
            analysis_id,
            company_name,
            tier,
            status,
            packet.get("legal_notice"),
            _j(packet.get("complaint")),
            _j(packet.get("company")),
            _j(packet.get("contacts")),
            _j(packet.get("bare_act_references")),
            _j(packet.get("claim_element_results")),
            _j(packet.get("respondent_identity")),
            _j(packet.get("evidence_score")),
            _j(packet.get("limitation_info")),
            _j(packet.get("arbitration_info")),
            _j(packet.get("jurisdiction_info")),
            _j(packet.get("cure_period_info")),
            _j(packet.get("tc_counters")),
            _j(packet.get("policy_evidence")),
            _j(packet.get("delivery")),
            _j(customer_controls),
            _j(follow_up_answers),
            _j(packet),
            _now(),
            packet.get("generated_at"),
        ),
    )
    await db.commit()
    return nid


async def get_notice_db(notice_id: str) -> dict | None:
    db = await get_db()
    row = await (await db.execute("SELECT * FROM notices WHERE id=?", (notice_id,))).fetchone()
    return _unpack_notice(row) if row else None


async def get_all_notices_db(limit: int = 100, offset: int = 0) -> list[dict]:
    db = await get_db()
    rows = await (await db.execute(
        "SELECT * FROM notices ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)
    )).fetchall()
    # Check which notices have stored PDFs
    notice_ids = [r["id"] for r in rows]
    pdf_ids: set[str] = set()
    if notice_ids:
        placeholders = ",".join("?" * len(notice_ids))
        pdf_rows = await (await db.execute(
            f"SELECT notice_id FROM generated_pdfs WHERE notice_id IN ({placeholders})", notice_ids
        )).fetchall()
        pdf_ids = {r["notice_id"] for r in pdf_rows}
    results = []
    for r in rows:
        d = _unpack_notice(r)
        d["has_pdf"] = d["id"] in pdf_ids
        results.append(d)
    return results


async def get_user_notices(user_id: str) -> list[dict]:
    db = await get_db()
    rows = await (await db.execute(
        "SELECT * FROM notices WHERE user_id=? ORDER BY created_at DESC", (user_id,)
    )).fetchall()
    return [_unpack_notice(r) for r in rows]


async def update_notice_status_db(notice_id: str, status: str, reviewer_notes: str | None = None) -> dict | None:
    db = await get_db()
    row = await (await db.execute("SELECT id FROM notices WHERE id=?", (notice_id,))).fetchone()
    if not row:
        return None
    await db.execute(
        "UPDATE notices SET status=?, reviewed_at=?, reviewer_notes=? WHERE id=?",
        (status, _now(), reviewer_notes, notice_id),
    )
    await db.commit()
    return await get_notice_db(notice_id)


# ── Documents ────────────────────────────────────────────────────────

async def save_document(
    notice_id: str | None, user_id: str | None,
    filename: str, content_type: str, size_bytes: int,
) -> str:
    db = await get_db()
    doc_id = uuid.uuid4().hex[:12]
    await db.execute(
        "INSERT INTO documents (id, notice_id, user_id, filename, content_type, size_bytes, uploaded_at) VALUES (?,?,?,?,?,?,?)",
        (doc_id, notice_id, user_id, filename, content_type, size_bytes, _now()),
    )
    await db.commit()
    return doc_id


# ── Generated PDFs ───────────────────────────────────────────────────

async def store_pdf(notice_id: str, pdf_bytes: bytes, filename: str = "Legal_Notice.pdf") -> str:
    """Store a generated PDF blob linked to a notice."""
    db = await get_db()
    pid = uuid.uuid4().hex[:12]
    # Upsert: replace if PDF already exists for this notice
    await db.execute(
        "DELETE FROM generated_pdfs WHERE notice_id=?", (notice_id,)
    )
    await db.execute(
        "INSERT INTO generated_pdfs (id, notice_id, filename, size_bytes, pdf_data, created_at) VALUES (?,?,?,?,?,?)",
        (pid, notice_id, filename, len(pdf_bytes), pdf_bytes, _now()),
    )
    await db.execute(
        "UPDATE notices SET pdf_stored=1 WHERE id=?", (notice_id,),
    )
    await db.commit()
    return pid


async def get_pdf(notice_id: str) -> tuple[bytes, str] | None:
    """Return (pdf_bytes, filename) for a notice, or None."""
    db = await get_db()
    row = await (await db.execute(
        "SELECT pdf_data, filename FROM generated_pdfs WHERE notice_id=?", (notice_id,)
    )).fetchone()
    if row and row["pdf_data"]:
        return bytes(row["pdf_data"]), row["filename"] or "Legal_Notice.pdf"
    return None


async def get_all_pdfs_meta(limit: int = 100, offset: int = 0) -> list[dict]:
    """Return metadata (no blob) for all stored PDFs."""
    db = await get_db()
    rows = await (await db.execute(
        """SELECT p.id, p.notice_id, p.filename, p.size_bytes, p.created_at,
                  n.company_name, n.tier, n.user_id,
                  u.full_name AS user_name, u.email AS user_email
           FROM generated_pdfs p
           LEFT JOIN notices n ON p.notice_id = n.id
           LEFT JOIN users u ON n.user_id = u.id
           ORDER BY p.created_at DESC LIMIT ? OFFSET ?""",
        (limit, offset),
    )).fetchall()
    return [dict(r) for r in rows]


# ── Activity log ─────────────────────────────────────────────────────

async def log_activity_db(action: str, details: str = "", entity_type: str = "", entity_id: str = "") -> str:
    db = await get_db()
    lid = uuid.uuid4().hex[:12]
    await db.execute(
        "INSERT INTO activity_log (id, action, details, entity_type, entity_id, created_at) VALUES (?,?,?,?,?,?)",
        (lid, action, details, entity_type, entity_id, _now()),
    )
    await db.commit()
    return lid


async def get_activity_log_db(limit: int = 50) -> list[dict]:
    db = await get_db()
    rows = await (await db.execute(
        "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?", (limit,)
    )).fetchall()
    return [dict(r) for r in rows]


# ── Dashboard stats ──────────────────────────────────────────────────

async def get_dashboard_stats_db() -> dict:
    db = await get_db()
    total = (await (await db.execute("SELECT COUNT(*) FROM notices")).fetchone())[0]
    pending = (await (await db.execute("SELECT COUNT(*) FROM notices WHERE status='pending_review'")).fetchone())[0]
    approved = (await (await db.execute("SELECT COUNT(*) FROM notices WHERE status='approved'")).fetchone())[0]
    rejected = (await (await db.execute("SELECT COUNT(*) FROM notices WHERE status='rejected'")).fetchone())[0]
    sent = (await (await db.execute("SELECT COUNT(*) FROM notices WHERE status='sent'")).fetchone())[0]
    delivered = (await (await db.execute("SELECT COUNT(*) FROM notices WHERE status='delivered'")).fetchone())[0]
    lawyer_tier = (await (await db.execute("SELECT COUNT(*) FROM notices WHERE tier='lawyer'")).fetchone())[0]
    self_tier = total - lawyer_tier
    total_users = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
    total_analyses = (await (await db.execute("SELECT COUNT(*) FROM analyses")).fetchone())[0]
    total_pdfs = (await (await db.execute("SELECT COUNT(*) FROM generated_pdfs")).fetchone())[0]

    # Notices by date
    rows = await (await db.execute(
        "SELECT SUBSTR(created_at,1,10) AS d, COUNT(*) AS c FROM notices GROUP BY d ORDER BY d"
    )).fetchall()
    notices_by_date = {r["d"]: r["c"] for r in rows}

    return {
        "total_notices": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "sent": sent,
        "delivered": delivered,
        "lawyer_tier": lawyer_tier,
        "self_tier": self_tier,
        "total_users": total_users,
        "total_analyses": total_analyses,
        "total_pdfs": total_pdfs,
        "notices_by_date": notices_by_date,
    }


# ── Helpers ──────────────────────────────────────────────────────────

def _j(obj: Any) -> str | None:
    """Serialize to JSON string, or None if obj is None."""
    if obj is None:
        return None
    return json.dumps(obj, default=str)


def _pj(text: str | None) -> Any:
    """Parse JSON string back, or None."""
    if not text:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def _unpack_notice(row: aiosqlite.Row) -> dict:
    """Convert a notices row into a rich dict with parsed JSON fields."""
    d = dict(row)
    for key in (
        "complaint_json", "company_json", "contacts_json",
        "bare_act_refs_json", "claim_elements_json", "respondent_identity_json",
        "evidence_score_json", "limitation_json", "arbitration_json",
        "jurisdiction_json", "cure_period_json", "tc_counters_json",
        "policy_evidence_json", "delivery_json",
        "customer_controls_json", "follow_up_answers_json",
    ):
        parsed_key = key.replace("_json", "")
        d[parsed_key] = _pj(d.pop(key, None))
    # Remove the large blob from list views but keep it accessible
    d.pop("full_packet_json", None)
    return d
