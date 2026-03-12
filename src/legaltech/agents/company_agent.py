from urllib.parse import urlparse

import tldextract

from legaltech.schemas import CompanyProfile


class CompanyAgent:
    async def run(self, company_name_hint: str | None, website: str | None) -> CompanyProfile:
        domain = None
        brand = company_name_hint

        if website:
            domain = urlparse(website).netloc
            ext = tldextract.extract(website)
            if not brand and ext.domain:
                brand = ext.domain.title()

        return CompanyProfile(
            legal_name=company_name_hint,
            brand_name=brand,
            domain=domain,
        )
