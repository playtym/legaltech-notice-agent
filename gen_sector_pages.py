#!/usr/bin/env python3
"""
Generate consumer-complaint sector hub pages for Lawly.
VakilSearch strategy replication: sector-level pages that sit above company-specific pages.
"""

import os

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# Each sector page definition
PAGES = [
    {
        "slug": "consumer-complaint-ecommerce",
        "title": "E-Commerce Consumer Complaint India (2026)",
        "h1": "E-Commerce Consumer Complaint India (2026)",
        "desc": "File a consumer complaint against Amazon, Flipkart, Meesho, Myntra, Nykaa, or any e-commerce platform in India. Know your rights under CPA 2019, timelines, and how to send a legal notice in 5 minutes.",
        "keywords": "e-commerce consumer complaint India, online shopping complaint India, Amazon consumer complaint, Flipkart consumer complaint, consumer complaint ecommerce India, online purchase complaint India",
        "regulator": "Consumer Protection Act 2019 + E-Commerce Rules 2020",
        "regulator_note": "E-Commerce Rules 2020 (Rule 6) require every platform to appoint a Grievance Officer and resolve complaints within 48 hours of acknowledgment. If unresolved within 30 days, a Consumer Commission case is maintainable.",
        "rights": [
            ("Refund within 30 days", "E-Commerce Rules 2020, Rule 6(5) mandate refund within 7–30 days of raised complaint. Delay = deficiency in service under CPA 2019 §2(11)."),
            ("Product must match description", "CPA 2019 §2(10) defines 'defective goods' broadly — false description, inferior quality, or mismatch from listing qualifies."),
            ("Grievance Officer mandatory", "Every e-commerce platform must display a Grievance Officer name + email. You can escalate directly to the Officer. No response within 48 hrs = default."),
            ("No hidden charges", "CCPA Guidelines on Dark Patterns 2023 prohibit drip pricing, basket sneaking, and forced auto-subscription. You can claim refund + ₹10 lakh penalty."),
            ("Return must be accepted", "If a product is defective or not as described, refusal to accept return is an unfair trade practice under CPA 2019 §2(47)."),
        ],
        "common_complaints": [
            "Product delivered damaged or not as described",
            "Refund not received after return approved",
            "Fake/counterfeit product delivered",
            "Order not delivered but marked delivered",
            "Wrong item delivered; return rejected",
            "Hidden charges at checkout",
            "Auto-renewed subscription without consent",
            "Cash-on-delivery order cancelled unilaterally",
        ],
        "timeline": "File grievance with platform → 48 hrs acknowledgment → 30 days resolution. If unresolved: send legal notice → 15-day deadline → file on EDAAKHIL.",
        "companies": [
            ("Amazon", "amazon-complaints"),
            ("Flipkart", "flipkart-complaints"),
            ("Meesho", "meesho-complaints"),
            ("Myntra", "myntra-complaints"),
            ("Ajio", "ajio-complaints"),
            ("Nykaa", "nykaa-complaints"),
            ("Tata CLiQ", "tata-cliq-complaints"),
            ("Croma", "croma-complaints"),
            ("Reliance Digital", "reliance-digital-complaints"),
            ("Apple India", "apple-complaints"),
            ("Lenskart", "lenskart-complaints"),
        ],
        "faqs": [
            ("Can I file a consumer complaint against Amazon or Flipkart?", "Yes. Both are registered as e-commerce platforms under the CPA 2019 and E-Commerce Rules 2020. You can file directly on EDAAKHIL or send a legal notice first. Amazon India's registered entity is Amazon Seller Services Pvt Ltd; Flipkart's is Flipkart Internet Pvt Ltd."),
            ("What if the seller is a third-party on the platform?", "Under E-Commerce Rules 2020, the marketplace is jointly responsible for grievances related to listed products. You can join both the seller and the platform as opposite parties in your complaint."),
            ("What documents do I need to file an e-commerce consumer complaint?", "Order confirmation email, invoice/receipt, delivery proof (or non-delivery screenshot), photos of defective product, all customer care chat/email transcripts, and bank statement showing payment."),
            ("How much compensation can I claim?", "You can claim: (a) refund of amount paid, (b) compensation for mental agony, (c) litigation costs. There is no fixed cap — District Commission handles claims up to ₹1 crore. Courts routinely award ₹5,000–₹25,000 in mental agony compensation for e-commerce disputes."),
            ("Is there a time limit to file an e-commerce complaint?", "Yes — 2 years from the date the cause of action arose (CPA 2019 §69). For a non-refund case, the clock starts from the date the refund was due."),
        ],
        "breadcrumb_label": "E-Commerce",
    },
    {
        "slug": "consumer-complaint-bank",
        "title": "Bank Consumer Complaint India (2026)",
        "h1": "Bank Consumer Complaint India (2026)",
        "desc": "File a consumer complaint against HDFC, SBI, ICICI, Axis Bank or any bank in India. RBI Integrated Ombudsman handles complaints free of charge. Know your rights and get justice in 30 days.",
        "keywords": "bank consumer complaint India, HDFC Bank complaint, SBI complaint, banking complaint India, RBI ombudsman complaint, bank fraud complaint India, credit card complaint India",
        "regulator": "RBI Integrated Ombudsman Scheme 2021",
        "regulator_note": "The RBI Integrated Ombudsman Scheme 2021 provides a free, fast-track mechanism for complaints against banks, NBFCs, and payment systems. You can file at cms.rbi.org.in. Awards up to ₹20 lakh. No fee. Average resolution: 30 days.",
        "rights": [
            ("Free banking ombudsman", "RBI Integrated Ombudsman Scheme 2021 — file for free at cms.rbi.org.in. Covers all scheduled banks and NBFCs. No advocate needed. Average 30-day turnaround."),
            ("Unauthorized transaction refund", "RBI Circular RBI/2017-18/15 — if you report an unauthorized transaction within 3 days, zero liability. Between 4–7 days: capped liability. The bank must reverse within 10 working days."),
            ("Credit card dispute resolution", "Banks must resolve credit card disputes within 30 days. If a transaction is disputed, the liability is capped until investigation is complete."),
            ("Minimum balance penalty limit", "RBI mandates that penalties for non-maintenance of minimum balance must be proportionate and disclosed upfront."),
            ("Consumer Protection Act applies", "Banking is a 'service' under CPA 2019 §2(42). You can file at Consumer Commission in addition to or instead of the Banking Ombudsman."),
        ],
        "common_complaints": [
            "Unauthorized debit/credit card transaction",
            "Bank refusing to refund fraudulent transaction",
            "Incorrect EMI deduction or loan processing",
            "Account frozen without notice",
            "Excessive or hidden charges",
            "Cheque bounce despite sufficient balance",
            "Fixed deposit not renewed/paid on maturity",
            "Loan account errors or wrong CIBIL reporting",
        ],
        "timeline": "File complaint with bank → 30 days. If unresolved: escalate to RBI Ombudsman at cms.rbi.org.in or file Consumer Commission case via EDAAKHIL.",
        "companies": [
            ("HDFC Bank", "hdfc-bank-complaints"),
            ("SBI", "sbi-complaints"),
            ("ICICI Bank", "icici-bank-complaints"),
            ("Axis Bank", "axis-bank-complaints"),
        ],
        "faqs": [
            ("How do I file an RBI Ombudsman complaint?", "Visit cms.rbi.org.in. File online — no fee, no advocate needed. You must first complain to the bank; if unresolved in 30 days or the response is unsatisfactory, the Ombudsman becomes available. Maximum award: ₹20 lakh."),
            ("Can I file a consumer case against a bank in Consumer Court?", "Yes. Banking is a 'service' under CPA 2019. You can file at the District Consumer Commission or approach the RBI Ombudsman — but not pursue both simultaneously for the same grievance."),
            ("What if my bank deducted money but the transaction failed?", "The bank must reverse the failed transaction amount within 5 working days (T+5). If they don't, they must pay ₹100 per day as compensation under RBI TAT framework."),
            ("My bank is reporting wrong information to CIBIL. What can I do?", "First raise a dispute on the CIBIL website. Simultaneously file a complaint with the bank demanding CIBIL correction in writing. If unresolved in 30 days, approach RBI Ombudsman. You can also send a legal notice demanding correction and compensation for mental agony."),
            ("What documents do I need for a bank consumer complaint?", "Bank statement showing the disputed transaction, all written communications with the bank, account opening documents, screenshots of app/SMS alerts, and any police complaint copy for fraud cases."),
        ],
        "breadcrumb_label": "Bank",
    },
    {
        "slug": "consumer-complaint-telecom",
        "title": "Telecom Consumer Complaint India (2026)",
        "h1": "Telecom Consumer Complaint India (2026)",
        "desc": "File a consumer complaint against Airtel, Jio, BSNL, Vodafone Idea, or ACT Fibernet in India. TRAI and TDSAT handle telecom grievances. Know your rights to compensation for network failure and billing errors.",
        "keywords": "telecom consumer complaint India, Airtel complaint, Jio complaint, BSNL complaint, Vodafone Idea complaint, telecom billing complaint, TRAI complaint India, internet service complaint India",
        "regulator": "TRAI Quality of Service Regulations + Consumer Protection Act 2019",
        "regulator_note": "TRAI (Telecom Regulatory Authority of India) has set mandatory Quality of Service (QoS) standards. Operators must resolve billing complaints within 4 weeks. For unresolved issues, TDSAT (Telecom Disputes Settlement Appellate Tribunal) has jurisdiction, but consumers can also file under CPA 2019 in Consumer Commission.",
        "rights": [
            ("Network QoS standards", "TRAI QoS Regulations mandate minimum service levels for call drops, data speed, and outages. Consistent failure = deficiency in service."),
            ("Billing complaint resolution in 4 weeks", "Operators must resolve billing disputes within 4 weeks. Overcharging is a clear unfair trade practice under CPA 2019 §2(47)."),
            ("Free helpline required", "TRAI mandates operators to provide a free helpline (198 for Airtel, 188 for Jio). All complaints must have a reference number."),
            ("Port-out not to be blocked", "Mobile Number Portability is a right. Operators cannot delay or block porting unfairly. Violation = complaint to TRAI + Consumer Commission."),
            ("Internet data must not expire unfairly", "Prepaid data that expires due to technical issues must be credited back. TRAI regulations require fair data rollover practices."),
        ],
        "common_complaints": [
            "Incorrect billing or unexpected charges",
            "Poor network/data speed despite high-speed pack",
            "SIM card blocked or deactivated without notice",
            "Mobile number porting delayed or blocked",
            "Broadband/fiber service outage for extended period",
            "Recharge not credited to account",
            "Unsolicited calls/SMS despite DND registration",
            "OTT subscription bundled but not activated",
        ],
        "timeline": "File complaint with operator helpline → Get reference number → 4 weeks resolution. If unresolved: TRAI/TDSAT complaint or CPA 2019 Consumer Commission via EDAAKHIL.",
        "companies": [
            ("Airtel", "airtel-complaints"),
            ("Jio", "jio-complaints"),
            ("BSNL", "bsnl-complaints"),
            ("Vodafone Idea (Vi)", "vodafone-idea-complaints"),
            ("ACT Fibernet", "act-fibernet-complaints"),
            ("Hathway", "hathway-complaints"),
        ],
        "faqs": [
            ("How do I escalate a Jio or Airtel complaint after their helpline fails?", "Step 1: File with operator's Nodal Officer (details on their website). Step 2: If unresolved in 30 days, file with TRAI's complaint portal or approach TDSAT. Step 3: Alternatively, file a Consumer Commission case on EDAAKHIL — this is often faster for billing disputes."),
            ("Can telecom companies be sued in Consumer Court?", "Yes. Telecom is a 'service' under CPA 2019. Consumer Courts have jurisdiction alongside TDSAT. For billing disputes and subscription fraud, Consumer Court is often more effective."),
            ("Jio/Airtel deducted money but didn't activate my recharge. What do I do?", "File on the operator app → ask for refund with reference number. If not refunded within 5–7 days, send a legal notice demanding refund + ₹100/day compensation for delay. File on EDAAKHIL after 15-day notice period."),
            ("What if I'm getting spam calls despite DND registration?", "File a complaint via the DND portal (dnd.trai.gov.in) or SMS BLOCK <sender> to 1909. If the operator fails to act, file with TRAI directly."),
            ("Is there a time limit to file a telecom consumer complaint?", "2 years from the date of the deficiency under CPA 2019 §69. However, file as soon as possible — evidence (bills, receipts) is easier to gather fresh."),
        ],
        "breadcrumb_label": "Telecom",
    },
    {
        "slug": "consumer-complaint-travel",
        "title": "Travel Consumer Complaint India (2026)",
        "h1": "Travel Consumer Complaint India (2026)",
        "desc": "File a consumer complaint against IndiGo, Air India, MakeMyTrip, OYO, IRCTC, or any travel company in India. Know DGCA rules on refunds, hotel dispute rights, and how to get compensation quickly.",
        "keywords": "travel consumer complaint India, airline complaint India, IndiGo complaint, Air India complaint, MakeMyTrip complaint, IRCTC complaint, hotel complaint India, DGCA complaint, travel refund complaint India",
        "regulator": "DGCA CAR S3 Series M Part IV (Airlines) + Consumer Protection Act 2019",
        "regulator_note": "DGCA (Directorate General of Civil Aviation) mandates compensation for denied boarding (₹5,000–₹20,000), flight cancellation (full refund + ₹5,000–₹10,000), and delays over 6 hours. File at airpassengershelpline.dgca.gov.in or EDAAKHIL.",
        "rights": [
            ("Flight cancellation: full refund + compensation", "DGCA CAR S3 Part IV — if the airline cancels your flight and you reject the alternative, you get a full ticket refund within 7 days + ₹5,000–₹10,000 compensation."),
            ("Denied boarding: ₹5,000–₹20,000 compensation", "If involuntarily denied boarding due to overbooking, you are entitled to ₹5,000 (short flight) to ₹20,000 (long flight) compensation."),
            ("Checked baggage delay/loss", "₹350 per kg for damaged/delayed baggage (international); domestic rates per airline contract. File claim before leaving airport."),
            ("IRCTC ticket refund", "TDR (Ticket Deposit Receipt) must be filed within timelines per Railway rules. Unexplained non-refund = deficiency in service under CPA 2019."),
            ("Hotel must provide booked room or equivalent", "Under CPA 2019, a confirmed hotel booking is a contract. Failure to provide the booked room or downgrading without consent = breach."),
        ],
        "common_complaints": [
            "Flight cancelled — refund not received",
            "Denied boarding due to overbooking",
            "Baggage lost or damaged",
            "Hotel didn't honour confirmed booking",
            "OTA (MakeMyTrip/Cleartrip) charging cancellation fee higher than airline's",
            "IRCTC TDR not processed",
            "Tour package not as promised",
            "Ticket fare changed at checkout vs. advertised",
        ],
        "timeline": "File with airline/hotel/OTA → DGCA complaint (airlines) → Consumer Commission or Consumer Court via EDAAKHIL. Legal notice first = faster resolution.",
        "companies": [
            ("IndiGo", "indigo-complaints"),
            ("Air India", "air-india-complaints"),
            ("Akasa Air", "akasa-air-complaints"),
            ("SpiceJet", "spicejet-complaints"),
            ("Vistara", "vistara-complaints"),
            ("MakeMyTrip", "makemytrip-complaints"),
            ("Cleartrip", "cleartrip-complaints"),
            ("Yatra", "yatra-complaints"),
            ("RedBus", "redbus-complaints"),
            ("IRCTC", "irctc-complaints"),
            ("OYO Rooms", "oyo-rooms-complaints"),
            ("Agoda", "agoda-complaints"),
            ("BookMyShow", "bookmyshow-complaints"),
            ("Airbnb", "airbnb-complaints"),
        ],
        "faqs": [
            ("My flight was cancelled. What compensation am I entitled to?", "If the airline cancels your flight and you reject the alternate offered: (a) full ticket refund within 7 days, (b) ₹5,000 compensation for flights ≤1 hr delay alternative, ₹10,000 for >1 hr. If the airline provides no alternative: full refund + compensation as above per DGCA CAR S3 Part IV."),
            ("Can I file a Consumer Court case against an airline?", "Yes. Airlines are 'service providers' under CPA 2019. Consumer Commission has jurisdiction for deficiency in service (refund delays, denied boarding, baggage loss). DGCA complaint and Consumer Court can be pursued parallelly."),
            ("MakeMyTrip charged me extra cancellation fees. Is this legal?", "OTAs must disclose all charges upfront. Per E-Commerce Rules 2020 and CCPA Guidelines 2023, hidden cancellation fees are a dark pattern. You can file a complaint and claim refund + ₹10 lakh CCPA penalty against the platform."),
            ("My hotel booking was cancelled on arrival. What can I do?", "The hotel must arrange equivalent or better accommodation at no extra cost. If they fail, file a consumer complaint under CPA 2019 for deficiency in service + compensation for mental agony and hotel search costs."),
            ("What is the time limit to file a travel consumer complaint?", "2 years from the date of journey/stay under CPA 2019 §69. For DGCA complaints, file within 30 days of the incident for best results."),
        ],
        "breadcrumb_label": "Travel",
    },
    {
        "slug": "consumer-complaint-education",
        "title": "Education Consumer Complaint India (2026)",
        "h1": "Education Consumer Complaint India (2026)",
        "desc": "File a consumer complaint against Byju's, Unacademy, Vedantu, upGrad, or any ed-tech company in India. UGC refund policy mandates 100% refund before course starts. Know your rights and get your fees back.",
        "keywords": "education consumer complaint India, Byju's refund complaint, ed-tech consumer complaint India, UGC refund policy, coaching fee refund India, online course refund complaint India, Unacademy complaint India",
        "regulator": "UGC Refund Policy 2023 + Consumer Protection Act 2019 + CCPA",
        "regulator_note": "UGC Notification 2023 mandates 100% fee refund if student withdraws before course start date. Post-withdrawal refunds are pro-rated. CCPA has taken suo motu action against Byju's. Consumer Courts have consistently held that education is a 'service' under CPA 2019.",
        "rights": [
            ("UGC mandates 100% refund before course start", "UGC (University Grants Commission) mandates 100% fee refund if a student cancels before the academic session starts. This applies to all UGC-affiliated institutions and many ed-tech companies offering degree-linked programs."),
            ("Ed-tech EMI lock-in clauses are challengeable", "Many ed-tech companies sell courses with partner NBFCs/banks. If the course is not delivered as promised, the loan obligation can be disputed under CPA 2019 — Consumer Courts have set aside such loans."),
            ("Misleading advertisements: CCPA jurisdiction", "CCPA (Central Consumer Protection Authority) has penalized ed-tech companies for misleading placement guarantees. Any false promise about placement rates or salary outcomes = actionable."),
            ("Coaches must refund fee if course discontinued", "If an ed-tech platform shuts down or discontinues a program, full refund is compulsory under CPA 2019 §2(11)."),
            ("Consumer Court has jurisdiction over private coaching", "Supreme Court clarified (Bihar School Examination Board v Suresh Prasad Sinha): private coaching and ed-tech services are 'services' under CPA 2019. Complaints are maintainable."),
        ],
        "common_complaints": [
            "Byju's/Unacademy refusing to cancel EMI-linked course",
            "Online course quality far below promised standard",
            "Placement guarantee not honoured",
            "Refund not processed after withdrawal",
            "Coaching center shutting down without refund",
            "Teacher/mentor changed multiple times",
            "App/platform not accessible after payment",
            "Certificate not issued after course completion",
        ],
        "timeline": "Complain to ed-tech Grievance Officer → 30 days. If unresolved: send legal notice → 15 days → file on EDAAKHIL or approach CCPA at consumerhelpline.gov.in.",
        "companies": [
            ("Byju's", "byjus-complaints"),
            ("Unacademy", "unacademy-complaints"),
            ("Vedantu", "vedantu-complaints"),
            ("upGrad", "upgrad-complaints"),
        ],
        "faqs": [
            ("Can I cancel my Byju's course and get a refund?", "Yes, under UGC guidelines and CPA 2019. If Byju's refuses, send a legal notice citing CPA 2019 §2(11) (deficiency in service) and the UGC Refund Policy. Consumer Courts have awarded full refunds + compensation in hundreds of Byju's cases. The National Consumer Commission has also taken cognizance."),
            ("My ed-tech company sold me a course with an EMI. Can I stop the EMI?", "If the course was not delivered as promised, you can contest the loan with the financing bank/NBFC as a consumer dispute. File a complaint against both the ed-tech company (for deficiency) and the financier (if they continue deducting EMI despite the dispute) under CPA 2019."),
            ("What if the coaching center/ed-tech platform has shut down?", "Full refund is mandatory. File a complaint on EDAAKHIL against the company directors + file a police FIR if the shutdown appears fraudulent. CCPA can also initiate recovery proceedings."),
            ("Can I file a consumer complaint against an offline coaching center like ALLEN or Aakash?", "Yes. Private coaching is a 'service' under CPA 2019. Refund disputes, course quality issues, and false placement guarantees are all actionable in Consumer Commission."),
            ("What documents do I need for an ed-tech consumer complaint?", "Enrollment receipt, payment confirmation, all email/SMS communications with the company, marketing brochure or website screenshots (showing promises made), EMI statements, and evidence of course not delivered (screenshots, app recordings)."),
        ],
        "breadcrumb_label": "Education",
    },
    {
        "slug": "consumer-complaint-home-appliances",
        "title": "Home Appliances Consumer Complaint India (2026)",
        "h1": "Home Appliances Consumer Complaint India (2026)",
        "desc": "File a consumer complaint against Samsung, LG, Whirlpool, Sony, or any appliance brand in India. Product liability under CPA 2019 Chapter VI covers manufacturing defects. Know how to claim free repair or replacement.",
        "keywords": "home appliances consumer complaint India, Samsung complaint India, LG complaint India, Whirlpool complaint India, product defect complaint India, consumer complaint washing machine, consumer complaint refrigerator India",
        "regulator": "Consumer Protection Act 2019 Chapter VI (Product Liability) + BIS Standards",
        "regulator_note": "CPA 2019 Chapter VI introduces strict product liability — manufacturers are liable for harm caused by defective products regardless of negligence. Distributors and sellers share responsibility. BIS (Bureau of Indian Standards) mandatory certification standards apply to electronics and appliances.",
        "rights": [
            ("Product liability: manufacturer is strictly liable", "CPA 2019 §83–§87 impose strict liability on manufacturers for defective products — no need to prove negligence. Design defects, manufacturing defects, and failure to warn are all covered."),
            ("Free repair/replacement in warranty period", "A warranty is a legal promise. Refusal to honour warranty = deficiency in service under CPA 2019 §2(11). The manufacturer must repair, replace, or refund."),
            ("Recurring defect = right to replacement", "If the same defect recurs 3+ times despite repairs, you have the right to demand a full replacement (not just repair) under Consumer Court practice."),
            ("After-sales service must be provided", "Manufacturers must maintain a service network for the product's reasonable useful life. Inability to provide service parts = CPA 2019 deficiency."),
            ("BIS certified products cannot be substandard", "If a product bearing BIS certification fails to meet BIS standards, you have grounds for complaint against the manufacturer + can report to BIS."),
        ],
        "common_complaints": [
            "New appliance stopped working within warranty period",
            "Manufacturer refusing warranty claim",
            "Repeated repair — same defect not fixed",
            "Service engineer not attending despite booking",
            "Spare parts unavailable for product within useful life",
            "Product causing damage (fire, electric shock, water leak)",
            "Delivered product differs from what was ordered",
            "Seller refusing to replace physically damaged delivery",
        ],
        "timeline": "Call manufacturer toll-free → Get service request number → 15 day repair/replacement timeline. If unresolved: send legal notice → 15 days → file on EDAAKHIL.",
        "companies": [
            ("Samsung", "samsung-complaints"),
            ("LG", "lg-complaints"),
            ("Whirlpool", "whirlpool-complaints"),
            ("Sony", "sony-complaints"),
            ("Apple India", "apple-complaints"),
        ],
        "faqs": [
            ("My new washing machine is defective. What are my legal options?", "Within warranty period: manufacturer must repair or replace free of charge. If they refuse: send a legal notice citing CPA 2019 §2(10) (defective goods) and §2(11) (deficiency in service). File on EDAAKHIL if legal notice is ignored. You can claim refund + replacement value + compensation for inconvenience."),
            ("Can I claim compensation if an appliance caused fire or damage?", "Yes. Under CPA 2019 Chapter VI (product liability), the manufacturer is strictly liable for any harm caused by a defective product — no need to prove negligence. You can claim: product cost, repair cost for damaged property, medical expenses, and compensation for mental agony."),
            ("The manufacturer says my warranty is void because I used a third-party service center. Is this legal?", "Partly — warranty can be voided for unauthorized service only if the manufacturer can prove it caused the defect. Blanket warranty void-on-third-party-service clauses are challengeable as unfair contract terms under CPA 2019 §2(46)."),
            ("Samsung/LG is not sending a service engineer despite multiple complaints. What can I do?", "Document all complaint IDs and dates. After 15 days of no response, file a legal notice citing CPA 2019 §2(11). This typically triggers escalation to the manufacturer's legal team. If unresolved, file on EDAAKHIL — service unavailability cases in Consumer Court are resolved within 60–90 days."),
            ("What if a product is recalled but the company doesn't inform me?", "Under CPA 2019 and CCPA regulations, manufacturers must notify registered owners of product recalls and facilitate free repair/replacement/refund. Non-compliance = complaint to CCPA at consumerhelpline.gov.in."),
        ],
        "breadcrumb_label": "Home Appliances",
    },
    {
        "slug": "consumer-complaint-food-delivery",
        "title": "Food Delivery Consumer Complaint India (2026)",
        "h1": "Food Delivery Consumer Complaint India (2026)",
        "desc": "File a consumer complaint against Swiggy, Zomato, Blinkit, Zepto or any food/quick-commerce platform in India. Know your rights to refund, compensation, and how to resolve disputes in 5 minutes with a legal notice.",
        "keywords": "food delivery consumer complaint India, Swiggy complaint India, Zomato complaint India, Blinkit complaint India, Zepto complaint India, food order complaint India, wrong food complaint India, quick commerce complaint India",
        "regulator": "Consumer Protection Act 2019 + E-Commerce Rules 2020 + FSSAI Act 2006",
        "regulator_note": "Food delivery platforms are liable as 'marketplace e-commerce entities' under E-Commerce Rules 2020. Additionally, FSSAI (Food Safety and Standards Authority of India) regulates food quality. Platforms must resolve complaints within 48 hours. Compensation for food safety violations can also be claimed under FSSAI Act.",
        "rights": [
            ("Refund for wrong or missing order", "E-Commerce Rules 2020 mandate refund for undelivered or incorrectly delivered orders. Platform cannot deny refund solely because the restaurant is a 'third party'."),
            ("Food must meet FSSAI standards", "Any food delivered must meet FSSAI standards for safety, hygiene, and quantity. Unhygienic food = complaint to FSSAI + Consumer Commission."),
            ("Surge pricing must be disclosed", "Under CCPA Dark Patterns Guidelines 2023, surge pricing on delivery must be clearly disclosed before checkout — hidden delivery fees at the final step = dark pattern."),
            ("Platform liable for misleading restaurant listings", "If the restaurant listed on the platform is closed or doesn't exist, the platform is liable under E-Commerce Rules 2020."),
            ("ETD (Estimated Time of Delivery) must be honest", "False ETAs to lure customers = misleading advertisement under CPA 2019 §2(28). You can file against the platform for systematic ETA manipulation."),
        ],
        "common_complaints": [
            "Wrong item delivered",
            "Order partially missing (items not in bag)",
            "Food arrived cold or spoiled",
            "Delivery marked complete but not received",
            "Refund not credited to original payment mode",
            "Platform blocking/cancelling order without refund",
            "Foreign object found in food",
            "Restaurant delivered smaller portion than ordered",
        ],
        "timeline": "Raise in-app complaint immediately → Screenshot all evidence → Escalate to Grievance Officer if unresolved in 48 hrs → Send legal notice → File on EDAAKHIL or NCH if unresolved.",
        "companies": [
            ("Swiggy", "swiggy-complaints"),
            ("Zomato", "zomato-complaints"),
            ("Blinkit", "blinkit-complaints"),
            ("Zepto", "zepto-complaints"),
            ("Dunzo", "dunzo-complaints"),
        ],
        "faqs": [
            ("Swiggy/Zomato refused my refund. What can I do?", "Immediately escalate to their Grievance Officer (email listed on website). If unresolved in 7 days, send a legal notice via Lawly (₹199) citing E-Commerce Rules 2020 Rule 6(5). Most food delivery platforms settle once a formal legal notice is received. If still unresolved, file on EDAAKHIL — filing fee: ₹100 for claims under ₹5 lakh."),
            ("I found a foreign object in my Swiggy/Zomato order. What can I do?", "Take photos immediately before touching. Raise an in-app complaint with photos. Simultaneously file an FSSAI complaint at fssai.gov.in or call 1800-112-100. You can claim compensation for medical expenses + mental agony under CPA 2019 from both the restaurant and the platform."),
            ("Blinkit says I'll get a refund in 5–7 days, but it's been 30 days. What can I do?", "Send a legal notice citing the specific delay:  platform committed to refund, failed to refund, creating a deficiency and constituting an unfair trade practice under CPA 2019. Claim original amount + interest + ₹5,000 compensation. File on EDAAKHIL if not resolved within 15 days of legal notice."),
            ("Can I file a Consumer Court case against Swiggy or Zomato?", "Yes. They are registered as e-commerce companies and classified as 'service providers' under CPA 2019. District Consumer Commission handles claims up to ₹1 crore. Filing fee is only ₹100–₹200 for small claims."),
            ("What documents do I need for a food delivery consumer complaint?", "Screenshot of the order confirmation, delivery notification (or lack thereof), in-app complaint chat, payment receipt, and photos of wrong/damaged/spoiled food. If food caused illness: doctor's prescription and medical bills."),
        ],
        "breadcrumb_label": "Food Delivery",
    },
    {
        "slug": "consumer-complaint-real-estate",
        "title": "Real Estate Consumer Complaint India (2026)",
        "h1": "Real Estate Consumer Complaint India (2026)",
        "desc": "File a consumer complaint against a builder, housing society, or real estate portal in India. RERA (Real Estate Regulation Act 2016) and Consumer Protection Act 2019 protect homebuyers. Get refund with interest or possession in 60 days.",
        "keywords": "real estate consumer complaint India, builder complaint RERA, housing complaint India, flat possession delayed complaint, RERA complaint India, consumer complaint builder delay, housing.com complaint India",
        "regulator": "RERA 2016 + Consumer Protection Act 2019",
        "regulator_note": "RERA (Real Estate (Regulation and Development) Act 2016) is the primary law for homebuyer protection. Every RERA state authority has an online complaint portal. Additionally, CPA 2019 applies — you can file at Consumer Commission for deficiency in service. Both RERA and Consumer Commission have concurrent jurisdiction per Supreme Court (Forum for People's Collective Efforts v State of West Bengal, 2021).",
        "rights": [
            ("RERA: builder must deliver possession on time", "RERA §18 — if the builder fails to deliver possession by the agreed date, the buyer can either: (a) withdraw and get full refund + SBI MCLR+2% interest, or (b) continue and claim interest for each month of delay."),
            ("RERA registration is mandatory", "All housing projects above a certain threshold must be RERA-registered. Starting sales before RERA registration = penalty of 10% of project cost. Check registration at rerain.gov.in."),
            ("Carpet area must match what was promised", "RERA §14 mandates that the delivered carpet area must match the agreed area. Any shortfall: proportionate refund."),
            ("Consumer Commission concurrent with RERA", "Supreme Court confirmed in 2021: homebuyers can choose between RERA and Consumer Commission — it's the buyer's right to pick the most favourable forum."),
            ("Structural defect warranty: 5 years", "RERA §14(3) — builders are liable for structural defects for 5 years post-handover. They must rectify at no cost within 30 days."),
        ],
        "common_complaints": [
            "Builder not delivering possession on time",
            "Builder refusing to refund on project cancellation",
            "Flat area delivered smaller than promised",
            "Amenities (gym, pool, clubhouse) not constructed",
            "Structural defects within 5 years of possession",
            "Real estate portal (Housing.com, MagicBricks) listing fraud",
            "Builder demanding extra charges not in agreement",
            "Housing society refusing to hand over maintenance documents",
        ],
        "timeline": "File RERA complaint at state RERA authority portal → or file at Consumer Commission via EDAAKHIL. Send legal notice first for faster settlement.",
        "companies": [
            ("Housing.com", "housingcom-complaints"),
            ("MagicBricks", "magicbricks-complaints"),
            ("NoBroker", "nobroker-complaints"),
        ],
        "faqs": [
            ("My builder has delayed possession by 2 years. What are my options?", "Under RERA §18, you can: (a) withdraw from the project and demand full refund + SBI MCLR+2% interest per year from the date of payment, OR (b) stay invested and claim monthly interest at MCLR+2% for every month of delay. File at your state RERA authority or Consumer Commission."),
            ("Can I file both at RERA and Consumer Court?", "Per Supreme Court's 2021 ruling (Forum for People's Collective Efforts), you can file at either RERA or Consumer Commission — your choice. You cannot pursue both simultaneously for the same relief. Many homebuyers prefer Consumer Commission for faster timelines (90-day target under CPA 2019)."),
            ("The builder is asking for extra charges not mentioned in the sale agreement. Do I have to pay?", "No. Under RERA §13, builders cannot demand more than 10% of the property cost before a registered sale agreement. Any charges not specified in the agreement cannot be demanded. Send a legal notice stating you will withhold payment and file RERA complaint if they proceed."),
            ("My flat has major structural cracks 2 years after possession. What can I do?", "RERA §14(3) provides a 5-year structural defect warranty. Send a written notice to the builder with photos. Builder must rectify within 30 days. If they don't, file RERA complaint at the state authority + Consumer Commission for deficiency in service."),
            ("What documents do I need for a builder/real estate complaint?", "Builder-buyer agreement / allotment letter, all payment receipts, RERA registration certificate (from rerain.gov.in), possession letter (if any), photos of the defect or unfinished construction, and all communications with the builder."),
        ],
        "breadcrumb_label": "Real Estate",
    },
]


def generate_page(page: dict) -> str:
    slug = page["slug"]
    title = page["title"]
    h1 = page["h1"]
    desc = page["desc"]
    keywords = page["keywords"]
    regulator = page["regulator"]
    regulator_note = page["regulator_note"]
    rights = page["rights"]
    common_complaints = page["common_complaints"]
    timeline = page["timeline"]
    companies = page["companies"]
    faqs = page["faqs"]
    breadcrumb_label = page["breadcrumb_label"]
    url = f"https://lawly.store/{slug}"

    # JSON-LD schemas
    faq_entries = "\n".join(
        f"""        {{
          "@type": "Question",
          "name": "{q.replace('"', '&quot;')}",
          "acceptedAnswer": {{
            "@type": "Answer",
            "text": "{a.replace('"', '&quot;').replace(chr(10), ' ')}"
          }}
        }}"""
        for q, a in faqs
    )

    faq_schema = f"""{{
      "@context": "https://schema.org",
      "@type": "FAQPage",
      "mainEntity": [
{faq_entries}
      ]
    }}"""

    breadcrumb_schema = f"""{{
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      "itemListElement": [
        {{ "@type": "ListItem", "position": 1, "name": "Home", "item": "https://lawly.store/" }},
        {{ "@type": "ListItem", "position": 2, "name": "Consumer Complaint India", "item": "https://lawly.store/consumer-complaint-india" }},
        {{ "@type": "ListItem", "position": 3, "name": "{breadcrumb_label}", "item": "{url}" }}
      ]
    }}"""

    service_schema = f"""{{
      "@context": "https://schema.org",
      "@type": "Service",
      "name": "{title}",
      "description": "{desc}",
      "provider": {{ "@type": "Organization", "name": "Lawly", "url": "https://lawly.store" }},
      "areaServed": {{ "@type": "Country", "name": "India" }},
      "url": "{url}",
      "offers": [
        {{ "@type": "Offer", "name": "AI Legal Notice (Self-Send)", "price": "199", "priceCurrency": "INR", "url": "https://lawly.store/app" }},
        {{ "@type": "Offer", "name": "Lawyer-Drafted Legal Notice", "price": "599", "priceCurrency": "INR", "url": "https://lawly.store/app" }}
      ]
    }}"""

    # Rights rows
    rights_rows = "\n".join(
        f"""                <tr>
                    <td class="py-3 px-4 font-medium text-gray-800 w-1/3">{r[0]}</td>
                    <td class="py-3 px-4 text-gray-700">{r[1]}</td>
                </tr>"""
        for r in rights
    )

    # Common complaints list
    complaints_items = "\n".join(
        f'                <li class="flex items-start gap-2"><span class="text-red-500 mt-0.5">&#x26A0;</span><span>{c}</span></li>'
        for c in common_complaints
    )

    # Company cards
    company_cards = "\n".join(
        f"""                <a href="/{slug_co}" class="block p-4 bg-white border border-gray-200 rounded-xl hover:border-blue-400 hover:shadow-sm transition text-center">
                    <span class="font-semibold text-gray-800">{name}</span>
                    <span class="block text-xs text-blue-600 mt-1">File complaint &rarr;</span>
                </a>"""
        for name, slug_co in companies
    )

    # FAQ accordion
    faq_items = "\n".join(
        f"""            <details class="bg-white border border-gray-200 rounded-xl p-5">
                <summary class="font-semibold text-gray-800 cursor-pointer">{q}</summary>
                <p class="mt-3 text-gray-700 leading-relaxed">{a}</p>
            </details>"""
        for q, a in faqs
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-F63GR76DSR"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', 'G-F63GR76DSR');
    </script>
    <title>{title} | Lawly</title>
    <meta name="description" content="{desc}">
    <meta name="keywords" content="{keywords}">
    <link rel="canonical" href="{url}">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{desc}">
    <meta property="og:url" content="{url}">
    <meta property="og:site_name" content="Lawly">
    <meta property="og:image" content="https://lawly.store/img/lawly-og.png">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:image" content="https://lawly.store/img/lawly-og.png">

    <script type="application/ld+json">
    {faq_schema}
    </script>

    <script type="application/ld+json">
    {breadcrumb_schema}
    </script>

    <script type="application/ld+json">
    {service_schema}
    </script>

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
      body {{ font-family: 'Inter', sans-serif; }}
      details summary::-webkit-details-marker {{ display: none; }}
      details summary {{ list-style: none; }}
    </style>
</head>
<body class="bg-gray-50 text-gray-900">

    <!-- NAV -->
    <nav class="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div class="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
            <a href="/" class="font-bold text-xl text-blue-700">Lawly</a>
            <div class="hidden md:flex gap-6 text-sm font-medium text-gray-600">
                <a href="/consumer-complaint-india" class="hover:text-blue-600">Consumer Complaints</a>
                <a href="/send-legal-notice-india" class="hover:text-blue-600">Legal Notice</a>
                <a href="/app" class="hover:text-blue-600">Send Notice</a>
            </div>
            <a href="/app" class="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2 rounded-lg transition">
                Get Started &rarr;
            </a>
        </div>
    </nav>

    <!-- BREADCRUMB -->
    <div class="max-w-5xl mx-auto px-4 pt-4 text-sm text-gray-500">
        <a href="/" class="hover:text-blue-600">Home</a>
        <span class="mx-1">/</span>
        <a href="/consumer-complaint-india" class="hover:text-blue-600">Consumer Complaint India</a>
        <span class="mx-1">/</span>
        <span class="text-gray-800 font-medium">{breadcrumb_label}</span>
    </div>

    <!-- HERO -->
    <section class="max-w-5xl mx-auto px-4 pt-8 pb-6">
        <h1 class="text-3xl md:text-4xl font-bold text-gray-900 leading-tight">{h1}</h1>
        <p class="mt-4 text-lg text-gray-600 leading-relaxed max-w-3xl">{desc}</p>

        <!-- Stats bar -->
        <div class="mt-6 flex flex-wrap gap-4">
            <div class="bg-green-50 border border-green-200 rounded-xl px-4 py-3 text-center min-w-[120px]">
                <div class="text-2xl font-bold text-green-700">15,000+</div>
                <div class="text-xs text-gray-600 mt-0.5">Complaints Resolved</div>
            </div>
            <div class="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 text-center min-w-[120px]">
                <div class="text-2xl font-bold text-blue-700">&#8377;199</div>
                <div class="text-xs text-gray-600 mt-0.5">Legal Notice</div>
            </div>
            <div class="bg-yellow-50 border border-yellow-200 rounded-xl px-4 py-3 text-center min-w-[120px]">
                <div class="text-2xl font-bold text-yellow-700">5 min</div>
                <div class="text-xs text-gray-600 mt-0.5">AI Draft Ready</div>
            </div>
            <div class="bg-purple-50 border border-purple-200 rounded-xl px-4 py-3 text-center min-w-[120px]">
                <div class="text-2xl font-bold text-purple-700">25+</div>
                <div class="text-xs text-gray-600 mt-0.5">Laws Cited Auto</div>
            </div>
        </div>
    </section>

    <!-- REGULATOR CALLOUT -->
    <section class="max-w-5xl mx-auto px-4 pb-6">
        <div class="bg-yellow-50 border-l-4 border-yellow-400 rounded-r-xl px-5 py-4">
            <div class="font-bold text-yellow-800 mb-1">Governing Law: {regulator}</div>
            <p class="text-yellow-900 text-sm leading-relaxed">{regulator_note}</p>
        </div>
    </section>

    <!-- YOUR RIGHTS -->
    <section class="max-w-5xl mx-auto px-4 pb-8">
        <h2 class="text-2xl font-bold text-gray-900 mb-4">Your Rights in {breadcrumb_label} Disputes</h2>
        <div class="overflow-x-auto rounded-2xl border border-gray-200 shadow-sm">
            <table class="w-full text-sm">
                <thead>
                    <tr class="bg-blue-600 text-white">
                        <th class="py-3 px-4 text-left font-semibold">Right</th>
                        <th class="py-3 px-4 text-left font-semibold">Legal Basis &amp; Details</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
{rights_rows}
                </tbody>
            </table>
        </div>
    </section>

    <!-- COMMON COMPLAINTS -->
    <section class="max-w-5xl mx-auto px-4 pb-8">
        <h2 class="text-2xl font-bold text-gray-900 mb-4">Common {breadcrumb_label} Consumer Complaints</h2>
        <div class="bg-white border border-gray-200 rounded-2xl p-6">
            <ul class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
{complaints_items}
            </ul>
        </div>
    </section>

    <!-- HOW TO FILE STEPS -->
    <section class="max-w-5xl mx-auto px-4 pb-8">
        <h2 class="text-2xl font-bold text-gray-900 mb-4">How to File a {breadcrumb_label} Consumer Complaint</h2>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div class="bg-white border border-gray-200 rounded-2xl p-5 text-center">
                <div class="text-3xl mb-2">&#x1F4DD;</div>
                <div class="font-bold text-gray-800 mb-1">Step 1</div>
                <div class="text-sm text-gray-600">Gather all documents — invoice, communication, payment proof, and evidence of the deficiency.</div>
            </div>
            <div class="bg-white border border-gray-200 rounded-2xl p-5 text-center">
                <div class="text-3xl mb-2">&#x2696;&#xFE0F;</div>
                <div class="font-bold text-gray-800 mb-1">Step 2</div>
                <div class="text-sm text-gray-600">Send a formal legal notice via <a href="/app" class="text-blue-600 font-semibold">Lawly</a> — drafted in 5 minutes, citing exact law sections.</div>
            </div>
            <div class="bg-white border border-gray-200 rounded-2xl p-5 text-center">
                <div class="text-3xl mb-2">&#x23F1;&#xFE0F;</div>
                <div class="font-bold text-gray-800 mb-1">Step 3</div>
                <div class="text-sm text-gray-600">Wait 15 days for company response. ~60% of disputes resolve after a proper legal notice.</div>
            </div>
            <div class="bg-white border border-gray-200 rounded-2xl p-5 text-center">
                <div class="text-3xl mb-2">&#x1F3DB;&#xFE0F;</div>
                <div class="font-bold text-gray-800 mb-1">Step 4</div>
                <div class="text-sm text-gray-600">If unresolved, file on <a href="https://edaakhil.nic.in" target="_blank" rel="noopener" class="text-blue-600">EDAAKHIL</a> (Consumer Forum). Filing fee: ₹100–₹200 for most claims.</div>
            </div>
        </div>
        <div class="mt-4 bg-gray-100 rounded-xl px-4 py-3 text-sm text-gray-700">
            <strong>Typical Timeline:</strong> {timeline}
        </div>
    </section>

    <!-- COMPANY GRID -->
    <section class="max-w-5xl mx-auto px-4 pb-8">
        <h2 class="text-2xl font-bold text-gray-900 mb-4">File Complaint Against Specific Companies</h2>
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
{company_cards}
        </div>
    </section>

    <!-- LEGAL NOTICE CTA -->
    <section class="max-w-5xl mx-auto px-4 pb-8">
        <div class="bg-blue-600 rounded-2xl px-6 py-8 text-white text-center">
            <h2 class="text-2xl font-bold mb-2">Send a Legal Notice in 5 Minutes</h2>
            <p class="text-blue-100 mb-6 max-w-xl mx-auto">Lawly's AI cites 25+ Indian statutes, generates a lawyer-quality notice, and sends it via WhatsApp + email + RPAD post — all for ₹199.</p>
            <div class="flex flex-col sm:flex-row gap-3 justify-center">
                <a href="/app" class="bg-white text-blue-700 font-bold px-6 py-3 rounded-xl hover:bg-blue-50 transition">
                    Send Notice for ₹199 &rarr;
                </a>
                <a href="/app" class="border-2 border-white text-white font-semibold px-6 py-3 rounded-xl hover:bg-blue-700 transition">
                    Lawyer-Drafted ₹599
                </a>
            </div>
            <p class="text-xs text-blue-200 mt-4">No hidden fees &bull; Notice ready in 5 minutes &bull; 25+ statutes cited automatically</p>
        </div>
    </section>

    <!-- FAQ -->
    <section class="max-w-5xl mx-auto px-4 pb-12">
        <h2 class="text-2xl font-bold text-gray-900 mb-5">Frequently Asked Questions</h2>
        <div class="space-y-3">
{faq_items}
        </div>
    </section>

    <!-- FOOTER -->
    <footer class="bg-gray-900 text-gray-400 text-sm mt-8">
        <div class="max-w-5xl mx-auto px-4 py-10 grid grid-cols-2 md:grid-cols-4 gap-8">
            <div>
                <div class="text-white font-bold text-lg mb-3">Lawly</div>
                <p class="text-xs leading-relaxed">India's AI-powered legal notice platform. Send a lawyer-quality notice in 5 minutes for ₹199.</p>
            </div>
            <div>
                <div class="text-white font-semibold mb-3">Consumer Complaints</div>
                <ul class="space-y-1.5 text-xs">
                    <li><a href="/consumer-complaint-india" class="hover:text-white">Consumer Complaint India</a></li>
                    <li><a href="/consumer-complaint-ecommerce" class="hover:text-white">E-Commerce</a></li>
                    <li><a href="/consumer-complaint-bank" class="hover:text-white">Bank</a></li>
                    <li><a href="/consumer-complaint-telecom" class="hover:text-white">Telecom</a></li>
                    <li><a href="/consumer-complaint-travel" class="hover:text-white">Travel</a></li>
                    <li><a href="/consumer-complaint-education" class="hover:text-white">Education</a></li>
                    <li><a href="/consumer-complaint-home-appliances" class="hover:text-white">Home Appliances</a></li>
                    <li><a href="/consumer-complaint-food-delivery" class="hover:text-white">Food Delivery</a></li>
                    <li><a href="/consumer-complaint-real-estate" class="hover:text-white">Real Estate</a></li>
                </ul>
            </div>
            <div>
                <div class="text-white font-semibold mb-3">Legal Notices</div>
                <ul class="space-y-1.5 text-xs">
                    <li><a href="/send-legal-notice-india" class="hover:text-white">Send Legal Notice</a></li>
                    <li><a href="/legal-notice-for-refund" class="hover:text-white">Refund Notice</a></li>
                    <li><a href="/legal-notice-cheque-bounce" class="hover:text-white">Cheque Bounce</a></li>
                    <li><a href="/legal-notice-recovery-of-money" class="hover:text-white">Money Recovery</a></li>
                    <li><a href="/legal-notice-builder-delay" class="hover:text-white">Builder Delay</a></li>
                    <li><a href="/legal-notice-consumer-protection-act" class="hover:text-white">Consumer Protection Act</a></li>
                    <li><a href="/legal-notice-tenant-landlord" class="hover:text-white">Tenant / Landlord</a></li>
                </ul>
            </div>
            <div>
                <div class="text-white font-semibold mb-3">Resources</div>
                <ul class="space-y-1.5 text-xs">
                    <li><a href="/what-is-a-legal-notice" class="hover:text-white">What is a Legal Notice?</a></li>
                    <li><a href="/how-to-send-legal-notice-india" class="hover:text-white">How to Send a Notice</a></li>
                    <li><a href="/legal-notice-format-india" class="hover:text-white">Legal Notice Format</a></li>
                    <li><a href="/reply-to-legal-notice" class="hover:text-white">Reply to Legal Notice</a></li>
                </ul>
            </div>
        </div>
        <div class="border-t border-gray-800 text-center py-4 text-xs text-gray-600">
            &copy; 2026 Lawly &mdash; lawly.store. For information only; not legal advice.
        </div>
    </footer>

</body>
</html>"""


def main():
    os.makedirs(STATIC_DIR, exist_ok=True)
    for page in PAGES:
        html = generate_page(page)
        path = os.path.join(STATIC_DIR, f"{page['slug']}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✓ Generated {page['slug']}.html ({len(html):,} chars)")
    print(f"\nDone. {len(PAGES)} pages written to {STATIC_DIR}")


if __name__ == "__main__":
    main()
