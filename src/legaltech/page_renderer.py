"""
page_renderer.py — Programmatic page rendering engine for Lawly.

Turns URL slugs into full HTML pages using Jinja2 templates + JSON data.
URL patterns supported:
  /consumer-complaint-{sector}-{city}  → sector_complaint.html
  /legal-notice-{type}-{city}          → notice_type.html

All rendered pages are cached in-process (simple LRU dict, capped at 2000 entries).
In production, App Runner containers share nothing across instances — but each
container warms up fast because rendering is ~1ms.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).parent.parent.parent  # repo root
_DATA = _ROOT / "data" / "pages"
_TEMPLATES = Path(__file__).parent / "templates"

# ---------------------------------------------------------------------------
# Load data once at module import (a few hundred KB total, fine for startup)
# ---------------------------------------------------------------------------
def _load_json(name: str) -> dict | list:
    return json.loads((_DATA / name).read_text(encoding="utf-8"))


_raw_cities: list[dict] = _load_json("cities.json")
_cities: dict[str, dict] = {c["slug"]: c for c in _raw_cities}
_sectors: dict[str, dict] = _load_json("sectors.json")
_notice_types: dict[str, dict] = _load_json("notice_types.json")

# Pre-build "related cities" list (first 20 cities, excluding the current one)
_city_list_short = _raw_cities[:20]

# ---------------------------------------------------------------------------
# Jinja2 environment
# ---------------------------------------------------------------------------
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES)),
    autoescape=select_autoescape(["html"]),
)

# ---------------------------------------------------------------------------
# In-process LRU cache (capped to avoid unbounded memory growth)
# ---------------------------------------------------------------------------
_MAX_CACHE = 2_000
_cache: dict[str, str] = {}
_cache_keys: list[str] = []  # insertion-order track for eviction


def _cache_get(key: str) -> Optional[str]:
    return _cache.get(key)


def _cache_put(key: str, value: str) -> None:
    if key in _cache:
        return
    if len(_cache_keys) >= _MAX_CACHE:
        oldest = _cache_keys.pop(0)
        _cache.pop(oldest, None)
    _cache[key] = value
    _cache_keys.append(key)


# ---------------------------------------------------------------------------
# URL pattern matching
# ---------------------------------------------------------------------------
# Sector complaint: consumer-complaint-{sector}-{city}
# The tricky part: sector slugs can contain hyphens (e.g. "real-estate").
# Strategy: try the longest known sector match first.
_SECTOR_SLUGS_SORTED = sorted(_sectors.keys(), key=len, reverse=True)
_CITY_SLUGS = set(_cities.keys())


def _match_sector_city(path: str) -> Optional[tuple[str, str]]:
    """Return (sector_slug, city_slug) if path matches consumer-complaint-X-Y."""
    prefix = "consumer-complaint-"
    if not path.startswith(prefix):
        return None
    remainder = path[len(prefix):]
    for sector_slug in _SECTOR_SLUGS_SORTED:
        seg = sector_slug + "-"
        if remainder.startswith(seg):
            city_slug = remainder[len(seg):]
            if city_slug in _CITY_SLUGS:
                return sector_slug, city_slug
    return None


# Notice type: legal-notice-{type}-{city}
_NOTICE_SLUGS_SORTED = sorted(_notice_types.keys(), key=len, reverse=True)


def _match_notice_city(path: str) -> Optional[tuple[str, str]]:
    """Return (notice_slug, city_slug) if path matches legal-notice-X-Y."""
    prefix = "legal-notice-"
    if not path.startswith(prefix):
        return None
    remainder = path[len(prefix):]
    for notice_slug in _NOTICE_SLUGS_SORTED:
        seg = notice_slug + "-"
        if remainder.startswith(seg):
            city_slug = remainder[len(seg):]
            if city_slug in _CITY_SLUGS:
                return notice_slug, city_slug
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_page(path: str) -> Optional[str]:
    """
    Try to render a programmatic page for the given URL path.
    Returns rendered HTML string or None if path does not match any pattern.
    """
    # Strip leading slash if present
    path = path.lstrip("/")

    cached = _cache_get(path)
    if cached is not None:
        return cached

    html = _try_render(path)
    if html is not None:
        _cache_put(path, html)
    return html


def _related_cities(current_slug: str) -> list[dict]:
    """Return up to 15 cities excluding the current one."""
    return [c for c in _raw_cities if c["slug"] != current_slug][:15]


def _try_render(path: str) -> Optional[str]:
    # Pattern 1: consumer-complaint-{sector}-{city}
    match = _match_sector_city(path)
    if match:
        sector_slug, city_slug = match
        tpl = _env.get_template("sector_complaint.html")
        return tpl.render(
            sector=_sectors[sector_slug],
            city=_cities[city_slug],
            related_cities=_related_cities(city_slug),
        )

    # Pattern 2: legal-notice-{type}-{city}
    match = _match_notice_city(path)
    if match:
        notice_slug, city_slug = match
        tpl = _env.get_template("notice_type.html")
        return tpl.render(
            notice=_notice_types[notice_slug],
            city=_cities[city_slug],
            related_cities=_related_cities(city_slug),
        )

    return None


# ---------------------------------------------------------------------------
# Sitemap helpers (used by /sitemap.xml route)
# ---------------------------------------------------------------------------

def all_programmatic_urls() -> list[str]:
    """Return all URLs this renderer can handle (for sitemap generation)."""
    urls = []
    for sector_slug in _sectors:
        for city_slug in _cities:
            urls.append(f"consumer-complaint-{sector_slug}-{city_slug}")
    for notice_slug in _notice_types:
        for city_slug in _cities:
            urls.append(f"legal-notice-{notice_slug}-{city_slug}")
    return urls
