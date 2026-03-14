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
_SEO_FILE = _DATA_DIR / "seo_settings.json"
_BLOG_FILE = _DATA_DIR / "blog_posts.json"
_PAGES_FILE = _DATA_DIR / "pages.json"
_ACTIVITY_FILE = _DATA_DIR / "activity_log.json"
_ADMIN_PW_FILE = _DATA_DIR / "admin_pw.json"
_REDIRECTS_FILE = _DATA_DIR / "redirects.json"
_AEO_FILE = _DATA_DIR / "aeo_settings.json"


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


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


# ── Admin password override ──────────────────────────────────────────

def get_stored_password() -> str | None:
    """Return the admin password stored in data/, or None to use env default."""
    data = _read_json(_ADMIN_PW_FILE)
    return data.get("password") if isinstance(data, dict) else None


def set_stored_password(new_password: str) -> None:
    _ensure_dir()
    _write_json(_ADMIN_PW_FILE, {"password": new_password})


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
