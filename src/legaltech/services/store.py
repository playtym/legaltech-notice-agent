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


# ── SEO settings ─────────────────────────────────────────────────────

_DEFAULT_SEO: dict = {
    "site_title": "Jago Grahak Jago — AI Legal Notice Generator for Indian Consumers",
    "meta_description": "Generate a professional AI-powered legal notice in minutes. Backed by 15+ Indian consumer protection statutes. Starting at ₹199.",
    "meta_keywords": "legal notice generator, consumer complaint India, CPA 2019, consumer protection, legal notice online",
    "og_title": "Jago Grahak Jago — AI Legal Notice Generator",
    "og_description": "Generate a professional consumer legal notice in minutes. Backed by Indian law. Starting at ₹199.",
    "canonical_url": "https://lawly.store/",
    "google_analytics_id": "",
    "google_search_console_verification": "",
    "custom_head_tags": "",
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


# ── Helpers ──────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    import re
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "untitled"
