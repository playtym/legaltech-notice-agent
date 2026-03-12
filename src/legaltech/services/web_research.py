import ipaddress
import logging
import re
import socket
from urllib.parse import urljoin, urlparse

import certifi
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")

_BLOCKED_HOSTNAMES = {"localhost", "0.0.0.0", "metadata.google.internal"}


def _is_safe_url(url: str) -> bool:
    """Block SSRF: reject private/loopback/link-local IPs and known internal hostnames."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    if hostname in _BLOCKED_HOSTNAMES:
        return False
    try:
        for info in socket.getaddrinfo(hostname, None):
            addr = info[4][0]
            ip = ipaddress.ip_address(addr)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
    except (socket.gaierror, ValueError):
        return False
    return True


class WebResearchService:
    def __init__(self, user_agent: str, timeout_seconds: int = 20) -> None:
        self.timeout_seconds = timeout_seconds
        self.headers = {"User-Agent": user_agent}

    async def fetch_text(self, url: str) -> str:
        if not _is_safe_url(url):
            raise ValueError(f"Blocked: URL resolves to private/internal address")
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            follow_redirects=True,
            verify=certifi.where(),
        ) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text

    async def scrape_links(self, url: str, limit: int = 30) -> list[str]:
        html = await self.fetch_text(url)
        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []
        seen: set[str] = set()

        for a in soup.select("a[href]"):
            raw_href = a.get("href", "")
            if not isinstance(raw_href, str):
                continue
            href = raw_href.strip()
            if not href:
                continue
            absolute = urljoin(url, href)
            if absolute in seen:
                continue
            if urlparse(absolute).scheme not in {"http", "https"}:
                continue
            seen.add(absolute)
            links.append(absolute)
            if len(links) >= limit:
                break
        return links

    async def extract_contacts_from_page(self, page_url: str) -> dict[str, list[str]]:
        html = await self.fetch_text(page_url)
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)

        emails = sorted(set(EMAIL_RE.findall(text)))
        phones = sorted(set(PHONE_RE.findall(text)))
        return {"emails": emails, "phones": phones}

    async def find_relevant_pages(self, website: str) -> list[str]:
        keywords = [
            "contact",
            "support",
            "customer",
            "legal",
            "grievance",
            "complaint",
            "terms",
            "policy",
            "privacy",
            "refund",
        ]
        links = await self.scrape_links(website, limit=80)
        scored: list[tuple[int, str]] = []
        for link in links:
            ll = link.lower()
            score = sum(1 for k in keywords if k in ll)
            if score > 0:
                scored.append((score, link))
        scored.sort(key=lambda x: x[0], reverse=True)

        ranked = [website]
        for _, link in scored:
            if link not in ranked:
                ranked.append(link)
            if len(ranked) >= 12:
                break
        return ranked
