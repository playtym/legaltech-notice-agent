"""Respondent identity verification agent.

Attempts to resolve official company identity via MCA (CIN/LLPIN),
registered office, and grievance officer details from public sources.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from legaltech.services.web_research import WebResearchService


CIN_RE = re.compile(r"\b[UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b")
LLPIN_RE = re.compile(r"\b(?:AAA|AAB|AAC|AAD|AAE|AAF|AAG|AAH|AAI|AAJ|AAK|AAL|AAM)[A-Z]{1}-\d{4}\b")


@dataclass
class RespondentIdentity:
    cin: str | None = None
    llpin: str | None = None
    registered_name: str | None = None
    registered_office: str | None = None
    grievance_officer_name: str | None = None
    grievance_officer_email: str | None = None
    grievance_officer_phone: str | None = None
    source_urls: list[str] = field(default_factory=list)
    verification_flags: list[str] = field(default_factory=list)


class RespondentIdAgent:
    """Scrapes public pages for CIN/LLPIN, registered office, and grievance officer."""

    async def run(self, website: str, company_name_hint: str | None, web: WebResearchService) -> RespondentIdentity:
        identity = RespondentIdentity()

        pages = await web.find_relevant_pages(website)
        target_keywords = ("about", "legal", "grievance", "contact", "terms", "privacy", "compliance")
        target_pages = [p for p in pages if any(k in p.lower() for k in target_keywords)][:8]

        import asyncio

        async def _fetch(url: str) -> tuple[str, str] | None:
            try:
                html = await web.fetch_text(url)
                return (url, html)
            except Exception:
                return None

        fetched = await asyncio.gather(*[_fetch(u) for u in target_pages])

        for result in fetched:
            if result is None:
                continue
            page_url, html = result

            text = " ".join(html.split())

            cin_matches = CIN_RE.findall(text)
            if cin_matches and not identity.cin:
                identity.cin = cin_matches[0]
                identity.source_urls.append(page_url)

            llpin_matches = LLPIN_RE.findall(text)
            if llpin_matches and not identity.llpin:
                identity.llpin = llpin_matches[0]
                identity.source_urls.append(page_url)

            lower = text.lower()

            if not identity.registered_office:
                for marker in ("registered office:", "regd. office:", "registered address:"):
                    idx = lower.find(marker)
                    if idx != -1:
                        snippet = text[idx + len(marker):idx + len(marker) + 300].strip()
                        identity.registered_office = _clean_address(snippet)
                        identity.source_urls.append(page_url)
                        break

            if not identity.grievance_officer_name:
                for marker in ("grievance officer", "nodal officer", "compliance officer"):
                    idx = lower.find(marker)
                    if idx != -1:
                        block = text[idx:idx + 500]
                        identity.grievance_officer_name = _extract_name_near(block)
                        emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", block)
                        if emails:
                            identity.grievance_officer_email = emails[0]
                        phones = re.findall(r"\+?\d[\d\s().-]{7,}\d", block)
                        if phones:
                            identity.grievance_officer_phone = phones[0].strip()
                        identity.source_urls.append(page_url)
                        break

        if not identity.cin and not identity.llpin:
            identity.verification_flags.append(
                "CIN/LLPIN not found on website; verify via MCA portal (mca.gov.in) before serving notice"
            )
        if not identity.registered_office:
            identity.verification_flags.append(
                "Registered office address not found; required for valid service of notice"
            )
        if not identity.grievance_officer_name:
            identity.verification_flags.append(
                "Grievance/nodal officer details not found; check company's IT Act §79 intermediary disclosure"
            )

        identity.source_urls = list(dict.fromkeys(identity.source_urls))
        return identity


def _clean_address(raw: str) -> str:
    end_markers = (".", "email", "phone", "tel:", "fax:", "cin:", "grievance")
    result = raw
    for marker in end_markers:
        idx = result.lower().find(marker)
        if idx > 20:
            result = result[:idx]
            break
    return result.strip().rstrip(",;")


def _extract_name_near(block: str) -> str | None:
    lines = block.split("\n")
    for line in lines[:5]:
        cleaned = line.strip().rstrip(",;:")
        words = cleaned.split()
        if 2 <= len(words) <= 5 and all(w[0].isupper() for w in words if w.isalpha()):
            return cleaned
    parts = block.split(":")
    if len(parts) > 1:
        candidate = parts[1].strip().split("\n")[0].split(",")[0].strip()
        if 2 <= len(candidate.split()) <= 5:
            return candidate
    return None
