from legaltech.schemas import PolicyEvidence
from legaltech.services.web_research import WebResearchService


class PolicyAgent:
    async def run(self, website: str, web: WebResearchService) -> list[PolicyEvidence]:
        pages = await web.find_relevant_pages(website)
        evidence: list[PolicyEvidence] = []

        for page in pages:
            lpage = page.lower()
            if not any(k in lpage for k in ("policy", "terms", "refund", "privacy", "grievance")):
                continue
            try:
                html = await web.fetch_text(page)
            except Exception:
                continue

            snippet = " ".join(html.split())[:500]
            evidence.append(
                PolicyEvidence(
                    title="Policy or terms excerpt",
                    excerpt=snippet,
                    source_url=page,
                )
            )

            if len(evidence) >= 6:
                break

        return evidence
