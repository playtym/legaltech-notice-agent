import asyncio

from legaltech.schemas import ContactInfo
from legaltech.services.web_research import WebResearchService


class ContactDiscoveryAgent:
    async def run(self, website: str, web: WebResearchService) -> list[ContactInfo]:
        pages = await web.find_relevant_pages(website)
        contacts: list[ContactInfo] = []

        async def _scrape(page: str) -> list[ContactInfo]:
            try:
                extracted = await web.extract_contacts_from_page(page)
            except Exception:
                return []
            results: list[ContactInfo] = []
            for email in extracted.get("emails", [])[:3]:
                label = "Legal/Support Contact" if any(k in page.lower() for k in ("legal", "grievance", "complaint")) else "Customer Support"
                results.append(ContactInfo(label=label, email=email, page_url=page, confidence=0.65))
            for phone in extracted.get("phones", [])[:2]:
                results.append(ContactInfo(label="Phone Contact", phone=phone, page_url=page, confidence=0.5))
            return results

        batch_results = await asyncio.gather(*[_scrape(p) for p in pages[:8]])
        for batch in batch_results:
            contacts.extend(batch)

        # De-duplicate by email/phone key while preserving order.
        seen: set[str] = set()
        unique: list[ContactInfo] = []
        for c in contacts:
            key = c.email or c.phone or ""
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(c)

        return unique[:10]
