"""Gap analysis agent — Claude-powered case weakness detector.

Analyses the full complaint context and identifies gaps that would
weaken the legal notice. Returns specific, actionable follow-up
questions to ask the user before generating the notice.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from legaltech.services.llm import LLMService

_SYSTEM_PROMPT = """\
You are a senior Indian consumer rights lawyer preparing to draft a legal notice \
under the Consumer Protection Act, 2019. Your job is to review the complaint material \
and identify ALL gaps, weaknesses, or missing information that could:
1. Make the notice legally incomplete or factually deficient
2. Allow the company to easily rebut or dismiss the notice
3. Weaken the claim before a Consumer Commission

For each gap, generate a specific follow-up question to ask the complainant.

CATEGORIES of gaps to check:
- FACTS: Missing key facts (what happened, when, how, who was involved)
- EVIDENCE: Missing documentary proof that strengthens the claim
- TIMELINE: Gaps or vagueness in chronology
- AMOUNT: Claim amount not quantified or unclear
- IDENTITY: Company identity, grievance officer, registered entity unknown
- PRIOR_ATTEMPTS: Whether the complainant exhausted internal grievance mechanisms
- CAUSATION: Missing link between company's action and the consumer's loss
- RESOLUTION: Desired resolution is vague or disproportionate

RULES:
- Only ask questions about information NOT already provided
- Prioritize questions that would make the biggest difference to case strength
- Mark each question as "critical" (notice will be weak without it) or "important" (strengthens the case)
- Maximum 8 questions — focus on what matters most
- Be specific — don't ask generic questions

Respond in JSON:
{
  "case_strength": "weak" | "moderate" | "strong",
  "case_strength_reasoning": "brief explanation of current case strength",
  "ready_to_generate": true | false,
  "questions": [
    {
      "id": "q1",
      "category": "FACTS|EVIDENCE|TIMELINE|AMOUNT|IDENTITY|PRIOR_ATTEMPTS|CAUSATION|RESOLUTION",
      "priority": "critical|important",
      "question": "specific question text",
      "why_it_matters": "brief explanation of why this info is needed"
    }
  ]
}

If the complaint is comprehensive and ready for notice generation, set ready_to_generate=true \
and return an empty questions list.
"""


@dataclass
class FollowUpQuestion:
    id: str
    category: str
    priority: str  # "critical" or "important"
    question: str
    why_it_matters: str


@dataclass
class GapAnalysisResult:
    case_strength: str  # "weak", "moderate", "strong"
    case_strength_reasoning: str
    ready_to_generate: bool
    questions: list[FollowUpQuestion] = field(default_factory=list)


class GapAnalysisAgent:
    """Uses Claude to assess case completeness and generate follow-up questions."""

    def __init__(self, llm: LLMService) -> None:
        self.llm = llm

    async def run(
        self,
        issue_summary: str,
        timeline: list[str],
        evidence: list[str],
        desired_resolution: str,
        company_name: str | None,
        website: str | None,
        contacts_found: list[str],
        policies_found: list[str],
        respondent_identity_found: bool,
        previous_answers: dict[str, str] | None = None,
    ) -> GapAnalysisResult:
        # Build context for Claude
        context_parts = [
            f"## Complaint Summary\n{issue_summary}",
            f"\n## Company\nName: {company_name or 'NOT PROVIDED'}\nWebsite: {website or 'NOT PROVIDED'}",
            f"\n## Timeline ({len(timeline)} entries)",
        ]
        for t in timeline:
            context_parts.append(f"- {t}")

        context_parts.append(f"\n## Evidence ({len(evidence)} items)")
        for e in evidence:
            context_parts.append(f"- {e}")

        context_parts.append(f"\n## Desired Resolution\n{desired_resolution}")

        context_parts.append(f"\n## Web Research Results")
        context_parts.append(f"Contacts found: {len(contacts_found)} ({', '.join(contacts_found[:3]) if contacts_found else 'NONE — web scraping found no contacts'})")
        context_parts.append(f"Policies/T&C found: {len(policies_found)} pages ({'yes' if policies_found else 'NONE — could not scrape company policies'})")
        context_parts.append(f"Respondent identity (CIN/registered office): {'Found' if respondent_identity_found else 'NOT FOUND from website'}")

        if previous_answers:
            context_parts.append("\n## Previously Answered Follow-up Questions")
            for qid, answer in previous_answers.items():
                context_parts.append(f"- {qid}: {answer}")

        user_prompt = "\n".join(context_parts)

        data = await self.llm.complete_json(_SYSTEM_PROMPT, user_prompt)

        questions = [
            FollowUpQuestion(
                id=q["id"],
                category=q["category"],
                priority=q["priority"],
                question=q["question"],
                why_it_matters=q["why_it_matters"],
            )
            for q in data.get("questions", [])
        ]

        return GapAnalysisResult(
            case_strength=data.get("case_strength", "unknown"),
            case_strength_reasoning=data.get("case_strength_reasoning", ""),
            ready_to_generate=data.get("ready_to_generate", False),
            questions=questions,
        )
