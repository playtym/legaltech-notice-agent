"""Bing Webmaster Tools API client for search insights."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_BING_API_BASE = "https://ssl.bing.com/webmaster/api.svc/json"
_SITE_URL = "https://lawly.store/"


def _api_key() -> str | None:
    return os.getenv("BING_WEBMASTER_API_KEY")


# ── low-level helpers ────────────────────────────────────────────────

async def _bing_get(endpoint: str, extra_params: dict | None = None) -> Any:
    """Call a Bing Webmaster GET endpoint. Returns parsed JSON or None."""
    key = _api_key()
    if not key:
        return None
    params: dict[str, str] = {"siteUrl": _SITE_URL, "apikey": key}
    if extra_params:
        params.update(extra_params)
    url = f"{_BING_API_BASE}/{endpoint}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return data.get("d", data)
    except Exception:
        logger.warning("Bing API call failed: %s", endpoint, exc_info=True)
        return None


async def _bing_post(endpoint: str, body: Any = None) -> Any:
    """Call a Bing Webmaster POST endpoint."""
    key = _api_key()
    if not key:
        return None
    params: dict[str, str] = {"siteUrl": _SITE_URL, "apikey": key}
    url = f"{_BING_API_BASE}/{endpoint}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, params=params, json=body)
            resp.raise_for_status()
            data = resp.json()
            return data.get("d", data)
    except Exception:
        logger.warning("Bing API POST failed: %s", endpoint, exc_info=True)
        return None


# ── public functions ─────────────────────────────────────────────────

async def get_query_stats() -> list[dict]:
    """Search queries driving traffic (keywords, impressions, clicks, CTR, position)."""
    raw = await _bing_get("GetQueryStats")
    if not raw:
        return []
    rows: list[dict] = []
    for r in raw:
        rows.append({
            "query": r.get("Query", ""),
            "date": _parse_date(r.get("Date", "")),
            "impressions": r.get("Impressions", 0),
            "clicks": r.get("Clicks", 0),
            "ctr": round(r.get("AvgClickPosition", 0), 2),
            "position": round(r.get("AvgImpressionPosition", 0), 1),
        })
    return rows


async def get_page_stats() -> list[dict]:
    """Per-page traffic stats."""
    raw = await _bing_get("GetRankAndTrafficStats")
    if not raw:
        return []
    rows: list[dict] = []
    for r in raw:
        rows.append({
            "date": _parse_date(r.get("Date", "")),
            "impressions": r.get("Impressions", 0),
            "clicks": r.get("Clicks", 0),
            "position": round(r.get("AvgClickPosition", 0), 1),
        })
    return rows


async def get_crawl_stats() -> list[dict]:
    """Crawl activity — pages crawled, errors, etc."""
    raw = await _bing_get("GetCrawlStats")
    if not raw:
        return []
    rows: list[dict] = []
    for r in raw:
        rows.append({
            "date": _parse_date(r.get("Date", "")),
            "pages_crawled": r.get("CrawledPages", 0),
            "crawl_errors": r.get("CrawlErrors", 0),
            "in_index": r.get("InIndex", 0),
            "in_links": r.get("InLinks", 0),
        })
    return rows


async def get_url_traffic(url: str) -> list[dict]:
    """Traffic stats for a specific URL."""
    raw = await _bing_get("GetUrlTrafficInfo", {"url": url})
    if not raw:
        return []
    if isinstance(raw, dict):
        raw = [raw]
    return [
        {
            "date": _parse_date(r.get("Date", "")),
            "impressions": r.get("Impressions", 0),
            "clicks": r.get("Clicks", 0),
        }
        for r in raw
    ]


async def get_submission_quota() -> dict:
    """How many URL submissions remain today."""
    raw = await _bing_get("GetUrlSubmissionQuota")
    if not raw:
        return {"daily_quota": 0, "monthly_quota": 0}
    return {
        "daily_quota": raw.get("DailyQuota", 0),
        "monthly_quota": raw.get("MonthlyQuota", 0),
    }


async def submit_url(url: str) -> dict:
    """Submit a single URL for Bing indexing."""
    key = _api_key()
    if not key:
        return {"ok": False, "error": "No Bing API key configured"}
    params = {"siteUrl": _SITE_URL, "apikey": key}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{_BING_API_BASE}/SubmitUrl",
                params=params,
                json={"siteUrl": _SITE_URL, "url": url},
            )
            resp.raise_for_status()
            return {"ok": True, "url": url}
    except httpx.HTTPStatusError as exc:
        return {"ok": False, "error": f"HTTP {exc.response.status_code}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def submit_url_batch(urls: list[str]) -> dict:
    """Submit multiple URLs for Bing indexing."""
    key = _api_key()
    if not key:
        return {"ok": False, "error": "No Bing API key configured"}
    params = {"siteUrl": _SITE_URL, "apikey": key}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{_BING_API_BASE}/SubmitUrlBatch",
                params=params,
                json={"siteUrl": _SITE_URL, "urlList": urls},
            )
            resp.raise_for_status()
            return {"ok": True, "urls": urls, "count": len(urls)}
    except httpx.HTTPStatusError as exc:
        return {"ok": False, "error": f"HTTP {exc.response.status_code}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def get_insights_summary() -> dict:
    """Aggregate summary for the admin Insights dashboard."""
    query_stats = await get_query_stats()
    page_stats = await get_page_stats()
    crawl_stats = await get_crawl_stats()
    quota = await get_submission_quota()

    # Aggregate query stats by keyword
    keyword_agg: dict[str, dict] = {}
    for row in query_stats:
        q = row["query"]
        if q not in keyword_agg:
            keyword_agg[q] = {"query": q, "impressions": 0, "clicks": 0, "positions": []}
        keyword_agg[q]["impressions"] += row["impressions"]
        keyword_agg[q]["clicks"] += row["clicks"]
        if row["position"]:
            keyword_agg[q]["positions"].append(row["position"])

    top_keywords = []
    for kw, agg in keyword_agg.items():
        positions = agg["positions"]
        avg_pos = round(sum(positions) / len(positions), 1) if positions else 0
        ctr = round(agg["clicks"] / agg["impressions"] * 100, 2) if agg["impressions"] else 0
        top_keywords.append({
            "query": kw,
            "impressions": agg["impressions"],
            "clicks": agg["clicks"],
            "ctr": ctr,
            "avg_position": avg_pos,
        })
    top_keywords.sort(key=lambda x: x["impressions"], reverse=True)

    # Totals
    total_impressions = sum(r["impressions"] for r in page_stats)
    total_clicks = sum(r["clicks"] for r in page_stats)
    overall_ctr = round(total_clicks / total_impressions * 100, 2) if total_impressions else 0

    # Daily traffic trend
    daily_traffic: dict[str, dict] = {}
    for r in page_stats:
        d = r["date"]
        if d not in daily_traffic:
            daily_traffic[d] = {"impressions": 0, "clicks": 0}
        daily_traffic[d]["impressions"] += r["impressions"]
        daily_traffic[d]["clicks"] += r["clicks"]

    # Latest crawl info
    latest_crawl = crawl_stats[-1] if crawl_stats else {}
    total_crawled = sum(r["pages_crawled"] for r in crawl_stats)
    total_errors = sum(r["crawl_errors"] for r in crawl_stats)

    return {
        "configured": bool(_api_key()),
        "totals": {
            "impressions": total_impressions,
            "clicks": total_clicks,
            "ctr": overall_ctr,
        },
        "top_keywords": top_keywords[:50],
        "daily_traffic": daily_traffic,
        "crawl": {
            "total_pages_crawled": total_crawled,
            "total_errors": total_errors,
            "latest": latest_crawl,
        },
        "submission_quota": quota,
        "raw_query_count": len(query_stats),
        "raw_page_count": len(page_stats),
        "raw_crawl_count": len(crawl_stats),
    }


# ── helpers ──────────────────────────────────────────────────────────

def _parse_date(val: str) -> str:
    """Parse Bing's /Date(...)/ format to YYYY-MM-DD."""
    if not val:
        return ""
    if val.startswith("/Date("):
        try:
            ms = int(val.split("(")[1].split(")")[0].rstrip("-+0123456789")[0:13] if "-" in val.split("(")[1] or "+" in val.split("(")[1] else val.split("(")[1].split(")")[0])
            dt = datetime.utcfromtimestamp(ms / 1000)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, IndexError):
            return val
    return val
