import logging
from datetime import datetime

from legaltech.agents.arbitration_agent import ArbitrationDetectionAgent

logger = logging.getLogger(__name__)
from legaltech.agents.claim_elements_agent import ClaimElementsAgent
from legaltech.agents.escalation_agent import EscalationStrategyAgent
from legaltech.agents.company_agent import CompanyAgent
from legaltech.agents.contact_agent import ContactDiscoveryAgent
from legaltech.agents.cure_period import determine_cure_period
from legaltech.agents.evidence_scoring_agent import EvidenceScoringAgent
from legaltech.agents.gap_analysis_agent import GapAnalysisAgent, GapAnalysisResult
from legaltech.agents.intake_agent import IntakeAgent
from legaltech.agents.jurisdiction_agent import determine_jurisdiction
from legaltech.agents.legal_analysis_agent import LegalAnalysisAgent
from legaltech.agents.limitation_agent import check_limitation
from legaltech.agents.notice_agent import NoticeDraftAgent
from legaltech.agents.policy_agent import PolicyAgent
from legaltech.agents.respondent_id_agent import RespondentIdAgent
from legaltech.agents.tc_counter_agent import TCCounterAgent
from legaltech.config.settings import get_settings
from legaltech.schemas import (
    ArbitrationInfo,
    BareActReference,
    CaseAnalysisResponse,
    ClaimElementResult,
    ComplaintInput,
    CurePeriodInfo,
    DeliveryInfo,
    EvidenceScoreInfo,
    FollowUpQuestionOut,
    JurisdictionInfo,
    LimitationInfo,
    NoticePacket,
    PolicyEvidence,
    RespondentIdentityInfo,
    ServiceTier,
    TCCounterInfo,
)
from legaltech.services.email_service import (
    build_lawyer_send_body,
    build_self_send_body,
    send_notice_email,
)
from legaltech.services.llm import LLMService
from legaltech.services.pdf_generator import generate_pdf
from legaltech.services.web_research import WebResearchService


class LegalNoticePipeline:
    def __init__(self) -> None:
        settings = get_settings()
        self.web = WebResearchService(
            user_agent=settings.user_agent,
            timeout_seconds=settings.request_timeout_seconds,
        )
        self.llm = LLMService(
            model_name=settings.model_name,
            api_key=settings.anthropic_api_key,
        )
        self.intake = IntakeAgent()
        self.company = CompanyAgent()
        self.contacts = ContactDiscoveryAgent()
        self.policy = PolicyAgent()
        self.legal = LegalAnalysisAgent(llm=self.llm)
        self.claim_elements = ClaimElementsAgent()
        self.respondent_id = RespondentIdAgent()
        self.evidence_scoring = EvidenceScoringAgent()
        self.arbitration = ArbitrationDetectionAgent()
        self.tc_counter = TCCounterAgent()
        self.escalation = EscalationStrategyAgent()
        self.gap_analysis = GapAnalysisAgent(self.llm)
        self.notice = NoticeDraftAgent(self.llm)

    def _required_user_uploads(self, complaint: ComplaintInput) -> list[str]:
        required = [
            "Purchase receipt/invoice",
            "Order number and transaction/reference ID",
            "Payment proof (bank statement/card/wallet/UPI screenshot)",
            "Complaint emails/chats/call logs with timestamps",
        ]

        if len(complaint.evidence) > 0:
            return []
        return required

    async def analyze(
        self,
        complaint: ComplaintInput,
        previous_answers: dict[str, str] | None = None,
    ) -> CaseAnalysisResponse:
        """Phase 1: Analyze the case and return follow-up questions if needed.

        Call this BEFORE run(). If ready_to_generate is False, present the
        questions to the user, collect answers, and call analyze() again with
        previous_answers until ready_to_generate is True (or user wants to proceed anyway).
        """
        # Run lightweight pipeline steps to gather context
        intake = await self.intake.run(complaint)

        company = await self.company.run(
            company_name_hint=complaint.company_name_hint,
            website=str(complaint.website) if complaint.website else None,
        )

        contacts_found: list[str] = []
        policies_found: list[str] = []
        respondent_found = False
        respondent_identity = None

        if complaint.website:
            website = str(complaint.website)
            try:
                contacts = await self.contacts.run(website=website, web=self.web)
                contacts_found = [c.email or c.phone or "" for c in contacts if c.email or c.phone]
            except Exception as exc:
                logger.warning("Contact discovery failed (non-fatal): %s", exc)
            try:
                policies = await self.policy.run(website=website, web=self.web)
                policies_found = [p.title for p in policies]
            except Exception as exc:
                logger.warning("Policy scraping failed (non-fatal): %s", exc)
            try:
                respondent_identity = await self.respondent_id.run(
                    website=website,
                    company_name_hint=complaint.company_name_hint,
                    web=self.web,
                )
                respondent_found = bool(
                    respondent_identity and (respondent_identity.cin or respondent_identity.registered_name)
                )
            except Exception as exc:
                logger.warning("Respondent ID lookup failed (non-fatal): %s", exc)

        # Run Claude-powered gap analysis
        gap_result = await self.gap_analysis.run(
            issue_summary=complaint.issue_summary,
            timeline=complaint.timeline,
            evidence=complaint.evidence,
            desired_resolution=complaint.desired_resolution,
            company_name=complaint.company_name_hint,
            website=str(complaint.website) if complaint.website else None,
            contacts_found=contacts_found,
            policies_found=policies_found,
            respondent_identity_found=respondent_found,
            previous_answers=previous_answers,
        )

        questions = [
            FollowUpQuestionOut(
                id=q.id,
                category=q.category,
                priority=q.priority,
                question=q.question,
                why_it_matters=q.why_it_matters,
            )
            for q in gap_result.questions
        ]

        return CaseAnalysisResponse(
            case_strength=gap_result.case_strength,
            case_strength_reasoning=gap_result.case_strength_reasoning,
            ready_to_generate=gap_result.ready_to_generate,
            questions=questions,
            llm_cost_estimate=self.llm.pricing_info,
            company_name_found=company.legal_name or company.brand_name,
            company_domain=company.domain,
            contacts_found=contacts_found,
            respondent_cin=respondent_identity.cin if respondent_identity else None,
            respondent_registered_name=respondent_identity.registered_name if respondent_identity else None,
            respondent_registered_office=respondent_identity.registered_office if respondent_identity else None,
            grievance_officer_email=respondent_identity.grievance_officer_email if respondent_identity else None,
            policies_found=policies_found,
        )

    async def run(
        self,
        complaint: ComplaintInput,
        tier: ServiceTier = ServiceTier.self_send,
        follow_up_answers: dict[str, str] | None = None,
    ) -> NoticePacket:
        intake = await self.intake.run(complaint)

        company = await self.company.run(
            company_name_hint=complaint.company_name_hint,
            website=str(complaint.website) if complaint.website else None,
        )

        contacts = []
        policies = []
        respondent_identity = None
        if complaint.website:
            website = str(complaint.website)
            try:
                contacts = await self.contacts.run(website=website, web=self.web)
            except Exception as exc:
                logger.warning("Contact discovery failed (non-fatal): %s", exc)
            try:
                policies = await self.policy.run(website=website, web=self.web)
            except Exception as exc:
                logger.warning("Policy scraping failed (non-fatal): %s", exc)
            try:
                respondent_identity = await self.respondent_id.run(
                    website=website,
                    company_name_hint=complaint.company_name_hint,
                    web=self.web,
                )
            except Exception as exc:
                logger.warning("Respondent ID lookup failed (non-fatal): %s", exc)

        legal_analysis = await self.legal.run(
            complaint=complaint,
            policy_evidence=policies,
            normalized_issue=intake.normalized_issue,
        )

        # ── Element-by-element claim checks ──────────────────────────
        corpus = " ".join([
            complaint.issue_summary,
            complaint.desired_resolution,
            intake.normalized_issue,
            " ".join(complaint.timeline),
            " ".join(complaint.evidence),
            " ".join(e.excerpt for e in policies),
        ])
        claim_results = await self.claim_elements.run(
            plausible_sections=legal_analysis.plausible_sections,
            corpus=corpus,
        )

        # ── Evidence consistency scoring ─────────────────────────────
        evidence_score = await self.evidence_scoring.run(
            complaint=complaint,
            normalized_issue=intake.normalized_issue,
        )

        # ── Limitation period check ──────────────────────────────────
        limitation_result = check_limitation(
            timeline=complaint.timeline,
            issue_summary=complaint.issue_summary,
        )

        # ── Arbitration clause detection ─────────────────────────────
        arbitration_result = await self.arbitration.run(policy_evidence=policies)

        # ── T&C counter-arguments (preemptive defense rebuttal) ──────
        tc_counter_result = await self.tc_counter.run(
            policy_evidence=policies,
            issue_summary=complaint.issue_summary,
        )

        # ── Jurisdiction / forum determination ───────────────────────
        jurisdiction_result = determine_jurisdiction(
            complainant_address=complaint.complainant.address,
            issue_summary=complaint.issue_summary,
            desired_resolution=complaint.desired_resolution,
            timeline=complaint.timeline,
            evidence=complaint.evidence,
        )

        # ── Dynamic cure period ──────────────────────────────────────
        cure_days, cure_rationale = determine_cure_period(
            issue_summary=complaint.issue_summary,
            timeline_length=len(complaint.timeline),
        )

        # ── Escalation strategy (pressure tactics) ────────────────
        escalation_result = self.escalation.run(
            complaint=complaint,
            company=company,
            policies=policies,
            contacts_found=len(contacts),
            respondent_identity_found=bool(
                respondent_identity and (respondent_identity.cin or respondent_identity.registered_name)
            ),
            evidence_count=len(complaint.evidence),
        )

        # ── Notice draft ─────────────────────────────────────────────
        legal_notice = await self.notice.run(
            complaint=complaint,
            normalized_issue=intake.normalized_issue,
            company=company,
            contacts=contacts,
            policies=policies,
            legal_analysis=legal_analysis,
            claim_results=claim_results,
            respondent_identity=respondent_identity,
            evidence_score=evidence_score,
            limitation_result=limitation_result,
            arbitration_result=arbitration_result,
            jurisdiction_result=jurisdiction_result,
            tc_counter_result=tc_counter_result,
            cure_days=cure_days,
            cure_rationale=cure_rationale,
            follow_up_answers=follow_up_answers,
            escalation_strategy=escalation_result,
        )

        # ── Build output packet ──────────────────────────────────────
        synthetic_policy = [*policies]
        for flag in intake.smell_test_flags + legal_analysis.risk_flags:
            synthetic_policy.append(
                PolicyEvidence(
                    title="Risk/Smell Test Flag",
                    excerpt=flag,
                    source_url="internal://analysis",
                )
            )
        for missing in intake.missing_facts:
            synthetic_policy.append(
                PolicyEvidence(
                    title="Missing Intake Detail",
                    excerpt=missing,
                    source_url="internal://analysis",
                )
            )

        bare_act_refs = [
            BareActReference(
                act=e.act,
                section=e.section,
                title=e.title,
                bare_text=e.bare_text,
                amendment_note=e.amendment_note,
                state_rules=list(e.state_rules),
            )
            for e in legal_analysis.bare_act_entries
        ]

        claim_element_results = [
            ClaimElementResult(
                section_label=f"{cr.section.act}, {cr.section.section}",
                score=cr.score,
                overall_pass=cr.overall_pass,
                element_details=[
                    {"element": c.element, "satisfied": str(c.satisfied), "reasoning": c.reasoning}
                    for c in cr.checks
                ],
            )
            for cr in claim_results
        ]

        respondent_info = None
        if respondent_identity:
            respondent_info = RespondentIdentityInfo(
                cin=respondent_identity.cin,
                llpin=respondent_identity.llpin,
                registered_name=respondent_identity.registered_name,
                registered_office=respondent_identity.registered_office,
                grievance_officer_name=respondent_identity.grievance_officer_name,
                grievance_officer_email=respondent_identity.grievance_officer_email,
                grievance_officer_phone=respondent_identity.grievance_officer_phone,
                source_urls=respondent_identity.source_urls,
                verification_flags=respondent_identity.verification_flags,
            )

        evidence_score_info = EvidenceScoreInfo(
            overall_score=evidence_score.overall_score,
            completeness_score=evidence_score.completeness_score,
            consistency_score=evidence_score.consistency_score,
            contradictions=evidence_score.contradictions,
            gaps=evidence_score.gaps,
            suggestions=evidence_score.suggestions,
        )

        limitation_info = LimitationInfo(
            category=limitation_result.warning.split("'")[1] if "'" in limitation_result.warning else "consumer_complaint",
            period_years=limitation_result.limitation_years,
            start_event=limitation_result.earliest_event_date.isoformat() if limitation_result.earliest_event_date else "unknown",
            deadline=limitation_result.deadline.isoformat() if limitation_result.deadline else None,
            days_remaining=limitation_result.days_remaining,
            urgent=limitation_result.days_remaining is not None and limitation_result.days_remaining < 90,
            warning=limitation_result.warning,
        )

        arbitration_info = ArbitrationInfo(
            has_arbitration_clause=arbitration_result.has_arbitration_clause,
            clause_text=arbitration_result.clauses_found[0].text_excerpt if arbitration_result.clauses_found else None,
            has_jurisdiction_clause=arbitration_result.has_jurisdiction_restriction,
            jurisdiction_text=arbitration_result.restricted_jurisdiction,
            legal_impact=arbitration_result.legal_impact or None,
            consumer_override_note=arbitration_result.recommendation or None,
        )

        jurisdiction_info = JurisdictionInfo(
            forum=jurisdiction_result.forum,
            pecuniary_basis=jurisdiction_result.pecuniary_basis,
            territorial_basis=jurisdiction_result.territorial_basis,
            filing_note="; ".join(jurisdiction_result.filing_notes),
        )

        cure_period_info = CurePeriodInfo(
            days=cure_days,
            category=cure_rationale.split("(")[1].rstrip(")") if "(" in cure_rationale else "standard",
            rationale=cure_rationale,
        )

        tc_counter_infos = [
            TCCounterInfo(
                defense_clause=c.defense_clause,
                clause_excerpt=c.clause_excerpt,
                legal_counter=c.legal_counter,
                statutory_basis=c.statutory_basis,
                precedent_note=c.precedent_note,
            )
            for c in tc_counter_result.counters
        ]

        # ── PDF generation ───────────────────────────────────────────
        is_lawyer = tier == ServiceTier.lawyer_assisted
        pdf_bytes = generate_pdf(legal_notice, is_lawyer_tier=is_lawyer)
        price = 599 if is_lawyer else 199

        # ── Email delivery ───────────────────────────────────────────
        company_label = company.legal_name or company.brand_name or "the company"
        company_email = contacts[0].email if contacts else None
        delivery = DeliveryInfo(
            tier=tier,
            price_inr=price,
            pdf_generated=True,
            delivery_status="pdf_ready",
        )

        if tier == ServiceTier.self_send:
            body = build_self_send_body(complaint.complainant.full_name, company_label)
            result = send_notice_email(
                to_email=complaint.complainant.email,
                to_name=complaint.complainant.full_name,
                subject=f"Your Legal Notice against {company_label} — Ready to Send",
                body_text=body,
                pdf_bytes=pdf_bytes,
                pdf_filename=f"Legal_Notice_{company_label.replace(' ', '_')}.pdf",
            )
            delivery.email_sent = result.success
            delivery.email_recipients = result.recipients
            delivery.email_message_id = result.message_id
            delivery.delivery_status = "sent_to_complainant" if result.success else f"email_failed: {result.message}"

        elif tier == ServiceTier.lawyer_assisted and company_email:
            # Send to company (primary), CC complainant
            body = build_lawyer_send_body(
                complaint.complainant.full_name, company_label, company_email,
            )
            result = send_notice_email(
                to_email=company_email,
                to_name=company_label,
                cc_emails=[complaint.complainant.email],
                subject=f"LEGAL NOTICE — {complaint.complainant.full_name} v. {company_label}",
                body_text=body,
                pdf_bytes=pdf_bytes,
                pdf_filename=f"Legal_Notice_{company_label.replace(' ', '_')}.pdf",
                request_read_receipt=True,
            )
            delivery.email_sent = result.success
            delivery.email_recipients = result.recipients
            delivery.email_message_id = result.message_id
            delivery.delivery_status = "served_to_company" if result.success else f"email_failed: {result.message}"

        return NoticePacket(
            complaint=complaint,
            company=company,
            contacts=contacts,
            policy_evidence=synthetic_policy,
            bare_act_references=bare_act_refs,
            claim_element_results=claim_element_results,
            respondent_identity=respondent_info,
            evidence_score=evidence_score_info,
            limitation_info=limitation_info,
            arbitration_info=arbitration_info,
            jurisdiction_info=jurisdiction_info,
            cure_period_info=cure_period_info,
            tc_counters=tc_counter_infos,
            required_user_uploads=self._required_user_uploads(complaint),
            legal_notice=legal_notice,
            delivery=delivery,
            generated_at=datetime.utcnow(),
        )
