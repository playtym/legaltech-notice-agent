from legaltech.schemas import ContactInfo
from legaltech.services.web_research import WebResearchService


class ContactDiscoveryAgent:
    async def run(self, website: str, web: WebResearchService) -> list[ContactInfo]:
        pages = await web.find_relevant_pages(website)
        contacts: list[ContactInfo] = []

        for page in pages[:8]:
            try:
                extracted = await web.extract_contacts_from_page(page)
            except Exception:
                continue

            for email in extracted.get("emails", [])[:3]:
                label = "Legal/Support Contact" if any(k in page.lower() for k in ("legal", "grievance", "complaint")) else "Customer Support"
                contacts.append(
                    ContactInfo(
                        label=label,
                        email=email,
                        page_url=page,
                        confidence=0.65,
                    )
                )

            for phone in extracted.get("phones", [])[:2]:
                contacts.append(
                    ContactInfo(
                        label="Phone Contact",
                        phone=phone,
                        page_url=page,
                        confidence=0.5,
                    )
                )

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
