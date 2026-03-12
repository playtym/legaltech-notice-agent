import ipaddress
import logging
import re
import socket
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse

import certifi
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")

_BLOCKED_HOSTNAMES = {"localhost", "0.0.0.0", "metadata.google.internal"}

_POLICY_PATH_HINTS = [
    "terms",
    "terms-and-conditions",
    "terms-conditions",
    "policy",
    "privacy",
    "refund",
    "return",
    "returns",
    "replacement",
    "cancellation",
    "cancel",
    "shipping",
    "delivery",
    "warranty",
    "grievance",
    "complaint",
    "legal",
]

_COMMON_POLICY_PATHS = [
    "/terms",
    "/terms-and-conditions",
    "/terms-conditions",
    "/policy",
    "/policies",
    "/privacy-policy",
    "/refund-policy",
    "/cancellation-policy",
    "/return-policy",
    "/returns-policy",
    "/shipping-policy",
    "/warranty-policy",
    "/grievance-redressal",
    "/legal",
]

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "have", "has", "was",
    "were", "your", "their", "they", "want", "just", "then", "than", "when", "what",
    "where", "how", "after", "before", "within", "about", "against", "because", "been",
    "not", "you", "our", "them", "can", "will", "could", "would", "should", "did",
    "complaint", "issue", "company", "consumer", "customer",
}


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

    async def find_policy_pages(
        self,
        website: str,
        issue_summary: str | None = None,
        company_name_hint: str | None = None,
    ) -> list[str]:
        """Discover policy/T&C pages using website HTML structure and path heuristics.

        The ranking uses:
        - anchor URL and anchor text hints (terms/refund/cancellation/etc.)
        - structural hints (footer/nav/legal sections)
        - complaint relevance (keywords from issue summary)
        """
        html = await self.fetch_text(website)
        soup = BeautifulSoup(html, "html.parser")
        base_host = urlparse(website).hostname
        if not base_host:
            return []

        complaint_terms = self._extract_issue_terms(issue_summary or "")

        scored: dict[str, int] = {}

        for a in soup.select("a[href]"):
            href = (a.get("href") or "").strip()
            if not href or href.startswith("#"):
                continue
            if href.lower().startswith(("mailto:", "tel:", "javascript:")):
                continue

            abs_url = urljoin(website, href)
            parsed = urlparse(abs_url)
            if parsed.scheme not in {"http", "https"}:
                continue
            if parsed.hostname and parsed.hostname != base_host:
                continue

            link_text = " ".join(a.stripped_strings).lower()
            url_text = abs_url.lower()
            score = 0

            # Keyword signals in URL and anchor text
            score += sum(2 for k in _POLICY_PATH_HINTS if k in url_text)
            score += sum(2 for k in _POLICY_PATH_HINTS if k in link_text)

            # Structural signals (footer/nav/legal)
            parent_blob = " ".join(
                [
                    str(a.get("class", "")),
                    str(a.get("id", "")),
                    str(a.parent.get("class", "")) if a.parent else "",
                    str(a.parent.get("id", "")) if a.parent else "",
                ]
            ).lower()
            if any(x in parent_blob for x in ("footer", "legal", "policy", "help", "support", "nav")):
                score += 2

            # Complaint relevance boost
            if complaint_terms:
                relevance = sum(1 for t in complaint_terms if t in link_text or t in url_text)
                score += relevance

            if score > 0:
                current = scored.get(abs_url, 0)
                scored[abs_url] = max(current, score)

        # Add common policy paths as candidates even if not linked prominently
        for p in _COMMON_POLICY_PATHS:
            candidate = urljoin(website, p)
            if urlparse(candidate).hostname == base_host:
                current = scored.get(candidate, 0)
                scored[candidate] = max(current, 1)

        # Search-engine fallback: query policy pages by domain and issue context.
        # We use a public HTML endpoint to avoid requiring API keys.
        query_targets = [base_host.replace("www.", "")]
        if company_name_hint:
            query_targets.append(company_name_hint)
        if complaint_terms:
            query_targets.append(" ".join(sorted(list(complaint_terms))[:5]))

        for target in query_targets:
            queries = [
                f'site:{base_host} terms and conditions',
                f'site:{base_host} refund policy',
                f'site:{base_host} cancellation policy',
                f'site:{base_host} return policy',
                f'site:{base_host} grievance policy',
                f'{target} refund policy terms conditions',
            ]
            for q in queries:
                for link in await self._search_links(q, limit=10):
                    p = urlparse(link)
                    if p.scheme not in {"http", "https"}:
                        continue
                    if p.hostname != base_host:
                        continue
                    bonus = 2 + sum(1 for k in _POLICY_PATH_HINTS if k in link.lower())
                    current = scored.get(link, 0)
                    scored[link] = max(current, bonus)

        ranked = sorted(scored.items(), key=lambda x: x[1], reverse=True)
        return [u for u, _ in ranked[:20]]

    async def _search_links(self, query: str, limit: int = 10) -> list[str]:
        """Fetch search result links from a public HTML endpoint.

        This is a best-effort fallback used to discover policy pages that are
        not clearly linked from homepage/footer/nav.
        """
        search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                follow_redirects=True,
                verify=certifi.where(),
            ) as client:
                resp = await client.get(search_url, headers=self.headers)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
        except Exception:
            return []

        links: list[str] = []
        seen: set[str] = set()
        for a in soup.select("a[href]"):
            href = (a.get("href") or "").strip()
            if not href:
                continue

            candidate = href
            # DuckDuckGo result links often wrap actual target in "uddg" param.
            if "duckduckgo.com/l/?" in href or href.startswith("/l/?"):
                q = parse_qs(urlparse(urljoin("https://duckduckgo.com", href)).query)
                uddg = (q.get("uddg") or [None])[0]
                if uddg:
                    candidate = unquote(uddg)

            parsed = urlparse(candidate)
            if parsed.scheme not in {"http", "https"}:
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            links.append(candidate)
            if len(links) >= limit:
                break
        return links

    def _extract_issue_terms(self, issue_summary: str) -> set[str]:
        words = re.findall(r"[a-zA-Z]{4,}", issue_summary.lower())
        return {w for w in words if w not in _STOPWORDS}
