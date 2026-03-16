"""Lightweight JSON-file store for notices and admin settings.

When DATA_BUCKET is set every JSON file is persisted to S3 so data
survives App Runner re-deploys. Falls back to local data/ for dev.
"""

from __future__ import annotations

import json
import logging
import os
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
_NOTICES_FILE = _DATA_DIR / "notices.json"
_LAWYER_FILE = _DATA_DIR / "lawyer.json"
_SEO_FILE = _DATA_DIR / "seo_settings.json"
_BLOG_FILE = _DATA_DIR / "blog_posts.json"
_PAGES_FILE = _DATA_DIR / "pages.json"
_ACTIVITY_FILE = _DATA_DIR / "activity_log.json"
_ADMIN_PW_FILE = _DATA_DIR / "admin_pw.json"
_REDIRECTS_FILE = _DATA_DIR / "redirects.json"
_AEO_FILE = _DATA_DIR / "aeo_settings.json"
_EMAIL_SETTINGS_FILE = _DATA_DIR / "email_settings.json"
_EMAIL_LOG_FILE = _DATA_DIR / "email_log.json"
_ANALYTICS_FILE = _DATA_DIR / "analytics_events.json"
_TICKETS_FILE = _DATA_DIR / "support_tickets.json"

_PW_ALGO = "pbkdf2_sha256"
_PW_ITERATIONS = 200_000

# ── S3 backend ───────────────────────────────────────────────────────

_DATA_BUCKET: str | None = os.getenv("DATA_BUCKET")
_S3_PREFIX = "data/"
_s3 = None


def _get_s3():
    global _s3
    if _s3 is None:
        import boto3
        _s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION", "ap-south-1"))
    return _s3


def _s3_key(local_path: Path) -> str:
    return _S3_PREFIX + local_path.name


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> Any:
    if _DATA_BUCKET:
        return _read_json_s3(path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _write_json(path: Path, data: Any) -> None:
    if _DATA_BUCKET:
        _write_json_s3(path, data)
        return
    _ensure_dir()
    path.write_text(json.dumps(data, indent=2, default=str))


def _read_json_s3(path: Path) -> Any:
    try:
        resp = _get_s3().get_object(Bucket=_DATA_BUCKET, Key=_s3_key(path))
        return json.loads(resp["Body"].read())
    except _get_s3().exceptions.NoSuchKey:
        return {}
    except Exception:
        _logger.exception("S3 read failed for %s", _s3_key(path))
        return {}


def _write_json_s3(path: Path, data: Any) -> None:
    try:
        _get_s3().put_object(
            Bucket=_DATA_BUCKET,
            Key=_s3_key(path),
            Body=json.dumps(data, indent=2, default=str).encode(),
            ContentType="application/json",
        )
    except Exception:
        _logger.exception("S3 write failed for %s", _s3_key(path))


# ── Lawyer settings ──────────────────────────────────────────────────

def get_lawyer() -> dict | None:
    _ensure_dir()
    data = _read_json(_LAWYER_FILE)
    return data if data else None


def save_lawyer(data: dict) -> dict:
    _ensure_dir()
    _write_json(_LAWYER_FILE, data)
    return data


# ── Admin password override ──────────────────────────────────────────

def is_password_hash(value: str) -> bool:
    return value.startswith(f"{_PW_ALGO}$")


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PW_ITERATIONS,
    ).hex()
    return f"{_PW_ALGO}${_PW_ITERATIONS}${salt}${digest}"


def verify_password(candidate: str, stored: str) -> bool:
    if not stored:
        return False
    if not is_password_hash(stored):
        return hmac.compare_digest(candidate, stored)
    try:
        _, iterations, salt, expected = stored.split("$", 3)
        computed = hashlib.pbkdf2_hmac(
            "sha256",
            candidate.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
    except Exception:
        return False
    return hmac.compare_digest(computed, expected)

def get_stored_password() -> str | None:
    """Return the admin password stored in data/, or None to use env default."""
    data = _read_json(_ADMIN_PW_FILE)
    return data.get("password") if isinstance(data, dict) else None


def set_stored_password(new_password: str) -> None:
    _ensure_dir()
    _write_json(_ADMIN_PW_FILE, {"password": _hash_password(new_password)})


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


# ── SEO settings ─────────────────────────────────────────────────────

_DEFAULT_SEO: dict = {
    "site_title": "Jago Grahak Jago — AI Legal Notice Generator for Indian Consumers",
    "meta_description": "Generate a professional AI-powered legal notice in minutes. Backed by 15+ Indian consumer protection statutes. Starting at ₹199.",
    "meta_keywords": "legal notice generator, consumer complaint India, CPA 2019, consumer protection, legal notice online",
    "og_title": "Jago Grahak Jago — AI Legal Notice Generator",
    "og_description": "Generate a professional consumer legal notice in minutes. Backed by Indian law. Starting at ₹199.",
    "og_image": "",
    "canonical_url": "https://lawly.store/",
    "google_analytics_id": "",
    "google_search_console_verification": "",
    "bing_verification": "",
    "custom_head_tags": "",
    "default_robots": "index, follow",
    "hreflang_entries": [],
    "faq_schema": [],
}


def get_seo_settings() -> dict:
    _ensure_dir()
    data = _read_json(_SEO_FILE)
    return {**_DEFAULT_SEO, **data} if data else dict(_DEFAULT_SEO)


def save_seo_settings(data: dict) -> dict:
    _ensure_dir()
    merged = {**_DEFAULT_SEO, **data}
    _write_json(_SEO_FILE, merged)
    return merged


# ── Blog posts ───────────────────────────────────────────────────────

def get_all_blog_posts() -> list[dict]:
    posts = _read_json(_BLOG_FILE)
    if not isinstance(posts, dict):
        return []
    return sorted(posts.values(), key=lambda p: p.get("created_at", ""), reverse=True)


def get_blog_post(slug: str) -> dict | None:
    posts = _read_json(_BLOG_FILE)
    return posts.get(slug)


def get_published_blog_posts() -> list[dict]:
    return [p for p in get_all_blog_posts() if p.get("status") == "published"]


def save_blog_post(data: dict) -> dict:
    _ensure_dir()
    posts = _read_json(_BLOG_FILE)
    if not isinstance(posts, dict):
        posts = {}

    slug = data.get("slug") or _slugify(data.get("title", "untitled"))
    now = datetime.utcnow().isoformat()

    existing = posts.get(slug)
    post = {
        "slug": slug,
        "title": data.get("title", ""),
        "meta_description": data.get("meta_description", ""),
        "meta_keywords": data.get("meta_keywords", ""),
        "content": data.get("content", ""),
        "author": data.get("author", "Jago Grahak Jago"),
        "status": data.get("status", "draft"),
        "created_at": existing["created_at"] if existing else now,
        "updated_at": now,
    }
    posts[slug] = post
    _write_json(_BLOG_FILE, posts)
    return post


def delete_blog_post(slug: str) -> bool:
    posts = _read_json(_BLOG_FILE)
    if slug not in posts:
        return False
    del posts[slug]
    _write_json(_BLOG_FILE, posts)
    return True


# ── SEO pages ────────────────────────────────────────────────────────

def get_all_pages() -> list[dict]:
    pages = _read_json(_PAGES_FILE)
    if not isinstance(pages, dict):
        return []
    return sorted(pages.values(), key=lambda p: p.get("path", ""))


def get_page(path: str) -> dict | None:
    pages = _read_json(_PAGES_FILE)
    return pages.get(path)


def save_page(data: dict) -> dict:
    _ensure_dir()
    pages = _read_json(_PAGES_FILE)
    if not isinstance(pages, dict):
        pages = {}

    path = data.get("path", "/")
    page = {
        "path": path,
        "title": data.get("title", ""),
        "meta_description": data.get("meta_description", ""),
        "meta_keywords": data.get("meta_keywords", ""),
        "og_title": data.get("og_title", ""),
        "og_description": data.get("og_description", ""),
        "priority": data.get("priority", 0.5),
        "changefreq": data.get("changefreq", "weekly"),
        "include_in_sitemap": data.get("include_in_sitemap", True),
        "updated_at": datetime.utcnow().isoformat(),
    }
    pages[path] = page
    _write_json(_PAGES_FILE, pages)
    return page


def delete_page(path: str) -> bool:
    pages = _read_json(_PAGES_FILE)
    if path not in pages:
        return False
    del pages[path]
    _write_json(_PAGES_FILE, pages)
    return True


# ── 301 Redirects ────────────────────────────────────────────────────

def get_all_redirects() -> list[dict]:
    data = _read_json(_REDIRECTS_FILE)
    if not isinstance(data, list):
        return []
    return data


def save_redirect(entry: dict) -> dict:
    _ensure_dir()
    redirects = get_all_redirects()
    entry["id"] = entry.get("id") or uuid.uuid4().hex[:8]
    entry["created_at"] = entry.get("created_at") or datetime.utcnow().isoformat()
    # Replace if same source exists
    redirects = [r for r in redirects if r.get("from_path") != entry["from_path"]]
    redirects.append(entry)
    _write_json(_REDIRECTS_FILE, redirects)
    return entry


def delete_redirect(redirect_id: str) -> bool:
    redirects = get_all_redirects()
    filtered = [r for r in redirects if r.get("id") != redirect_id]
    if len(filtered) == len(redirects):
        return False
    _write_json(_REDIRECTS_FILE, filtered)
    return True


def find_redirect(path: str) -> dict | None:
    for r in get_all_redirects():
        if r.get("from_path") == path:
            return r
    return None


# ── AEO / AI Engine Optimization ─────────────────────────────────────

_DEFAULT_AEO: dict = {
    "llms_txt": "",
    "llms_full_txt": "",
    "org_schema": {
        "name": "Lawly",
        "url": "https://lawly.store",
        "logo": "",
        "description": "",
        "founding_date": "",
        "founders": "",
        "same_as": [],
        "contact_email": "",
        "contact_phone": "",
    },
    "speakable_selectors": [],
    "howto_schemas": [],
    "ai_snippets": [],
    "topic_clusters": [],
    "cite_sources": [],
}


def get_aeo_settings() -> dict:
    _ensure_dir()
    data = _read_json(_AEO_FILE)
    if not data or not isinstance(data, dict):
        return dict(_DEFAULT_AEO)
    merged = {}
    for k, v in _DEFAULT_AEO.items():
        if k in data:
            merged[k] = data[k]
        else:
            merged[k] = v if not isinstance(v, (dict, list)) else (dict(v) if isinstance(v, dict) else list(v))
    return merged


def save_aeo_settings(data: dict) -> dict:
    _ensure_dir()
    current = get_aeo_settings()
    current.update(data)
    _write_json(_AEO_FILE, current)
    return current


# ── Helpers ──────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    import re
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "untitled"


# ── Activity log ─────────────────────────────────────────────────────

def log_activity(action: str, details: str = "", entity_type: str = "", entity_id: str = "") -> dict:
    """Append an admin action to the activity log."""
    _ensure_dir()
    activities = _read_json(_ACTIVITY_FILE)
    if not isinstance(activities, list):
        activities = []
    entry = {
        "id": uuid.uuid4().hex[:8],
        "action": action,
        "details": details,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
    activities.insert(0, entry)
    activities = activities[:500]  # keep last 500
    _write_json(_ACTIVITY_FILE, activities)
    return entry


def get_activity_log(limit: int = 50) -> list[dict]:
    activities = _read_json(_ACTIVITY_FILE)
    if not isinstance(activities, list):
        return []
    return activities[:limit]


# ── Dashboard stats ──────────────────────────────────────────────────

def get_dashboard_stats() -> dict:
    """Aggregate stats for the admin dashboard."""
    notices = _read_json(_NOTICES_FILE)
    if not isinstance(notices, dict):
        notices = {}
    all_notices = list(notices.values())

    blog_posts = _read_json(_BLOG_FILE)
    if not isinstance(blog_posts, dict):
        blog_posts = {}

    total = len(all_notices)
    pending = sum(1 for n in all_notices if n.get("status") == "pending_review")
    approved = sum(1 for n in all_notices if n.get("status") == "approved")
    rejected = sum(1 for n in all_notices if n.get("status") == "rejected")
    sent = sum(1 for n in all_notices if n.get("status") == "sent")
    delivered = sum(1 for n in all_notices if n.get("status") == "delivered")

    lawyer_tier = sum(1 for n in all_notices if n.get("tier") == "lawyer")
    self_tier = total - lawyer_tier

    published_posts = sum(1 for p in blog_posts.values() if p.get("status") == "published")
    draft_posts = len(blog_posts) - published_posts

    date_counts: dict[str, int] = {}
    for n in all_notices:
        d = (n.get("created_at") or "")[:10]
        if d:
            date_counts[d] = date_counts.get(d, 0) + 1

    return {
        "total_notices": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "sent": sent,
        "delivered": delivered,
        "lawyer_tier": lawyer_tier,
        "self_tier": self_tier,
        "total_blog_posts": len(blog_posts),
        "published_posts": published_posts,
        "draft_posts": draft_posts,
        "notices_by_date": dict(sorted(date_counts.items())),
    }


# ── Email / Notification settings ────────────────────────────────────

_DEFAULT_EMAIL_SETTINGS: dict = {
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_password": "",
    "from_name": "Lawly",
    "from_email": "",
    "use_tls": True,
    "admin_alert_email": "",
    "templates": {
        "notice_ready": {
            "subject": "Your Legal Notice is Ready — Lawly",
            "body": "Dear {{name}},\n\nYour legal notice regarding {{company}} is ready.\n\n{{notice_link}}\n\nRegards,\nLawly Team",
        },
        "payment_receipt": {
            "subject": "Payment Receipt — Lawly #{{notice_id}}",
            "body": "Dear {{name}},\n\nPayment of {{amount}} received for your legal notice against {{company}}.\n\nTier: {{tier}}\nNotice ID: {{notice_id}}\n\nRegards,\nLawly Team",
        },
        "follow_up": {
            "subject": "Follow-up: Your Legal Notice Against {{company}}",
            "body": "Dear {{name}},\n\nIt's been {{days}} days since your legal notice against {{company}} was sent.\n\nIf you haven't received a response within the cure period, you may consider:\n1. File a complaint at edaakhil.nic.in\n2. Escalate to the consumer forum\n\nNeed help? Reply to this email.\n\nRegards,\nLawly Team",
        },
        "admin_alert": {
            "subject": "[Lawly Admin] New Notice Generated — {{company}}",
            "body": "A new legal notice was generated.\n\nComplainant: {{name}} ({{email}})\nCompany: {{company}}\nTier: {{tier}}\nNotice ID: {{notice_id}}\nTime: {{time}}",
        },
    },
    "auto_send_notice_ready": True,
    "auto_send_admin_alert": True,
    "follow_up_days": 15,
}


def get_email_settings() -> dict:
    _ensure_dir()
    data = _read_json(_EMAIL_SETTINGS_FILE)
    if not data or not isinstance(data, dict):
        return dict(_DEFAULT_EMAIL_SETTINGS)
    merged = dict(_DEFAULT_EMAIL_SETTINGS)
    for k, v in data.items():
        if k == "templates" and isinstance(v, dict):
            merged["templates"] = {**_DEFAULT_EMAIL_SETTINGS["templates"], **v}
        else:
            merged[k] = v
    return merged


def save_email_settings(data: dict) -> dict:
    _ensure_dir()
    current = get_email_settings()
    for k, v in data.items():
        if k == "templates" and isinstance(v, dict):
            current["templates"] = {**current.get("templates", {}), **v}
        else:
            current[k] = v
    _write_json(_EMAIL_SETTINGS_FILE, current)
    return current


def log_email(entry: dict) -> dict:
    """Append a sent/failed email record to the email log."""
    _ensure_dir()
    log = _read_json(_EMAIL_LOG_FILE)
    if not isinstance(log, list):
        log = []
    record = {
        "id": uuid.uuid4().hex[:8],
        "to": entry.get("to", ""),
        "subject": entry.get("subject", ""),
        "template": entry.get("template", "custom"),
        "status": entry.get("status", "sent"),
        "error": entry.get("error", ""),
        "notice_id": entry.get("notice_id", ""),
        "timestamp": datetime.utcnow().isoformat(),
    }
    log.insert(0, record)
    log = log[:1000]  # keep last 1000
    _write_json(_EMAIL_LOG_FILE, log)
    return record


def get_email_log(limit: int = 50) -> list[dict]:
    log = _read_json(_EMAIL_LOG_FILE)
    if not isinstance(log, list):
        return []
    return log[:limit]


# ── Analytics / Events ───────────────────────────────────────────────

def track_event(event_type: str, data: dict | None = None) -> dict:
    """Track a funnel event (page_view, notice_started, notice_generated, pdf_downloaded, payment)."""
    _ensure_dir()
    events = _read_json(_ANALYTICS_FILE)
    if not isinstance(events, list):
        events = []
    entry = {
        "id": uuid.uuid4().hex[:8],
        "event": event_type,
        "data": data or {},
        "timestamp": datetime.utcnow().isoformat(),
    }
    events.insert(0, entry)
    events = events[:10000]  # keep last 10k
    _write_json(_ANALYTICS_FILE, events)
    return entry


def get_analytics_events(limit: int = 5000) -> list[dict]:
    events = _read_json(_ANALYTICS_FILE)
    if not isinstance(events, list):
        return []
    return events[:limit]


def get_analytics_summary() -> dict:
    """Compute funnel, daily trends, category breakdown from raw events."""
    events = get_analytics_events(10000)
    now = datetime.utcnow()

    # Funnel counts
    funnel = {"page_view": 0, "notice_started": 0, "notice_generated": 0, "pdf_downloaded": 0, "payment": 0}
    # Daily counts (last 30 days)
    daily: dict[str, dict[str, int]] = {}
    # Category breakdown
    categories: dict[str, int] = {}
    # Revenue
    revenue_total = 0.0
    revenue_daily: dict[str, float] = {}
    # Tier counts for funnel
    tier_counts: dict[str, int] = {}
    # Traffic sources
    sources: dict[str, int] = {}
    referrers: dict[str, int] = {}

    for e in events:
        evt = e.get("event", "")
        ts = e.get("timestamp", "")[:10]
        data = e.get("data", {})

        if evt in funnel:
            funnel[evt] += 1

        # Daily
        if ts:
            if ts not in daily:
                daily[ts] = {}
            daily[ts][evt] = daily[ts].get(evt, 0) + 1

        # Categories
        cat = data.get("category", "")
        if cat and evt == "notice_generated":
            categories[cat] = categories.get(cat, 0) + 1

        # Revenue
        if evt == "payment":
            amt = float(data.get("amount", 0))
            revenue_total += amt
            if ts:
                revenue_daily[ts] = revenue_daily.get(ts, 0) + amt

        # Tiers
        if evt == "notice_generated":
            t = data.get("tier", "self_send")
            tier_counts[t] = tier_counts.get(t, 0) + 1

        # Traffic sources (from page_view events)
        if evt == "page_view":
            ref = (data.get("referrer") or "").strip()
            src = (data.get("source") or "").strip()
            # Determine source label
            if src:
                label = src.lower()
            elif ref:
                try:
                    from urllib.parse import urlparse
                    host = urlparse(ref).hostname or ""
                    # Simplify common domains
                    for domain, name in [
                        ("reddit.com", "reddit"), ("google.", "google"),
                        ("bing.com", "bing"), ("facebook.com", "facebook"),
                        ("twitter.com", "twitter"), ("x.com", "twitter"),
                        ("linkedin.com", "linkedin"), ("instagram.com", "instagram"),
                        ("youtube.com", "youtube"), ("t.co", "twitter"),
                    ]:
                        if domain in host:
                            label = name
                            break
                    else:
                        label = host.replace("www.", "")
                except Exception:
                    label = "other"
            else:
                label = "direct"
            sources[label] = sources.get(label, 0) + 1
            if ref:
                try:
                    from urllib.parse import urlparse
                    host = urlparse(ref).hostname or ref
                    host = host.replace("www.", "")
                    referrers[host] = referrers.get(host, 0) + 1
                except Exception:
                    referrers[ref[:60]] = referrers.get(ref[:60], 0) + 1

    # Sort daily by date, last 30
    sorted_days = sorted(daily.keys())[-30:]
    daily_trend = {d: daily[d] for d in sorted_days}

    return {
        "funnel": funnel,
        "daily_trend": daily_trend,
        "categories": dict(sorted(categories.items(), key=lambda x: -x[1])),
        "revenue_total": revenue_total,
        "revenue_daily": dict(sorted(revenue_daily.items())[-30:]),
        "tier_counts": tier_counts,
        "total_events": len(events),
        "traffic_sources": dict(sorted(sources.items(), key=lambda x: -x[1])),
        "top_referrers": dict(sorted(referrers.items(), key=lambda x: -x[1])[:20]),
    }


# ── Support Tickets ──────────────────────────────────────────────────

def create_ticket(data: dict) -> dict:
    _ensure_dir()
    tickets = _read_json(_TICKETS_FILE)
    if not isinstance(tickets, dict):
        tickets = {}
    ticket_id = uuid.uuid4().hex[:8]
    now = datetime.utcnow().isoformat()
    ticket = {
        "id": ticket_id,
        "name": data.get("name", ""),
        "email": data.get("email", ""),
        "subject": data.get("subject", ""),
        "message": data.get("message", ""),
        "category": data.get("category", "general"),
        "notice_id": data.get("notice_id", ""),
        "status": "open",
        "priority": data.get("priority", "normal"),
        "admin_notes": "",
        "replies": [],
        "created_at": now,
        "updated_at": now,
    }
    tickets[ticket_id] = ticket
    _write_json(_TICKETS_FILE, tickets)
    return ticket


def get_all_tickets() -> list[dict]:
    tickets = _read_json(_TICKETS_FILE)
    if not isinstance(tickets, dict):
        return []
    return sorted(tickets.values(), key=lambda t: t.get("created_at", ""), reverse=True)


def get_ticket(ticket_id: str) -> dict | None:
    tickets = _read_json(_TICKETS_FILE)
    if not isinstance(tickets, dict):
        return None
    return tickets.get(ticket_id)


def update_ticket(ticket_id: str, updates: dict) -> dict | None:
    tickets = _read_json(_TICKETS_FILE)
    if not isinstance(tickets, dict) or ticket_id not in tickets:
        return None
    ticket = tickets[ticket_id]
    for k in ("status", "priority", "admin_notes"):
        if k in updates:
            ticket[k] = updates[k]
    ticket["updated_at"] = datetime.utcnow().isoformat()
    tickets[ticket_id] = ticket
    _write_json(_TICKETS_FILE, tickets)
    return ticket


def add_ticket_reply(ticket_id: str, reply: dict) -> dict | None:
    tickets = _read_json(_TICKETS_FILE)
    if not isinstance(tickets, dict) or ticket_id not in tickets:
        return None
    ticket = tickets[ticket_id]
    ticket["replies"].append({
        "id": uuid.uuid4().hex[:6],
        "from": reply.get("from", "admin"),
        "message": reply.get("message", ""),
        "timestamp": datetime.utcnow().isoformat(),
    })
    ticket["updated_at"] = datetime.utcnow().isoformat()
    tickets[ticket_id] = ticket
    _write_json(_TICKETS_FILE, tickets)
    return ticket


def get_ticket_stats() -> dict:
    tickets = get_all_tickets()
    total = len(tickets)
    open_count = sum(1 for t in tickets if t.get("status") == "open")
    in_progress = sum(1 for t in tickets if t.get("status") == "in_progress")
    resolved = sum(1 for t in tickets if t.get("status") == "resolved")
    closed = sum(1 for t in tickets if t.get("status") == "closed")
    return {
        "total": total,
        "open": open_count,
        "in_progress": in_progress,
        "resolved": resolved,
        "closed": closed,
    }


# ── Version management (S3 object versioning) ───────────────────────

_STATIC_BUCKET = "lawly.store"


def list_versioned_files(bucket: str | None = None) -> list[dict]:
    """List all files in a bucket that have multiple versions."""
    bucket = bucket or _DATA_BUCKET or _STATIC_BUCKET
    s3 = _get_s3()
    files: dict[str, dict] = {}
    kwargs: dict = {"Bucket": bucket}
    if bucket == _DATA_BUCKET:
        kwargs["Prefix"] = _S3_PREFIX
    while True:
        resp = s3.list_object_versions(**kwargs)
        for v in resp.get("Versions", []):
            key = v["Key"]
            if key not in files:
                files[key] = {
                    "key": key,
                    "latest_modified": v["LastModified"].isoformat(),
                    "latest_size": v["Size"],
                    "version_count": 0,
                    "is_latest": v["IsLatest"],
                }
            files[key]["version_count"] += 1
            if v["IsLatest"]:
                files[key]["latest_modified"] = v["LastModified"].isoformat()
                files[key]["latest_size"] = v["Size"]
        if resp.get("IsTruncated"):
            kwargs["KeyMarker"] = resp["NextKeyMarker"]
            kwargs["VersionIdMarker"] = resp["NextVersionIdMarker"]
        else:
            break
    return sorted(files.values(), key=lambda f: f["key"])


def list_file_versions(file_key: str, bucket: str | None = None) -> list[dict]:
    """List all versions of a specific file."""
    bucket = bucket or _DATA_BUCKET or _STATIC_BUCKET
    s3 = _get_s3()
    versions = []
    kwargs: dict = {"Bucket": bucket, "Prefix": file_key}
    while True:
        resp = s3.list_object_versions(**kwargs)
        for v in resp.get("Versions", []):
            if v["Key"] != file_key:
                continue
            versions.append({
                "version_id": v["VersionId"],
                "last_modified": v["LastModified"].isoformat(),
                "size": v["Size"],
                "is_latest": v["IsLatest"],
            })
        if resp.get("IsTruncated"):
            kwargs["KeyMarker"] = resp["NextKeyMarker"]
            kwargs["VersionIdMarker"] = resp["NextVersionIdMarker"]
        else:
            break
    return versions


def get_file_version_content(file_key: str, version_id: str, bucket: str | None = None) -> tuple[str, str]:
    """Return (content, content_type) for a specific version of a file."""
    bucket = bucket or _DATA_BUCKET or _STATIC_BUCKET
    s3 = _get_s3()
    resp = s3.get_object(Bucket=bucket, Key=file_key, VersionId=version_id)
    content_type = resp.get("ContentType", "application/octet-stream")
    body = resp["Body"].read()
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        import base64
        text = base64.b64encode(body).decode()
        content_type = "application/base64"
    return text, content_type


def revert_file_version(file_key: str, version_id: str, bucket: str | None = None) -> dict:
    """Revert a file to a specific version by copying it as a new version."""
    bucket = bucket or _DATA_BUCKET or _STATIC_BUCKET
    s3 = _get_s3()
    copy_source = {"Bucket": bucket, "Key": file_key, "VersionId": version_id}
    s3.copy_object(
        Bucket=bucket,
        Key=file_key,
        CopySource=copy_source,
    )
    return {"status": "reverted", "key": file_key, "reverted_to_version": version_id}
