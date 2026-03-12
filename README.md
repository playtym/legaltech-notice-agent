# Indian Legal Notice Agentic System

Agentic workflow to intake consumer complaints (typed or voice), discover company contacts, analyze policies, build persuasive legal arguments that dismantle company T&C defenses, and deliver a professionally formatted legal notice PDF — either for self-dispatch (₹199) or with lawyer review and direct service to the company (₹599).

## What this solves

- Captures complaint details from typed input or transcribed voice input (Hindi-English mixed OK).
- Uses website input to discover customer/legal contact channels.
- Extracts and analyzes company Terms & Conditions for potential defense clauses.
- **Argues like a seasoned consumer lawyer**: preemptively identifies and dismantles corporate T&C defenses (no-refund clauses, liability caps, arbitration clauses, sole-discretion terms, etc.) using Indian statutory provisions and precedent.
- Produces a **professional PDF legal notice** with statutory citations, bare-act text, and T&C counter-arguments.
- **Two pricing tiers**:
  - **₹199 Self-Send**: PDF emailed to complainant to send themselves
  - **₹599 Lawyer-Assisted**: Notice reviewed by an advocate, served directly to the company on advocate's letterhead with read-receipt tracking

## Important legal note

- This is a legal drafting support system, not a substitute for advice from a licensed advocate.
- Section matching is heuristic and should be validated by counsel before serving notice.
- This workflow is restricted to civil/consumer disputes only; criminal-law analysis and drafting are out of scope.

## Legal interpretation layer (India)

The current rules engine includes plausible mapping references such as:

- Consumer Protection Act, 2019: Section 2(47), Section 2(11), Section 35, Section 59 (product liability), Section 62 (punitive damages)
- Indian Contract Act, 1872: Section 73
- Specific Relief Act, 1963: Section 14 (specific performance)
- Information Technology Act, 2000: Section 43A (civil compensation context)
- Digital Personal Data Protection Act, 2023: Sections 8/13 (consent, breach notification)
- Consumer Protection (E-Commerce) Rules, 2020: Rules 4, 5, 6 (entity disclosure, pricing, cancellation)
- Payment and Settlement Systems Act, 2007: Section 18 read with RBI directions
- Sale of Goods Act, 1930: Section 16 (implied fitness warranty)

You can extend mappings in src/legaltech/legal_india.py.

## Architecture

- IntakeAgent: normalizes issue narrative, runs smell tests, Hinglish→English normalization.
- CompanyAgent: infers company profile from hint and website.
- ContactDiscoveryAgent: finds support/legal contacts from relevant pages.
- PolicyAgent: extracts policy evidence snippets from terms/refund/privacy pages.
- **LegalAnalysisAgent**: computes plausible sections + bare-act text + spirit/reasonableness view + risk flags. **Falls back to Claude for out-of-syllabus cases** — when the rule engine finds ≤2 keyword matches (e.g. social media account blocks, AI moderation disputes, platform delistings), Claude researches applicable Indian law and identifies 5-15 additional statutory provisions.
- ClaimElementsAgent: element-by-element civil claim checking (duty, breach, causation, loss, mitigation).
- RespondentIdAgent: scrapes CIN/LLPIN, registered office, grievance officer from website.
- EvidenceScoringAgent: scores evidence completeness/consistency, detects contradictions.
- **TCCounterAgent**: scans company T&Cs for 10+ common corporate defense patterns (no-refund, liability caps, force majeure, sole discretion, as-is disclaimers, deemed acceptance, etc.) and builds preemptive legal rebuttals with statutory basis and precedent.
- LimitationAgent: checks statutory limitation period, warns if claim is time-barred.
- ArbitrationDetectionAgent: scans policies for arbitration/ADR/jurisdiction clauses.
- JurisdictionAgent: determines District/State/National Commission and territorial jurisdiction.
- CurePeriodAgent: sets dynamic cure period (7–30 days) based on dispute type.
- **EscalationStrategyAgent**: auto-detects the company's industry and assembles multi-directional pressure tactics — sector-specific regulators, CCPA complaints, government portals (CPGRAMS/NCH/INGRAM), director personal liability (CPA §89), social media/review escalation, MCA/ROC non-compliance flags, DPDP Act complaints, GST refund flags, SEBI disclosure (listed companies), criminal remedy reservation, and a multi-stakeholder CC strategy. The goal: make the notice itself resolve the dispute without litigation.
- NoticeDraftAgent: produces a persuasive lawyerly legal notice that preemptively dismantles T&C defenses and includes the full escalation strategy.
- **PDFGenerator**: converts the notice text into a professionally formatted A4 letter PDF with headers, sections, legal quotes, and optional advocate attestation block.
- **EmailService**: delivers the PDF notice via SMTP — to complainant (self-send) or directly to the company (lawyer tier) with read-receipt tracking. Delivery is **email-only** (no postal dispatch).
- LegalNoticePipeline: orchestrates all agents, generates PDF, and delivers via email.

## Pricing tiers

| Tier | Price | What happens |
|------|-------|------|
| **Self-Send** | ₹199 | AI generates the full legal notice with T&C counter-arguments + escalation strategy → Professional PDF → Emailed to you with dispatch instructions |
| **Lawyer-Assisted** | ₹599 | Everything above + Advocate reviews and attests → Notice served to company via email from advocate's address with read-receipt tracking |

## API

### Health

- GET /health

### Pricing info

- GET /pricing — returns both tier descriptions and pricing

### Generate notice from typed complaint (JSON response)

- POST /notice/typed — returns full NoticePacket JSON with tier/delivery info
- Body: include `"tier": "self_send"` or `"tier": "lawyer"`

### Generate notice from typed complaint (PDF download)

- POST /notice/typed/pdf — returns the PDF file directly for download
- Body: same as /notice/typed

### Generate notice from voice transcript

- POST /notice/voice
- Body: includes `transcript_text` field, same tier options

## Setup

1. Create and activate a Python 3.11+ environment.
2. Install dependencies:

```bash
pip install -e .
```

3. Copy env template and set values:

```bash
cp .env.example .env
```

4. Run server:

```bash
uvicorn legaltech.app:app --reload
```

## Test quickly

```bash
# Self-send tier (₹199) — returns JSON with notice + delivery status
curl -X POST http://127.0.0.1:8000/notice/typed \
  -H "Content-Type: application/json" \
  -d @examples/typed_request.json

# Download PDF directly
curl -X POST http://127.0.0.1:8000/notice/typed/pdf \
  -H "Content-Type: application/json" \
  -d @examples/typed_request.json -o notice.pdf

# Check pricing
curl http://127.0.0.1:8000/pricing
```

## Make it production-ready

- Add advocate-in-the-loop approval workflow for ₹599 tier before dispatch.
- Integrate Razorpay/Cashfree for ₹199/₹599 payment before PDF generation.
- Keep legal notice output in English only for consistency and legal review workflows.
- Allow audio/text intake in mixed Hindi-English and normalize to English before legal drafting.
- Replace SMTP with transactional email (AWS SES / SendGrid) for deliverability.
- Add webhook for delivery/read-receipt status updates.

## Implemented features

- **Persuasive lawyerly argumentation**: Notice is drafted like a seasoned consumer lawyer — not a polite complaint letter. Uses assertive legal language, statutory framing, and credible litigation threat.
- **T&C counter-argument engine**: Detects 10+ corporate defense patterns (no-refund, liability caps, force majeure, sole discretion, as-is disclaimers, deemed acceptance, third-party disclaimers, exclusive jurisdiction, etc.) and builds preemptive rebuttals with statutory basis and case precedent (see `src/legaltech/agents/tc_counter_agent.py`).
- **Professional PDF output**: A4 legal letter PDF with proper formatting — title, address blocks, numbered sections, legal quotes, bullet points, and page numbering. Lawyer tier adds advocate attestation block (see `src/legaltech/services/pdf_generator.py`).
- **Email delivery**: Self-send tier emails PDF to complainant with dispatch instructions. Lawyer tier serves directly to company with read-receipt tracking (see `src/legaltech/services/email_service.py`).
- **Two pricing tiers**: ₹199 self-send, ₹599 lawyer-assisted. GET /pricing endpoint returns tier details.
- **Authoritative legal retrieval**: Curated bare-act text with amendment status and state-level rules for 12 statutory sections.
- **Element-by-element civil claim checks**: Each plausible section is evaluated for duty/breach/causation/loss/mitigation before citation.
- **Respondent identity verification**: Scrapes CIN/LLPIN, registered office, and grievance officer details from the company website.
- **Evidence consistency scoring**: Scores completeness and consistency; detects timeline contradictions and amount discrepancies.
- **Limitation period check**: Detects claim category and checks statutory limitation (2–3 years). Warns if time-barred.
- **Arbitration clause detection + rebuttal**: Detects arbitration/ADR clauses and preemptively cites CPA 2019 §2(7)(ii) and Emaar MGF (Supreme Court) to assert consumer forum jurisdiction.
- **Jurisdiction and forum determination**: Determines District/State/National Commission based on claim value with e-daakhil filing notes.
- **Dynamic cure period**: 7–30 days based on dispute type instead of static 15 days.
- **Proof-of-service guidance**: Email with read/delivery receipt.
- **SSRF protection**: Blocks requests to private/loopback/link-local IPs.
- **Input validation hardening**: Field-level max length constraints on all user inputs.
- **Claude legal research fallback**: When the rule engine's 12 keyword-mapped sections don't cover the complaint (e.g. social media page blocks, AI moderation disputes, platform account bans, SaaS delistings), Claude identifies 5-15 additional applicable Indian statutory provisions from its legal knowledge. This means the system handles *any* civil/consumer dispute, not just pre-mapped ones.
- **Escalation strategy engine**: Auto-detects industry (banking, e-commerce, telecom, airlines, real estate, insurance, food, auto, education, healthcare) and assembles multi-directional pressure tactics: sector regulators, CCPA/CPGRAMS/NCH, director personal liability, social media escalation, MCA/ROC flags, DPDP Board complaints, GST authority flags, SEBI disclosure, criminal remedy reservation, and multi-stakeholder CC service. Each tactic is a statement of intent that creates compliance pressure from multiple directions simultaneously.
- **Email-only delivery**: All notice delivery is via email (no RPAD/Speed Post). Self-send tier emails PDF to complainant with forwarding instructions. Lawyer tier serves directly to company from advocate's email with read-receipt tracking.
