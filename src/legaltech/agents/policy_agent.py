import re

from bs4 import BeautifulSoup

from legaltech.schemas import PolicyEvidence
from legaltech.services.web_research import WebResearchService


_POLICY_TERMS = (
    "terms",
    "conditions",
    "policy",
    "refund",
    "cancellation",
    "return",
    "replacement",
    "privacy",
    "shipping",
    "delivery",
    "warranty",
    "grievance",
    "complaint",
    "legal",
)

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "have", "has", "was",
    "were", "your", "their", "they", "want", "just", "then", "than", "when", "what",
    "where", "how", "after", "before", "within", "about", "against", "because", "been",
    "not", "you", "our", "them", "can", "will", "could", "would", "should", "did",
    "complaint", "issue", "company", "consumer", "customer",
}


class PolicyAgent:
    async def run(
        self,
        website: str,
        web: WebResearchService,
        issue_summary: str | None = None,
        company_name_hint: str | None = None,
    ) -> list[PolicyEvidence]:
        pages = await web.find_policy_pages(
            website=website,
            issue_summary=issue_summary,
            company_name_hint=company_name_hint,
        )
        evidence: list[PolicyEvidence] = []
        issue_terms = self._extract_issue_terms(issue_summary or "")

        for page in pages:
            try:
                html = await web.fetch_text(page)
            except Exception:
                continue

            soup = BeautifulSoup(html, "html.parser")
            title = (soup.title.string.strip() if soup.title and soup.title.string else "").strip()
            body_text = soup.get_text(" ", strip=True)
            compact = " ".join(body_text.split())
            lower_blob = f"{page.lower()} {title.lower()} {compact[:3000].lower()}"

            policy_hits = sum(1 for t in _POLICY_TERMS if t in lower_blob)
            if policy_hits == 0:
                continue

            complaint_hits = sum(1 for t in issue_terms if t in lower_blob)
            score = policy_hits + (2 * complaint_hits)
            if score < 2:
                continue

            snippet = compact[:700]
            heading = (soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else "").strip()
            evidence_title = heading or title or "Policy or terms excerpt"

            evidence.append(
                PolicyEvidence(
                    title=evidence_title,
                    excerpt=snippet,
                    source_url=page,
                )
            )

            if len(evidence) >= 6:
                break

        return evidence

    @staticmethod
    def _extract_issue_terms(issue_summary: str) -> set[str]:
        words = re.findall(r"[a-zA-Z]{4,}", issue_summary.lower())
        return {w for w in words if w not in _STOPWORDS}
