#!/usr/bin/env python3
"""
Generate legal-notice-for-[type] landing pages for Lawly.
Mirrors eDrafter's Zapp cluster strategy.
Run: python3 gen_notice_pages.py
"""
import os

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

GA_TAG = """    <script async src="https://www.googletagmanager.com/gtag/js?id=G-F63GR76DSR"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', 'G-F63GR76DSR');
    </script>"""

STYLES = """
        body { font-family: 'Inter', sans-serif; background: #fafafa; color: #18181b; }
        .prose-legal h1 { font-size: 2rem; font-weight: 800; margin-bottom: 0.75rem; letter-spacing: -0.03em; line-height: 1.2; }
        .prose-legal h2 { font-size: 1.35rem; font-weight: 700; margin-top: 2.25rem; margin-bottom: 0.9rem; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.4rem; color: #111827; }
        .prose-legal h3 { font-size: 1.05rem; font-weight: 600; margin-top: 1.4rem; margin-bottom: 0.4rem; color: #1f2937; }
        .prose-legal p { margin-bottom: 1rem; line-height: 1.75; color: #4b5563; }
        .prose-legal ul, .prose-legal ol { padding-left: 1.75rem; margin-bottom: 1rem; color: #4b5563; }
        .prose-legal li { margin-bottom: 0.45rem; line-height: 1.7; }
        .prose-legal a { color: #2563eb; text-decoration: underline; }
        .prose-legal strong { color: #111827; }
        .cta-box { background: linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%); border-radius: 1rem; padding: 1.75rem; color: white; text-align: center; margin: 2.25rem 0; }
        .cta-box h3 { color: white; font-size: 1.2rem; font-weight: 700; margin-bottom: 0.4rem; }
        .cta-box p { color: #bfdbfe; margin-bottom: 1.1rem; }
        .info-box { background: #fef9c3; border: 1px solid #fde047; border-radius: 0.5rem; padding: 1rem 1.25rem; margin: 1.25rem 0; }
        .info-box p { margin-bottom: 0; color: #713f12; }
        .law-box { background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 0.5rem; padding: 1rem 1.25rem; margin: 1.25rem 0; }
        .law-box p { margin-bottom: 0.5rem; color: #0c4a6e; }
        .law-box p:last-child { margin-bottom: 0; }
        .step-list { counter-reset: step; list-style: none; padding: 0; }
        .step-list li { counter-increment: step; display: flex; gap: 1rem; align-items: flex-start; padding: 0.9rem 0; border-bottom: 1px solid #f3f4f6; }
        .step-list li:last-child { border-bottom: none; }
        .step-list li::before { content: counter(step); display: inline-flex; background: #1d4ed8; color: white; font-weight: 700; font-size: 0.78rem; min-width: 1.65rem; height: 1.65rem; border-radius: 50%; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 0.05rem; }
        .step-list li div strong { display: block; color: #111827; font-weight: 600; margin-bottom: 0.2rem; }
        .step-list li div p { margin: 0; color: #4b5563; font-size: 0.92rem; }
        .relief-tag { display: inline-block; background: #dcfce7; color: #166534; font-weight: 600; font-size: 0.8rem; padding: 0.2rem 0.6rem; border-radius: 9999px; margin: 0.2rem 0.2rem 0.2rem 0; }
"""

NAV = """    <nav class="bg-white/90 backdrop-blur-md border-b border-gray-100 sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">
        <div class="flex-shrink-0 flex items-center gap-2 cursor-pointer" onclick="window.location.href='/'">
            <div class="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center">
                <span class="text-white font-bold text-xl leading-none font-serif">L</span>
            </div>
            <span class="font-bold text-xl tracking-tight text-gray-900">Lawly</span>
        </div>
        <div class="hidden md:flex items-center space-x-6">
            <a href="/how-to-send-legal-notice-india" class="text-gray-500 hover:text-gray-900 text-sm font-medium">How to Send</a>
            <a href="/consumer-complaint-india" class="text-gray-500 hover:text-gray-900 text-sm font-medium">Consumer Complaints</a>
            <a href="/app" class="bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-gray-700 transition-colors">Generate Legal Notice</a>
        </div>
      </div>
    </div>
    </nav>"""

FOOTER = """    <footer class="border-t border-gray-200 mt-10 py-10">
        <div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex flex-col md:flex-row justify-between gap-4">
                <div>
                    <span class="font-bold text-gray-900">Lawly</span>
                    <p class="text-gray-500 text-sm mt-1">AI-powered legal notices for Indian consumers.</p>
                    <p class="text-gray-400 text-xs mt-1">© 2026 Lawly. All rights reserved.</p>
                </div>
                <div class="flex flex-wrap gap-x-5 gap-y-2 text-sm text-gray-500">
                    <a href="/" class="hover:text-gray-800">Home</a>
                    <a href="/consumer-complaint-india" class="hover:text-gray-800">Consumer Complaint Guide</a>
                    <a href="/how-to-send-legal-notice-india" class="hover:text-gray-800">How to Send Notice</a>
                    <a href="/app" class="hover:text-gray-800">Generate Notice</a>
                    <a href="/directory" class="hover:text-gray-800">All Guides</a>
                    <a href="/terms" class="hover:text-gray-800">Terms</a>
                </div>
            </div>
            <p class="text-gray-400 text-xs mt-4">Lawly provides legal information and document drafting, not legal advice. For complex matters, consult a qualified advocate.</p>
        </div>
    </footer>"""


PAGES = [
    {
        "slug": "legal-notice-for-refund",
        "title": "Legal Notice for Refund Not Received in India (2026) | Lawly",
        "meta_desc": "Send a legal notice for refund not received in India. Covers e-commerce refunds, service cancellations, and advance payments. Includes applicable law sections (CPA 2019, E-Commerce Rules), relief amounts, and step-by-step process.",
        "keywords": "legal notice for refund not received, legal notice for refund India, refund legal notice India, consumer legal notice for refund, legal notice refund e-commerce India",
        "canonical": "legal-notice-for-refund",
        "og_title": "Legal Notice for Refund Not Received in India (2026)",
        "og_desc": "How to send a legal notice when a company refuses your refund. Applies to e-commerce, service cancellations, and advance payments. Lawly generates the notice in 5 minutes.",
        "breadcrumb_parent": "How to Send Legal Notice",
        "breadcrumb_parent_url": "how-to-send-legal-notice-india",
        "badge": "Refund Disputes",
        "badge_color": "bg-green-100 text-green-800",
        "h1": "Legal Notice for Refund Not Received in India (2026)",
        "intro": "When a company refuses to refund money it legally owes you — whether for a cancelled e-commerce order, a defective product return, a subscription cancellation, or an advance payment — a legal notice is your most powerful first step. A properly drafted notice citing the Consumer Protection Act 2019 forces the company's legal team to review your case and typically resolves the matter within 15–30 days.",
        "quick_answer": "<strong>Short answer:</strong> Send a legal notice citing Section 2(11) of the Consumer Protection Act 2019 (deficiency in service) and Rule 6 of the E-Commerce Rules 2020 (for online purchases). State the exact refund amount, a 15-day deadline, and your intent to approach the Consumer Commission if unresolved. Use <a href='/app'>Lawly (₹199)</a> to generate the notice in 5 minutes.",
        "when_heading": "When Should You Send a Legal Notice for a Refund?",
        "when_points": [
            "You cancelled an e-commerce order and the refund was not credited within the promised or statutory timeline",
            "You returned a defective product and the replacement or refund was refused or ignored",
            "A service was cancelled (gym, OTT subscription, coaching, travel) and the provider refuses to issue the refund",
            "An advance payment was made for a service that was never rendered and the provider is unresponsive",
            "A company issued a coupon or store credit instead of the cash refund you are entitled to",
        ],
        "law_heading": "What the Law Says",
        "law_content": [
            "<strong>Consumer Protection Act 2019, Section 2(11)</strong> — Defines 'deficiency' to include any failure to perform the promised service, including non-refund after cancellation or non-delivery.",
            "<strong>Consumer Protection (E-Commerce) Rules 2020, Rule 6(5)</strong> — E-commerce entities must have a fair and transparent return and refund policy and must honour it. Refusing a legitimate refund is an unfair trade practice under Section 2(47) of CPA 2019.",
            "<strong>Consumer Protection Act 2019, Section 2(47)</strong> — 'Unfair trade practice' covers misleading advertisements, false guarantees, and deceptive practices on refund policies.",
            "<strong>Indian Contract Act 1872, Section 65</strong> — When an agreement is found void or when one party fails to perform, the other is entitled to restoration of any benefit received.",
        ],
        "relief_tags": ["Full refund of ₹X paid", "₹10,000–₹50,000 compensation for mental agony", "Interest at 9–12% p.a. on delayed refund", "Litigation costs ₹2,500–₹10,000"],
        "relief_note": "Consumer forums routinely award compensation equal to 2–3× the refund amount for willful refusal. A legal notice citing specific statute sections significantly increases the settlement amount companies are willing to offer.",
        "steps": [
            ("Gather your refund evidence", "Collect: order confirmation, payment receipt, cancellation confirmation email/SMS, any communication from the company about the refund, and the bank statement showing the charge was not reversed."),
            ("Identify the correct legal entity", "The notice must be sent to the company's registered legal name and registered office — not just the brand. Find this on <a href='https://www.mca.gov.in' target='_blank' rel='noopener'>mca.gov.in</a> or the company's Terms of Service. Also address a copy to the Grievance Officer (mandatory for e-commerce companies under E-Commerce Rules 2020)."),
            ("Generate or draft the legal notice", "Use <a href='/app'>Lawly (₹199)</a> to generate a notice citing the exact applicable sections. The notice must state: the amount paid, the date of cancellation/refund request, the company's failure to refund, and a 15-day deadline for repayment. It should threaten Consumer Commission proceedings if unresolved."),
            ("Send by Registered Post AD", "Print and send to the registered office by Registered Post with Acknowledgement Due (RPAD) at any India Post branch (₹50–₹100). Also send a copy to the Grievance Officer by email with read receipt. Keep the tracking receipt and the returned red card."),
            ("Wait for the deadline, then escalate if needed", "If unresolved after 15 days, file on <a href='https://edaakhil.nic.in' target='_blank' rel='noopener'>EDAAKHIL</a> (Consumer Forum e-filing portal). Attach the notice and postal proof as Exhibit A. Filing fee: ₹100 for claims up to ₹5 lakh."),
        ],
        "faqs": [
            ("Is it mandatory to send a legal notice before claiming a refund through Consumer Court?", "No — it is not legally mandatory under the Consumer Protection Act 2019. You can file on EDAAKHIL directly. However, sending a notice first is strongly recommended: ~60% of refund disputes resolve within 30 days of a correctly worded legal notice, saving months of Forum proceedings."),
            ("What is the legal notice format for refund?", "A legal notice for refund must include: your name and address, company's registered name and address, date, a chronological account of the transaction and refund failure, citation of CPA 2019 §2(11) and E-Commerce Rules 2020 Rule 6(5), exact refund amount demanded, and a 15-day response deadline. See the <a href='/legal-notice-format-india'>free format here</a>."),
            ("What if the company says the refund was processed but I haven't received it?", "Ask the company for the UTR (Unique Transaction Reference) number of the refund. If no UTR is provided and the bank confirms no credit, you can proceed with the legal notice. The bank statement is your evidence."),
            ("How much compensation can I claim for a delayed refund?", "Beyond the refund itself, consumer forums award ₹5,000–₹50,000 for mental agony depending on the duration of delay and company conduct, plus litigation costs. For amounts under ₹5 lakh, the District Commission handles the case with ₹100 filing fee."),
        ],
        "related_links": [
            ("Legal notice format India", "/legal-notice-format-india"),
            ("How to send legal notice", "/how-to-send-legal-notice-india"),
            ("File on EDAAKHIL (free)", "/how-to-file-consumer-complaint-online"),
            ("Amazon refund complaints", "/amazon-complaints"),
            ("Flipkart refund complaints", "/flipkart-complaints"),
            ("Consumer court online", "/consumer-court-online-complaint"),
        ],
    },
    {
        "slug": "legal-notice-defective-product",
        "title": "Legal Notice for Defective Product in India (2026) | Lawly",
        "meta_desc": "Send a legal notice for a defective or counterfeit product in India. Covers CPA 2019 product liability (Chapter VI), Section 2(10), and what compensation you can claim. Lawly generates the notice in 5 minutes.",
        "keywords": "legal notice defective product India, legal notice for defective goods India, consumer legal notice defective product, product liability legal notice India, legal notice wrong product delivered India",
        "canonical": "legal-notice-defective-product",
        "og_title": "Legal Notice for Defective Product in India (2026)",
        "og_desc": "How to send a legal notice for a defective, counterfeit, or substandard product under CPA 2019 Chapter VI product liability. Statute citations, relief amounts, and step-by-step process.",
        "breadcrumb_parent": "How to Send Legal Notice",
        "breadcrumb_parent_url": "how-to-send-legal-notice-india",
        "badge": "Product Defect",
        "badge_color": "bg-red-100 text-red-800",
        "h1": "Legal Notice for Defective Product in India (2026)",
        "intro": "Receiving a defective, counterfeit, or substandard product is a clear violation of your consumer rights under the Consumer Protection Act 2019. Whether you bought it from Amazon, Flipkart, a brand's own website, or a local retailer, you are entitled to a free replacement, full refund, or compensation. A legal notice citing the product liability provisions of CPA 2019 is the fastest path to resolution — most companies settle within 15–30 days rather than face a Consumer Commission proceeding.",
        "quick_answer": "<strong>Short answer:</strong> Send a legal notice citing Section 2(10) of CPA 2019 (defect in goods) and Chapter VI (product liability — manufacturer, seller, and service provider liability). State the defect clearly, your demanded relief (replacement or refund + compensation), and a 15-day deadline. Generate in 5 minutes at <a href='/app'>Lawly (₹199)</a>.",
        "when_heading": "When Should You Send a Legal Notice for a Defective Product?",
        "when_points": [
            "The product is broken, non-functional, or damaged on delivery",
            "The product is different from what was described or advertised (wrong model, colour, size, or brand)",
            "The product is counterfeit or fake — not the genuine branded item you paid for",
            "The product fails or malfunctions within the warranty period and the company refuses to repair/replace",
            "The product causes physical injury or property damage due to a manufacturing defect",
            "Expired food, medicines, or consumables were delivered by an e-commerce or quick commerce platform",
        ],
        "law_heading": "What the Law Says",
        "law_content": [
            "<strong>CPA 2019, Section 2(10)</strong> — Defines 'defect' broadly: any fault, imperfection, shortcoming, or inadequacy in quality, quantity, potency, purity, or standard that is required by law, contract, or claimed by the seller. This covers wrong items, damaged goods, and counterfeit products.",
            "<strong>CPA 2019, Chapter VI — Product Liability (Sections 82–87)</strong> — Manufacturer (<a href='#'>§83</a>), product service provider (§84), and product seller (§85) are all separately liable for harm caused by a defective product. A product seller is liable if they did not exercise reasonable care in assembling, inspecting, or maintaining the product. You can sue the seller even if the manufacturer is overseas.",
            "<strong>CPA 2019, Section 2(11)</strong> — 'Deficiency in service' also applies when a seller fails to replace or refund a defective product within a reasonable time.",
            "<strong>Bureau of Indian Standards Act 2016</strong> — Products in notified categories must bear ISI certification. Selling non-ISI products in these categories is an additional violation.",
        ],
        "relief_tags": ["Free replacement with same model", "Full refund of purchase price", "Compensation for consequential damage caused by defect", "₹10,000–₹1,00,000 for mental agony", "Recall of defective batch (for class actions via CCPA)"],
        "relief_note": "Under Chapter VI product liability, you can claim compensation for personal injury or property damage caused by the defective product — not just the product cost. This is in addition to the replacement/refund.",
        "steps": [
            ("Document the defect thoroughly", "Photograph or video the defect, damaged packaging, wrong item, and the delivery box with the shipping label (showing delivery address and order ID). This is your core evidence."),
            ("Raise a complaint with the company first", "Contact the company's customer support and document the interaction (support ticket number, email, chat screenshot). Most consumer forums expect you to have attempted resolution through the company's own channels first."),
            ("Generate the legal notice", "Use <a href='/app'>Lawly</a> to generate a notice citing CPA 2019 §2(10) and Chapter VI. Clearly describe the defect, attach photo/video references as Annexures, state whether you want replacement or refund + compensation, and set a 15-day deadline."),
            ("Send to manufacturer and seller both", "For product defects, send the notice to both the seller (e.g., Amazon/Flipkart) and the manufacturer (the brand). Under Chapter VI, both are independently liable. The manufacturer's registered address is typically on the product packaging."),
            ("Escalate to Consumer Forum if unresolved", "File on EDAAKHIL after the 15-day deadline. For product liability matters, include the product photos, packaging, and purchase proof as exhibits. The Forum can order replacement, refund, and additional compensation."),
        ],
        "faqs": [
            ("Can I get compensation beyond the product price for a defective product?", "Yes. Under CPA 2019 Chapter VI product liability, you can claim compensation for any injury to health, safety, or property caused by the defective product — in addition to the product refund/replacement. Consumer forums also award ₹10,000–₹1,00,000 for mental agony depending on the severity of the defect and the company's conduct."),
            ("Who is liable — the seller (Amazon/Flipkart) or the manufacturer?", "Under CPA 2019 §85, the product seller (Amazon, Flipkart, the store) is separately liable if they sold a defective product. Under §83, the manufacturer is also liable. You can send notices to both and include both as Opposite Parties in your Forum complaint."),
            ("What if the product was received damaged but I already accepted delivery?", "It doesn't matter. Accepting delivery does not waive your right to claim for a defective product. You must raise the complaint within a reasonable time (and before the 2-year limitation period under CPA 2019 §69). Photograph the defect and file within a few days of discovery."),
            ("Can I file a legal notice for an expired food product from Zomato, Swiggy, or Blinkit?", "Yes — and it is a criminal offence. Selling expired food violates FSSA 2006 §59 (up to 6 months imprisonment + ₹5 lakh fine). The quick commerce platform is a Food Business Operator. File both a consumer legal notice and a complaint with FSSAI."),
        ],
        "related_links": [
            ("Legal notice format India", "/legal-notice-format-india"),
            ("How to send legal notice", "/how-to-send-legal-notice-india"),
            ("Fake products Amazon Flipkart guide", "/fake-products-amazon-flipkart"),
            ("Defective electronics guide", "/defective-electronics"),
            ("Consumer complaint India", "/consumer-complaint-india"),
            ("File on EDAAKHIL", "/how-to-file-consumer-complaint-online"),
        ],
    },
    {
        "slug": "legal-notice-cheque-bounce",
        "title": "Cheque Bounce Legal Notice in India — Section 138 NI Act (2026) | Lawly",
        "meta_desc": "How to send a cheque bounce legal notice in India under Section 138 of the Negotiable Instruments Act. Strict 30-day deadline applies. Lawly generates the correct notice in 5 minutes.",
        "keywords": "cheque bounce legal notice India, legal notice cheque bounce section 138, dishonoured cheque notice India, NI act section 138 notice format, cheque bounce notice 30 days India",
        "canonical": "legal-notice-cheque-bounce",
        "og_title": "Cheque Bounce Legal Notice India — Section 138 NI Act (2026)",
        "og_desc": "Section 138 demand notice for a dishonoured cheque in India. Strict 30-day deadline from bank return memo. Includes correct format, timeline, and what happens if no reply.",
        "breadcrumb_parent": "How to Send Legal Notice",
        "breadcrumb_parent_url": "how-to-send-legal-notice-india",
        "badge": "Cheque Bounce · Section 138",
        "badge_color": "bg-orange-100 text-orange-800",
        "h1": "Cheque Bounce Legal Notice in India — Section 138 NI Act (2026)",
        "intro": "A cheque bounce notice under Section 138 of the Negotiable Instruments Act 1881 is one of the most time-critical legal notices in Indian law. You have a <strong>strict 30-day window</strong> from the date the bank returns the cheque memo to send the demand notice. Miss this deadline and you lose your right to prosecute under Section 138 permanently. If the drawer does not pay within 15 days of receiving your notice, you can file a criminal complaint — which can result in imprisonment of up to 2 years plus fine equal to or double the cheque amount.",
        "quick_answer": "<strong>Critical timeline:</strong> Bank returns cheque → receive the return memo → send Section 138 demand notice within 30 days → drawer has 15 days to pay → if not paid, file criminal complaint in the Magistrate's Court within 30 days. Do not delay. Generate your notice at <a href='/app'>Lawly</a>.",
        "when_heading": "When Does Section 138 Apply?",
        "when_points": [
            "A cheque was issued for discharge of a debt or legally enforceable liability (not a gift or deposit cheque)",
            "The cheque was deposited within 3 months of its date",
            "The bank returned it for reasons such as: insufficient funds, 'payment stopped by drawer', account closed, or signature mismatch",
            "You have received the bank's return memo (the official notice of dishonour)",
        ],
        "law_heading": "What the Law Says",
        "law_content": [
            "<strong>Negotiable Instruments Act 1881, Section 138</strong> — Makes it a criminal offence to issue a cheque for a legally enforceable liability that is returned unpaid due to insufficient funds or stop payment. Punishment: imprisonment up to 2 years, or fine up to double the cheque amount, or both.",
            "<strong>NI Act, Section 138 Proviso (b)</strong> — The payee must send a written demand notice to the drawer within 30 days of receiving the bank return memo. This notice is mandatory — without it, no prosecution can proceed.",
            "<strong>NI Act, Section 138 Proviso (c)</strong> — The drawer must repay within 15 days of receiving the demand notice. If they fail to pay, the criminal offence is deemed to have occurred.",
            "<strong>NI Act, Section 142</strong> — The complaint must be filed within 30 days of the expiry of the 15-day period given in the demand notice. Jurisdiction: where the cheque was delivered (where the payee banks).",
        ],
        "relief_tags": ["Full cheque amount", "Interest at 18% p.a. on delayed payment", "Fine up to 2× cheque amount (criminal proceeding)", "Up to 2 years imprisonment for drawer (if convicted)", "Civil suit for recovery simultaneously"],
        "relief_note": "Section 138 is a criminal offence — the drawee can be prosecuted even while a civil suit for money recovery is pending. The threat of criminal prosecution is often sufficient to recover the cheque amount quickly.",
        "steps": [
            ("Obtain the bank return memo", "When your bank returns the cheque, get the official return memo citing the reason (insufficiency of funds, stop payment, etc.). This is the starting point of the 30-day window."),
            ("Send the Section 138 demand notice within 30 days", "This is the most critical step. The notice must: (a) state the cheque details (number, date, amount, bank), (b) inform the drawer the cheque was returned dishonoured, (c) demand payment of the full cheque amount, (d) state that failure to pay within 15 days will result in criminal proceedings under NI Act §138. Use <a href='/app'>Lawly</a> to generate the correctly formatted notice."),
            ("Send by Registered Post AD", "Send by Registered Post with Acknowledgement Due (RPAD). This is especially critical for Section 138 — the court requires proof that the notice was sent and the start date of the 15-day period. Keep the tracking receipt and the returned acknowledgement card."),
            ("Wait 15 days from receipt of notice", "If the drawer pays within this period, your dispute is resolved. Get the payment in writing. If not, proceed to file a criminal complaint."),
            ("File criminal complaint in Magistrate's Court", "If the drawer does not pay within 15 days, file the Section 138 criminal complaint in the Jurisdictional Magistrate Court within 30 days of the expiry of the 15-day period. Attach: original cheque, bank return memo, demand notice, postal receipt, postal acknowledgement card, and a sworn affidavit."),
        ],
        "faqs": [
            ("What is the time limit to send a cheque bounce legal notice?", "You must send the Section 138 demand notice within 30 days of receiving the bank's return memo (cheque dishonour note). This is a statutory deadline — missing it means you cannot prosecute under Section 138 at all. If you've already missed it, you can still file a civil suit for recovery of money, but you lose the criminal remedy."),
            ("What should the Section 138 demand notice say?", "The notice must state: (1) the cheque details — number, date, bank, drawee account, amount; (2) that the cheque was presented and dishonoured on [date] citing [reason from return memo]; (3) a demand for payment of ₹[amount] within 15 days; (4) that failure to pay within 15 days will result in criminal proceedings under NI Act §138. The notice must be in writing and sent to the drawer's known address."),
            ("Can I send the cheque bounce notice by email?", "The law requires 'written notice' — email may satisfy this in some courts, but Registered Post AD is strongly recommended as the gold standard. Several High Court judgments have upheld that RPAD creates a presumption of delivery even if the drawer refuses to accept the envelope."),
            ("What happens if the drawer refuses to accept the registered post envelope?", "Under Indian Evidence Act §27, if a notice sent by registered post is returned unclaimed or refused, courts generally presume it was served. Keep the returned envelope — it is evidence of attempted service."),
        ],
        "related_links": [
            ("Legal notice format India", "/legal-notice-format-india"),
            ("How to send legal notice", "/how-to-send-legal-notice-india"),
            ("Recovery of money guide", "/legal-notice-recovery-of-money"),
            ("Consumer complaint India", "/consumer-complaint-india"),
            ("Consumer court online", "/consumer-court-online-complaint"),
            ("File on EDAAKHIL", "/how-to-file-consumer-complaint-online"),
        ],
    },
    {
        "slug": "legal-notice-recovery-of-money",
        "title": "Legal Notice for Recovery of Money in India (2026) | Lawly",
        "meta_desc": "Send a legal notice for recovery of money in India — unpaid loans, pending dues, security deposits, or advance payments. Covers Indian Contract Act §73, CPA 2019, and the correct format.",
        "keywords": "legal notice for recovery of money India, money recovery legal notice India, legal notice unpaid dues India, legal notice for loan recovery India, recovery notice India",
        "canonical": "legal-notice-recovery-of-money",
        "og_title": "Legal Notice for Recovery of Money in India (2026)",
        "og_desc": "How to send a money recovery legal notice in India. Covers personal loans, security deposits, advance payments, unpaid invoices. Template and step-by-step process.",
        "breadcrumb_parent": "How to Send Legal Notice",
        "breadcrumb_parent_url": "how-to-send-legal-notice-india",
        "badge": "Money Recovery",
        "badge_color": "bg-yellow-100 text-yellow-800",
        "h1": "Legal Notice for Recovery of Money in India (2026)",
        "intro": "When someone owes you money — a personal loan to a friend or family member, a security deposit from a tenant or landlord, an advance paid for services never rendered, or an unpaid business invoice — a formal legal notice is the most effective first step to recover it without going to court. In many cases, a well-drafted legal notice citing the Indian Contract Act and the Consumer Protection Act causes immediate repayment, because litigation is expensive and time-consuming for the debtor too.",
        "quick_answer": "<strong>Short answer:</strong> A money recovery notice must state the amount owed, the basis of the debt (contract, loan agreement, invoice), the applicable law section, a demand for repayment with interest within 15–30 days, and your intent to file a civil suit or consumer complaint if unresolved. Generate yours in 5 minutes at <a href='/app'>Lawly (₹199)</a>.",
        "when_heading": "When Should You Send a Money Recovery Legal Notice?",
        "when_points": [
            "A friend, family member, or colleague has not repaid a personal loan despite repeated requests",
            "A tenant has not returned your security deposit after vacating",
            "A landlord has not returned your security deposit and is making false deduction claims",
            "An advance paid to a service provider (contractor, vendor, consultant) was never applied to work and is being withheld",
            "A client has not paid your invoice despite multiple follow-ups and payment is overdue",
            "An employer has not paid pending salary, gratuity, or full-and-final settlement dues",
        ],
        "law_heading": "What the Law Says",
        "law_content": [
            "<strong>Indian Contract Act 1872, Section 73</strong> — When a contract is broken, the party who suffers from the breach is entitled to receive compensation for any loss or damage caused to them. This covers any agreement to repay money — oral or written.",
            "<strong>Indian Contract Act 1872, Section 65</strong> — Obliges a person who has received benefit under an agreement to restore that benefit (or make compensation) when the agreement becomes void or is not performed.",
            "<strong>Consumer Protection Act 2019, Section 2(11)</strong> — If the money owed relates to a consumer service (advance paid for services, security deposit to a builder/landlord where it constitutes a consumer transaction), this section applies, allowing filing at the Consumer Forum.",
            "<strong>Civil Procedure Code 1908, Order XXXVII (Summary Suit)</strong> — For money recovery exceeding a certain threshold, you can file a summary suit for faster recovery without a full trial, if the debt is based on a written contract, bill, or promissory note.",
        ],
        "relief_tags": ["Principal debt amount", "Interest at 18% p.a. from date of default", "Compensation for mental agony (consumer cases)", "Litigation costs", "Punitive damages (for willful refusal)"],
        "relief_note": "For personal loan recoveries, the interest rate is typically what was agreed in the loan agreement, or the legal rate of 6–18% p.a. if not specified. Consumer forums can award additional compensation for mental harassment.",
        "steps": [
            ("Gather all evidence of the debt", "Collect: the loan agreement or written undertaking (if any), WhatsApp/email conversations referencing the loan or advance, bank transfer receipts, invoices, prior demand messages, and any partial repayments made."),
            ("Calculate the total amount owed", "Add the principal amount + interest accrued since the default date. State this clearly in your notice. Be specific — 'I am owed ₹1,00,500 comprising ₹1,00,000 principal and ₹500 interest at 18% p.a. for 1 month.'"),
            ("Draft the legal notice", "Use <a href='/app'>Lawly</a> to generate a notice citing Indian Contract Act §73. State the nature of the debt, all prior demands made and ignored, the total amount demanded, a 15-day deadline, and your intent to file a civil suit or consumer complaint."),
            ("Send by Registered Post AD", "Send to the debtor's residential or office address by Registered Post with AD. If the debtor is a business, send to their registered office address. Keep all postal proof."),
            ("Choose the right escalation path", "If unresolved: (a) For consumer transactions — file on <a href='https://edaakhil.nic.in' target='_blank' rel='noopener'>EDAAKHIL</a> (faster, cheaper, no lawyer needed). (b) For personal loans/commercial debts — file a civil suit for recovery in the appropriate Civil Court or approach Lok Adalat for a conciliation settlement."),
        ],
        "faqs": [
            ("Can I send a legal notice for a personal loan between friends?", "Yes. Money lent to a friend or family member constitutes a contract under Indian law, even if it was verbal. The legal notice should reference any messages, calls, or emails where the loan was acknowledged. While oral loans are harder to enforce in court, a legal notice often prompts repayment without litigation."),
            ("What is the limitation period to file a suit for money recovery in India?", "Under the Limitation Act 1963, the limitation period for money recovery suits is 3 years from the date the debt became due. After 3 years, your legal right to sue may be barred — so act promptly. Sending a legal notice before the limitation period ends is important."),
            ("Can I charge interest in my legal notice?", "Yes. If a rate was agreed upon, charge that rate. If no rate was agreed, courts typically allow 6–18% p.a. (often 9% as a default). State the interest rate explicitly in your notice to make your demand enforceable."),
            ("What if the person says they don't have the money?", "The debtor's financial situation is not a defence to the legal obligation to repay. The legal notice puts your claim formally on record. In a court proceeding, the court can order sale of the debtor's assets to satisfy the judgment. Continue with the escalation path regardless."),
        ],
        "related_links": [
            ("Legal notice format India", "/legal-notice-format-india"),
            ("How to send legal notice", "/how-to-send-legal-notice-india"),
            ("Cheque bounce legal notice", "/legal-notice-cheque-bounce"),
            ("File on EDAAKHIL", "/how-to-file-consumer-complaint-online"),
            ("Consumer complaint India", "/consumer-complaint-india"),
            ("Consumer court online", "/consumer-court-online-complaint"),
        ],
    },
    {
        "slug": "legal-notice-insurance-claim-rejected",
        "title": "Legal Notice for Insurance Claim Rejected in India (2026) | Lawly",
        "meta_desc": "Send a legal notice when your insurance claim is rejected in India. Covers health insurance, life insurance, and motor insurance. Cites IRDAI Regulation 17(7) and Insurance Act §45. Lawly generates your notice in 5 minutes.",
        "keywords": "legal notice insurance claim rejected India, insurance claim rejection legal notice, legal notice health insurance rejected India, IRDAI complaint legal notice, insurance ombudsman legal notice India",
        "canonical": "legal-notice-insurance-claim-rejected",
        "og_title": "Legal Notice for Insurance Claim Rejected in India (2026)",
        "og_desc": "How to challenge an insurance claim rejection in India with a legal notice citing IRDAI Regulation 17(7) and Insurance Act §45. Includes escalation matrix and what compensation you can claim.",
        "breadcrumb_parent": "How to Send Legal Notice",
        "breadcrumb_parent_url": "how-to-send-legal-notice-india",
        "badge": "Insurance Disputes",
        "badge_color": "bg-blue-100 text-blue-800",
        "h1": "Legal Notice for Insurance Claim Rejected in India (2026)",
        "intro": "Insurance companies in India are legally required to give specific written reasons for rejecting a claim and to resolve claims within defined timelines under IRDAI regulations. If your health insurance, life insurance, or motor insurance claim was rejected without adequate reason, or if you suspect the rejection violates the terms of your policy, a legal notice is your most effective tool to challenge it — before approaching the Insurance Ombudsman or Consumer Forum.",
        "quick_answer": "<strong>Short answer:</strong> Send a legal notice citing IRDAI (Protection of Policyholders' Interests) Regulations 2017, Regulation 17(7) — requiring specific written reasons for rejection within 30 days — and Insurance Act 1938 §45 (prohibition on repudiation after 3 years). State the claim amount, the basis for rejection you dispute, and demand settlement within 15 days. Generate at <a href='/app'>Lawly (₹199)</a>.",
        "when_heading": "When Should You Send a Legal Notice for an Insurance Claim Rejection?",
        "when_points": [
            "Your health insurance cashless or reimbursement claim was rejected without a written, specific reason",
            "A life insurance death/maturity claim was repudiated citing 'non-disclosure' after the policy has been in force for more than 3 years",
            "Your motor insurance claim was rejected after an accident with grounds you believe are incorrect",
            "The insurer has not settled your claim within 30 days of submitting all required documents",
            "An insurer reduced your claim amount drastically without providing a reasoned survey report",
            "Your critical illness or disability rider claim was denied despite the condition being covered under the policy",
        ],
        "law_heading": "What the Law Says",
        "law_content": [
            "<strong>IRDAI (Protection of Policyholders' Interests) Regulations 2017, Regulation 17(7)</strong> — Insurers must communicate their decision on a claim — settlement or repudiation — within 30 days of submission of all required documents. Repudiation must be communicated with specific, written reasons. Vague rejections citing 'policy terms' without specifics violate this regulation.",
            "<strong>Insurance Act 1938, Section 45</strong> — An insurer cannot repudiate a life insurance policy for alleged non-disclosure of material fact after the policy has been in force for 3 years. Beyond 3 years, the insurer can only challenge a claim citing proven deliberate fraud, not inadvertent non-disclosure.",
            "<strong>Consumer Protection Act 2019, Section 2(11)</strong> — Unjustified rejection of an insurance claim is a 'deficiency in service.' Insurance is a 'service' under CPA 2019, making the Consumer Commission a highly effective forum — faster than civil courts.",
            "<strong>IRDAI Insurance Ombudsman Rules 2017</strong> — For disputes up to ₹30 lakh, the Insurance Ombudsman in your city can adjudicate free of charge. This is often faster than the Consumer Forum for insurance claims.",
        ],
        "relief_tags": ["Full claim amount as per policy", "Interest at 9–12% p.a. on delayed settlement", "Penalty under IRDAI regulations", "₹20,000–₹2,00,000 compensation from Consumer Forum", "Litigation costs"],
        "relief_note": "Consumer forums have awarded substantial compensation against insurers — often 25–50% of the claim amount as additional damages for mental harassment and bad-faith rejection. Insurance Ombudsman awards are fast (typically 3 months) and binding on the insurer.",
        "steps": [
            ("Obtain the rejection letter and analyse it", "Get the specific written reason for rejection from the insurer in writing (as mandated by IRDAI Regulation 17(7)). Compare the stated reason against your actual policy document's exclusion clauses and the facts of your claim."),
            ("Gather your claim documents", "Collect: policy document, premium receipts, original claim form, all medical/survey reports submitted, hospital bills, surveyor report (for motor/property), correspondence with the insurer, and the rejection letter."),
            ("Send a legal notice to the insurer's grievance officer", "Use <a href='/app'>Lawly</a> to generate a notice citing IRDAI Regulation 17(7) and CPA 2019 §2(11). Clearly state why the rejection reason is incorrect by referencing the specific policy clause and your factual situation. Demand settlement within 15 days."),
            ("Escalate to Insurance Ombudsman if unresolved", "If the insurer doesn't respond within 15 days: file with the <strong>Insurance Ombudsman</strong> (<a href='https://igms.irda.gov.in' target='_blank' rel='noopener'>igms.irda.gov.in</a>) for claims up to ₹30 lakh. This is free and typically resolves in 3 months."),
            ("File with Consumer Forum for larger amounts", "For claims above ₹30 lakh, or if the Ombudsman doesn't help, file on EDAAKHIL against the insurance company as the Opposite Party. Insurance disputes at the Forum typically take 6–12 months but can yield significant additional compensation."),
        ],
        "faqs": [
            ("Can I challenge a health insurance claim rejection after 3 years of the policy?", "Yes — in fact, for life insurance, Insurance Act §45 prohibits the insurer from repudiating a policy for non-disclosure after 3 years. For health insurance, the IRDAI Reg. 17(7) right applies regardless of policy age. If the rejection reason is incorrect or vague, you can challenge it."),
            ("What compensation can I get if my insurance claim is wrongly rejected?", "Besides the full claim amount, consumer forums regularly award 10–25% of the claim value as compensation for mental agony and harassment from wrongful rejection, plus interest on the delayed amount and litigation costs. In egregious cases, punitive damages have been awarded."),
            ("Is the Insurance Ombudsman free?", "Yes. The Insurance Ombudsman service is completely free. There are 17 offices across India. Filing is online via igms.irda.gov.in. The Ombudsman can award up to ₹30 lakh. The insurer pays all costs if they lose."),
            ("What if the rejection cites 'pre-existing disease' incorrectly?", "IRDAI regulations define what constitutes a pre-existing disease for disclosure purposes. If the condition you were treated for was not known to you at the time of buying the policy, it may not be a 'pre-existing condition' in the legal sense. Cite this specific regulatory definition in your legal notice."),
        ],
        "related_links": [
            ("Legal notice format India", "/legal-notice-format-india"),
            ("How to send legal notice", "/how-to-send-legal-notice-india"),
            ("Insurance claim rejection guide", "/insurance-claim-rejected"),
            ("Consumer complaint India", "/consumer-complaint-india"),
            ("File on EDAAKHIL", "/how-to-file-consumer-complaint-online"),
            ("Consumer helpline numbers", "/consumer-helpline-numbers"),
        ],
    },
    {
        "slug": "legal-notice-builder-delay",
        "title": "Legal Notice to Builder for Delay in Possession in India — RERA 2016 | Lawly",
        "meta_desc": "Send a legal notice to a builder for delay in possession under RERA 2016 Section 18. Claim SBI MCLR+2% interest on all payments made. Lawly generates the notice citing exact RERA provisions in 5 minutes.",
        "keywords": "legal notice builder delay possession, legal notice to builder for delay in possession India, RERA legal notice builder, possession delay legal notice India, builder delay compensation legal notice RERA",
        "canonical": "legal-notice-builder-delay",
        "og_title": "Legal Notice to Builder for Delay in Possession — RERA 2016 India",
        "og_desc": "How to send a legal notice for builder delay in possession under RERA 2016 §18. Claim SBI MCLR+2% interest or full refund. Lawly generates the correct RERA notice in 5 minutes.",
        "breadcrumb_parent": "How to Send Legal Notice",
        "breadcrumb_parent_url": "how-to-send-legal-notice-india",
        "badge": "RERA · Builder Delay",
        "badge_color": "bg-purple-100 text-purple-800",
        "h1": "Legal Notice to Builder for Delay in Possession — RERA 2016 (2026)",
        "intro": "If your builder has not handed over possession of your apartment, house, or commercial unit by the date promised in the Allotment Letter or Agreement to Sell, you are legally entitled to interest compensation under RERA 2016 Section 18 — calculated at SBI MCLR + 2% per annum on every rupee you have paid. A legal notice to the builder is the first formal step, followed by a complaint before the Real Estate Regulatory Authority (RERA) of your state if unresolved.",
        "quick_answer": "<strong>Short answer:</strong> Send a legal notice to the builder's registered address citing RERA 2016 Section 18 and CPA 2019 Section 2(11). Demand either: (a) immediate possession + interest for delay period, or (b) full refund with interest at SBI MCLR + 2% on all payments from the possession date. Give a 30-day deadline. Generate at <a href='/app'>Lawly (₹199)</a>.",
        "when_heading": "When Should You Send a Legal Notice for Builder Delay?",
        "when_points": [
            "The possession date stated in your Agreement to Sell or Allotment Letter has passed and no possession has been offered",
            "The builder obtained an occupation certificate (OC) but refuses to give you possession due to pending dues they are disputing",
            "The builder keeps citing construction delays, material shortages, or government approvals without providing a firm revised possession date",
            "You have been paying EMIs on a home loan for months/years without possession and want to reclaim the interest cost from the builder",
            "The builder sent a demand notice for the final payment but has not applied for or obtained the OC",
        ],
        "law_heading": "What the Law Says",
        "law_content": [
            "<strong>RERA 2016, Section 18(1)</strong> — If the promoter (builder) fails to complete construction or is unable to give possession by the date specified in the Agreement, the allottee (buyer) is entitled to: (a) withdraw from the project and receive full refund of the amount paid with interest at the prescribed rate (SBI MCLR + 2%), OR (b) continue with the agreement and receive interest for every month of delay from the promised possession date.",
            "<strong>RERA 2016, Section 18(2)</strong> — If an allottee decides to withdraw, the builder must refund the amount with interest within 45 days.",
            "<strong>RERA 2016, Section 18(3)</strong> — If the allottee suffers any other loss due to the delay, the builder is liable to pay compensation as determined by the Adjudicating Officer.",
            "<strong>Consumer Protection Act 2019, Section 2(11)</strong> — Delay in possession is a classic 'deficiency in service.' Buyers can approach both RERA and the Consumer Forum. Generally, RERA is the primary route under Section 79 of RERA 2016, but Consumer Forums continue to hear older cases.",
        ],
        "relief_tags": ["Interest at SBI MCLR+2% on all EMIs paid", "Full refund + SBI MCLR+2% interest (if you choose to withdraw)", "Compensation for home loan interest paid during delay", "₹50,000–₹5,00,000 additional compensation for Consumer Forum cases", "Builder liable to pay refund within 45 days of withdrawal request"],
        "relief_note": "The interest rate as of April 2026 under SBI MCLR+2% is approximately 10.55–11% p.a. On a ₹50 lakh payment delayed by 2 years, the interest alone is approximately ₹5–5.5 lakh — a significant amount that builders often prefer to settle rather than face RERA proceedings.",
        "steps": [
            ("Calculate your interest claim", "List every payment made to the builder with the date and amount. The RERA interest starts from the promised possession date (as per the Agreement to Sell). Multiply each payment amount by the interest rate for the number of months from possession date to today. Lawly's calculator can assist."),
            ("Identify the builder's registered legal entity", "Real estate promoters must be registered with the state RERA authority. Search the builder on your State RERA portal (e.g., MahaRERA, RERA UP, K-RERA) to find their registered legal entity name, RERA registration number, and registered office address."),
            ("Draft and send the legal notice", "Use <a href='/app'>Lawly</a> to generate a notice citing RERA 2016 §18. State clearly whether you are (a) demanding possession + interest for the delay period, OR (b) demanding full refund with interest under §18(1). Give a 30-day deadline. Send by Registered Post AD to the builder's registered office."),
            ("File a complaint with State RERA", "If unresolved within 30 days, file a complaint on your state RERA portal. Filing is online. State RERA Authorities have powers to: order possession, award interest compensation, and impose penalties on builders. Resolution typically takes 6–12 months."),
            ("Also consider Consumer Forum", "For older cases (agreements before RERA implementation in your state), or for additional compensation for mental harassment, file on EDAAKHIL simultaneously. Consumer forums have awarded substantial damages against builders."),
        ],
        "faqs": [
            ("What is the RERA compensation rate for builder delay in possession?", "Under RERA 2016 §18, the interest rate for builder delay is SBI MCLR + 2% per annum, calculated on every payment made. As of April 2026, this is approximately 10.55–11% per annum. The interest is compounded monthly and applies from the promised possession date until actual possession or refund."),
            ("Can I claim both RERA interest and Consumer Forum compensation?", "Generally, RERA Section 79 bars civil courts from adjudicating disputes under RERA for which a remedy is provided under the Act. However, Consumer Forums have continued to hear builder delay cases, especially for pre-RERA agreements. For newer cases, RERA is the primary route, with Consumer Forum as a supplementary option for compensation beyond what RERA provides."),
            ("What if the builder says the delay is due to COVID or government approvals?", "RERA authorities have recognised force majeure extensions for COVID in some states. However, the builder must apply for the extension — they cannot unilaterally cite force majeure. Check your state RERA portal to see if the builder applied for and received a valid extension for your project. If no extension was granted, the delay is still chargeable."),
            ("Can I cancel the booking and get a full refund plus interest?", "Yes — under RERA §18(1), you can choose to withdraw from the project if possession has not been given by the promised date, and claim full refund with SBI MCLR+2% interest on all amounts paid. The builder must process the refund within 45 days of your withdrawal request."),
        ],
        "related_links": [
            ("Legal notice format India", "/legal-notice-format-india"),
            ("How to send legal notice", "/how-to-send-legal-notice-india"),
            ("RERA builder delay guide", "/rera-builder-delay"),
            ("RERA delay interest calculator", "/rera-delay-interest-calculator"),
            ("Consumer complaint India", "/consumer-complaint-india"),
            ("File on EDAAKHIL", "/how-to-file-consumer-complaint-online"),
        ],
    },
    {
        "slug": "legal-notice-upi-payment-failure",
        "title": "Legal Notice for UPI Payment Failure / Failed Transaction in India (2026) | Lawly",
        "meta_desc": "Send a legal notice for a failed UPI/IMPS/NEFT transaction in India. Banks must auto-reverse within T+5 days and pay ₹100/day compensation for delay. Cite RBI TAT Circular and Payment & Settlement Systems Act §18.",
        "keywords": "legal notice UPI payment failure India, failed UPI transaction legal notice, UPI money not received legal notice India, UPI refund not received legal notice, RBI complaint failed UPI legal notice",
        "canonical": "legal-notice-upi-payment-failure",
        "og_title": "Legal Notice for UPI Payment Failure in India (2026)",
        "og_desc": "Your bank must auto-reverse a failed UPI/IMPS transaction within T+5 days and pay ₹100/day compensation for delays. Lawly generates the legal notice citing the RBI TAT Circular in 5 minutes.",
        "breadcrumb_parent": "How to Send Legal Notice",
        "breadcrumb_parent_url": "how-to-send-legal-notice-india",
        "badge": "UPI / Banking",
        "badge_color": "bg-indigo-100 text-indigo-800",
        "h1": "Legal Notice for UPI Payment Failure / Failed Transaction in India (2026)",
        "intro": "If your UPI, IMPS, or NEFT transaction failed but money was debited from your account and not reversed within the mandated time, your bank has violated the Reserve Bank of India's Turn-Around-Time (TAT) Circular. You are entitled to automatic reversal plus ₹100 per day in compensation for the delay — beyond the 5 working days allowed. A legal notice citing the RBI TAT Circular is the fastest path to recovery, typically triggering resolution within 48–72 hours of receipt.",
        "quick_answer": "<strong>Short answer:</strong> Under the RBI TAT Circular (December 2019), banks must reverse failed UPI/IMPS transactions within T+5 business days. If they don't, they must pay ₹100/day compensation without you having to ask. If yours hasn't been reversed, send a legal notice citing this circular and the Payment and Settlement Systems Act 2007 §18. Generate at <a href='/app'>Lawly (₹199)</a>.",
        "when_heading": "When Should You Send a Legal Notice for a Failed Payment?",
        "when_points": [
            "UPI/IMPS transaction failed and money was debited but not reversed within 5 working days",
            "NEFT/RTGS credit was not received by the beneficiary within the prescribed time and the debit has not been reversed",
            "A merchant payment failed mid-transaction but your bank account shows a debit",
            "The bank has reversed the amount but refused to pay the ₹100/day compensation for the delay",
            "Multiple escalations to the bank's customer support have been ignored or met with vague responses",
        ],
        "law_heading": "What the Law Says",
        "law_content": [
            "<strong>RBI Circular on Turn-Around-Time (TAT) for Failed Transactions, December 2019</strong> — Prescribes mandatory timelines: UPI/IMPS failed transaction reversal: within T+5 business days. NEFT wrong credit/non-credit: within T+2 days. RTGS non-credit: within T+1 day. Banks must pay ₹100 per day to the customer for each day beyond the prescribed TAT, as compensation charged to the bank's income — automatically, without waiting for the customer to complain.",
            "<strong>Payment and Settlement Systems Act 2007, Section 18</strong> — Empowers RBI to issue directions to payment system providers; banks violating these directions are subject to regulatory action. Citing this section in a legal notice puts the bank's compliance desk on high alert.",
            "<strong>Consumer Protection Act 2019, Section 2(11)</strong> — A bank's failure to reverse a failed transaction within the RBI-mandated timeline is a 'deficiency in service.' You can file in the Consumer Forum (via EDAAKHIL) or the RBI Integrated Ombudsman for banking complaints.",
            "<strong>RBI Integrated Ombudsman Scheme 2021</strong> — Covers all UPI/IMPS/NEFT transaction failures by scheduled commercial banks. Filing is free at <a href='https://cms.rbi.org.in' target='_blank' rel='noopener'>cms.rbi.org.in</a>. The Ombudsman can award up to ₹20 lakh in compensation.",
        ],
        "relief_tags": ["Full reversal of failed transaction amount", "₹100/day compensation from T+5 to date of reversal", "Additional compensation from Consumer Forum or RBI Ombudsman", "Up to ₹20 lakh via RBI Integrated Ombudsman (free)"],
        "relief_note": "The ₹100/day compensation is mandatory and automatic under the RBI TAT circular — your bank owes it to you without you needing to ask. However, many banks do not pay it proactively. A legal notice triggers immediate internal escalation and compels the bank to calculate and pay this compensation.",
        "steps": [
            ("Document the failed transaction", "Note: transaction date/time, UPI reference ID or transaction ID, amount, your bank account number, recipient's UPI ID/account number. Get this from your bank's app or SMS confirmation. Check if the bank's statement shows the debit without a corresponding reversal credit."),
            ("Raise a complaint with your bank", "Log a complaint with the bank's customer support citing the transaction ID and requesting reversal + ₹100/day compensation under the RBI TAT circular. Get the complaint reference number. This is step 1 — you typically need to exhaust the bank's grievance process before going to the Ombudsman."),
            ("Send the legal notice to the bank's Grievance Officer", "If the bank doesn't reverse within 5 working days of your complaint, use <a href='/app'>Lawly</a> to generate a legal notice to the bank's Grievance Officer, citing the RBI TAT Circular and Payment & Settlement Systems Act §18. Demand immediate reversal + ₹100/day compensation for each day beyond T+5."),
            ("Escalate to RBI Integrated Ombudsman", "If unresolved within 30 days of your bank complaint, file at <a href='https://cms.rbi.org.in' target='_blank' rel='noopener'>cms.rbi.org.in</a> — free of charge. The Ombudsman typically resolves banking complaints in 30–45 days and can award up to ₹20 lakh."),
            ("File with Consumer Forum as a parallel track", "You can also file a consumer complaint on EDAAKHIL against the bank. This is particularly effective for larger amounts or if the RBI Ombudsman cannot resolve. Filing fee: ₹100 for claims up to ₹5 lakh."),
        ],
        "faqs": [
            ("My UPI payment failed but money was deducted — how many days before I get a refund?", "Under the RBI TAT circular, the bank must reverse the amount within T+5 business days (T = day of the failed transaction). If not reversed by this date, the bank must pay you ₹100 per day in additional compensation. If your bank hasn't reversed within 5 business days, raise a complaint immediately."),
            ("Can I get compensation beyond the reversed amount?", "Yes. The ₹100/day penalty is mandatory. Beyond that, you can claim additional compensation from the RBI Integrated Ombudsman (up to ₹20 lakh) or the Consumer Forum for mental harassment, expenses caused by the failed payment, and inconvenience."),
            ("Which bank's Grievance Officer should I contact?", "Contact your bank — the bank that debited your account. Even if the failure was at the recipient's end, your bank is responsible for the reversal under the RBI TAT framework. The Grievance Officer's contact is available on your bank's website or RBI's banking ombudsman portal."),
            ("Does this apply to PhonePe, Google Pay, and Paytm UPI failures?", "Yes — UPI transactions through PhonePe, Google Pay, or Paytm are processed by banks. The TAT obligation falls on your bank (the remitting bank). The UPI app provider (PhonePe, etc.) is not separately liable, but your bank is. Direct your complaint and legal notice to your bank."),
        ],
        "related_links": [
            ("Legal notice format India", "/legal-notice-format-india"),
            ("How to send legal notice", "/how-to-send-legal-notice-india"),
            ("UPI payment failure guide", "/upi-payment-failures"),
            ("PhonePe complaints", "/phonepe-complaints"),
            ("Google Pay complaints", "/google-pay-complaints"),
            ("Consumer helpline numbers", "/consumer-helpline-numbers"),
        ],
    },
    {
        "slug": "legal-notice-flight-cancellation",
        "title": "Legal Notice for Flight Cancellation Compensation in India (2026) | Lawly",
        "meta_desc": "Send a legal notice to an airline for flight cancellation, delay, or denied boarding under DGCA CAR Section 3. Claim up to ₹20,000 compensation + full refund. Lawly generates the notice citing exact DGCA rules.",
        "keywords": "legal notice flight cancellation India, legal notice airline compensation India, DGCA complaint flight cancellation legal notice, flight delay legal notice India, denied boarding legal notice IndiGo Air India",
        "canonical": "legal-notice-flight-cancellation",
        "og_title": "Legal Notice for Flight Cancellation Compensation India (2026)",
        "og_desc": "How to send a legal notice to an airline for flight cancellation with less than 24h notice, delay, or denied boarding. DGCA entitlements up to ₹20,000. Lawly generates the notice in 5 minutes.",
        "breadcrumb_parent": "How to Send Legal Notice",
        "breadcrumb_parent_url": "how-to-send-legal-notice-india",
        "badge": "Airline · DGCA",
        "badge_color": "bg-sky-100 text-sky-800",
        "h1": "Legal Notice for Flight Cancellation Compensation in India (2026)",
        "intro": "Indian passengers have specific legal rights when a domestic or international flight is cancelled with short notice, delayed beyond defined thresholds, or when boarding is denied. These rights are laid down in the DGCA Civil Aviation Requirements (CAR) Section 3, Series M, Part IV — and airlines regularly fail to inform passengers of these entitlements. A legal notice citing the specific DGCA rules forces airlines to comply and typically results in the compensation being offered within days.",
        "quick_answer": "<strong>Short answer:</strong> Under DGCA CAR Section 3, Series M, Part IV: flight cancelled with less than 24h notice → up to ₹20,000 + alternate flight or full refund. Denied boarding → 200–400% of base fare. Delay over 6 hours → meals, hotel (if needed), and right to cancel for full refund. Generate your legal notice at <a href='/app'>Lawly (₹199)</a>.",
        "when_heading": "When Should You Send a Legal Notice Against an Airline?",
        "when_points": [
            "Your flight was cancelled with less than 24 hours' notice and the airline did not offer the mandatory compensation",
            "You were denied boarding on a confirmed ticket (overbooked flight) and not offered the statutory denied boarding compensation",
            "Your flight was delayed by more than 2 hours and the airline did not provide meals/refreshments",
            "Your flight was delayed by more than 6 hours and the airline refused to refund your full fare when you chose to cancel",
            "Your checked baggage was lost, damaged, or significantly delayed and the airline is not processing your claim",
            "You were offered a voucher or credit shell instead of a cash refund — you have the right to choose cash",
        ],
        "law_heading": "What the Law Says",
        "law_content": [
            "<strong>DGCA CAR Section 3, Series M, Part IV (Handling of Denied Boarding, Cancellations and Delays)</strong> — The primary regulation. Applies to all domestic flights operated from India and international flights operated by Indian carriers.",
            "<strong>Flight Cancellation (less than 24h notice)</strong>: Airlines must offer either alternate flight or full refund AND pay monetary compensation: ₹5,000 (for flights under 1 hour), ₹7,500 (1–2 hours), ₹10,000 (over 2 hours). If the alternate flight departs more than 4 hours after original departure, compensation increases to up to ₹20,000.",
            "<strong>Denied Boarding</strong>: If you are denied boarding due to overbooking on a confirmed ticket and offered alternate flight within 1 hour: no extra compensation beyond your ticket. If alternate flight is 1–24 hours later: 200% of base fare (capped at ₹10,000). If over 24 hours: 400% of base fare (capped at ₹20,000).",
            "<strong>Delays</strong>: 2+ hour delay — airline must provide meals and refreshments. 24+ hour delay — airline must provide hotel accommodation. 6+ hour delay — passenger can cancel the ticket for a full refund without any cancellation charges.",
        ],
        "relief_tags": ["Up to ₹20,000 DGCA mandatory compensation", "100% refund of base fare for denied boarding/cancellation", "Denied boarding: 200–400% of base fare (capped ₹10,000–₹20,000)", "Meals + hotel for long delays", "Consumer Forum additional compensation for mental agony"],
        "relief_note": "Airlines often offer travel vouchers or credit shells instead of cash compensation. You are entitled to demand cash payment. If the airline refuses, a legal notice citing the specific DGCA rule (not just 'passenger rights') typically resolves the matter.",
        "steps": [
            ("Document everything at the airport", "Note the exact time of the cancellation/delay announcement, get it in writing from airline staff, photograph the departure board, keep all boarding passes, and save all SMS/email communications about the flight change. Your documentation starts at the airport."),
            ("File a complaint with AirSewa first", "File an immediate complaint on <a href='https://airsewa.gov.in' target='_blank' rel='noopener'>airsewa.gov.in</a> (DGCA's grievance portal). This creates an official record. If unresolved within 30 days, proceed with the legal notice."),
            ("Send a legal notice to the airline's Grievance Officer", "Use <a href='/app'>Lawly</a> to generate a notice citing the specific DGCA CAR rule applicable to your situation (cancellation/denied boarding/delay) and CPA 2019 §2(11). State the exact compensation amount you are entitled to and demand payment within 15 days."),
            ("Address the notice correctly", "Send to the airline's registered legal entity name (e.g., 'InterGlobe Aviation Limited' for IndiGo, 'Air India Limited') and their registered office. Also send a copy to the Grievance Officer listed on the airline's website."),
            ("Escalate if unresolved", "If unresolved: AirSewa → DGCA formal complaint → Consumer Forum on EDAAKHIL. The Consumer Forum can award additional compensation for mental agony beyond the DGCA mandatory amounts."),
        ],
        "faqs": [
            ("Can I claim compensation if the flight was cancelled due to 'operational reasons'?", "Yes. 'Operational reasons' — including crew unavailability, aircraft maintenance, or schedule changes — do not exempt airlines from DGCA compensation requirements. Only genuine extraordinary circumstances (aircraft technical fault discovered at last minute, genuine weather emergency, air traffic control restrictions, security threats) may reduce the airline's liability. The airline must prove extraordinary circumstances — you don't have to accept their claim at face value."),
            ("Can I get a full cash refund instead of a credit shell for a cancelled flight?", "Yes. You have the right to demand a full cash refund to the original payment method for any flight cancelled by the airline. Airlines cannot force a credit shell or voucher on you. If they insist, cite DGCA CAR and file a complaint on AirSewa immediately."),
            ("What if my baggage was lost by the airline?", "For domestic flights, the Montreal Convention does not apply — airlines have their own tariff limits, but Consumer Forum can award full compensation for proven loss. For international flights, the Montreal Convention 1999 applies — the airline's liability is approximately SDR 1,288 (≈ ₹1.35 lakh) per passenger for checked baggage. Send a legal notice citing the Convention and CPA 2019 for international flights."),
            ("Does this apply to IndiGo, Air India, SpiceJet, Akasa?", "Yes — DGCA CAR applies to all domestic airline operators in India regardless of whether they are full-service or low-cost. IndiGo, Air India, SpiceJet, Akasa Air, Vistara, and all others must comply."),
        ],
        "related_links": [
            ("Legal notice format India", "/legal-notice-format-india"),
            ("How to send legal notice", "/how-to-send-legal-notice-india"),
            ("Flight cancellation guide", "/flight-cancellation"),
            ("IndiGo complaints", "/indigo-complaints"),
            ("Air India complaints", "/air-india-complaints"),
            ("Flight delay compensation calculator", "/flight-delay-compensation-calculator"),
        ],
    },
]


def build_howto_schema(page):
    steps_json = ",\n".join(
        f'        {{ "@type": "HowToStep", "position": {i+1}, "name": "{s[0]}", "text": "{s[1].replace(chr(34), chr(39)).replace(chr(10), " ")}" }}'
        for i, s in enumerate(page["steps"])
    )
    return f"""    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "HowTo",
      "name": "How to Send a Legal Notice for {page['h1'].replace(' in India (2026)', '').replace(' — RERA 2016 (2026)', '')}",
      "description": "{page['meta_desc'][:150].replace(chr(34), chr(39))}",
      "step": [
{steps_json}
      ]
    }}
    </script>"""


def build_faq_schema(page):
    faqs_json = ",\n".join(
        f"""        {{
          "@type": "Question",
          "name": "{q.replace(chr(34), chr(39))}",
          "acceptedAnswer": {{ "@type": "Answer", "text": "{a.replace(chr(34), chr(39)).replace(chr(10), ' ')}" }}
        }}"""
        for q, a in page["faqs"]
    )
    return f"""    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "FAQPage",
      "mainEntity": [
{faqs_json}
      ]
    }}
    </script>"""


def build_breadcrumb_schema(page):
    return f"""    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      "itemListElement": [
        {{ "@type": "ListItem", "position": 1, "name": "Home", "item": "https://lawly.store/" }},
        {{ "@type": "ListItem", "position": 2, "name": "{page['breadcrumb_parent']}", "item": "https://lawly.store/{page['breadcrumb_parent_url']}" }},
        {{ "@type": "ListItem", "position": 3, "name": "{page['h1']}", "item": "https://lawly.store/{page['canonical']}" }}
      ]
    }}
    </script>"""


def build_page(page):
    law_html = "\n".join(f"<p>{l}</p>" for l in page["law_content"])
    relief_tags_html = " ".join(
        f'<span class="relief-tag">{t}</span>' for t in page["relief_tags"]
    )
    steps_html = "\n".join(
        f"<li><div><strong>{s[0]}</strong><p>{s[1]}</p></div></li>"
        for s in page["steps"]
    )
    faq_html = "\n\n".join(
        f"<p><strong>{q}</strong><br>{a}</p>" for q, a in page["faqs"]
    )
    related_html = "\n".join(
        f'<a href="{url}" class="text-blue-600 hover:underline text-sm">{label}</a>'
        for label, url in page["related_links"]
    )
    when_html = "\n".join(f"<li>{pt}</li>" for pt in page["when_points"])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
{GA_TAG}
    <title>{page['title']}</title>
    <meta name="description" content="{page['meta_desc']}">
    <meta name="keywords" content="{page['keywords']}">
    <link rel="canonical" href="https://lawly.store/{page['canonical']}">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{page['og_title']}">
    <meta property="og:description" content="{page['og_desc']}">
    <meta property="og:url" content="https://lawly.store/{page['canonical']}">
    <meta property="og:image" content="https://lawly.store/img/lawly-og.png">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:image" content="https://lawly.store/img/lawly-og.png">

{build_howto_schema(page)}

{build_faq_schema(page)}

{build_breadcrumb_schema(page)}

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="/style.css">
    <style>{STYLES}
    </style>
</head>
<body>
{NAV}

    <div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 pt-4">
        <nav class="text-sm text-gray-500" aria-label="Breadcrumb">
            <ol class="flex flex-wrap gap-1">
                <li><a href="/" class="hover:text-gray-700">Home</a></li>
                <li class="mx-1">/</li>
                <li><a href="/{page['breadcrumb_parent_url']}" class="hover:text-gray-700">{page['breadcrumb_parent']}</a></li>
                <li class="mx-1">/</li>
                <li class="text-gray-800 font-medium">{page['badge']}</li>
            </ol>
        </nav>
    </div>

    <div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-6">
        <div class="prose-legal">
            <div class="flex flex-wrap gap-2 mb-4">
                <span class="inline-block {page['badge_color']} text-xs font-bold px-3 py-1 rounded-full">{page['badge']}</span>
                <span class="inline-block bg-gray-100 text-gray-600 text-xs font-semibold px-3 py-1 rounded-full">Updated April 2026</span>
            </div>
            <h1>{page['h1']}</h1>
            <p class="text-lg text-gray-600">{page['intro']}</p>

            <div class="info-box">
                <p>{page['quick_answer']}</p>
            </div>

            <h2>{page['when_heading']}</h2>
            <ul>
{when_html}
            </ul>

            <h2>{page['law_heading']}</h2>
            <div class="law-box">
{law_html}
            </div>

            <h2>What Relief You Can Demand</h2>
            <p>{relief_tags_html}</p>
            <p>{page['relief_note']}</p>

            <div class="cta-box">
                <h3>Generate This Legal Notice in 5 Minutes</h3>
                <p>Describe your situation — Lawly's AI identifies the exact law sections and drafts a court-ready notice. Print and send the same day.</p>
                <a href="/app" style="display:inline-block;background:white;color:#1e40af;font-weight:700;padding:0.75rem 1.75rem;border-radius:0.5rem;text-decoration:none;">Generate Legal Notice — ₹199 →</a>
            </div>

            <h2>Step-by-Step Process</h2>
            <ol class="step-list">
{steps_html}
            </ol>

            <h2>Frequently Asked Questions</h2>
{faq_html}

            <h2>Related Guides</h2>
            <div class="grid grid-cols-2 sm:grid-cols-3 gap-2 my-3">
{related_html}
            </div>

        </div>
    </div>

{FOOTER}
</body>
</html>"""


if __name__ == "__main__":
    generated = []
    for page in PAGES:
        html = build_page(page)
        out_path = os.path.join(STATIC_DIR, page["slug"] + ".html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✓  {page['slug']}.html  ({len(html):,} chars)")
        generated.append(page["slug"])

    print(f"\nGenerated {len(generated)} pages.")
    print("Slugs:", generated)
