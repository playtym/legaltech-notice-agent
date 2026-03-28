from create_page import generate_page
import os

os.makedirs("static/templates", exist_ok=True)

templates = [
    ("Legal Notice Format for Unpaid Salary", "unpaid-salary-legal-notice-format"),
    ("Legal Notice Format for Defective Product", "defective-product-legal-notice-format"),
    ("Legal Notice Format for Cheque Bounce", "cheque-bounce-legal-notice-format"),
    ("Legal Notice Format for Eviction of Tenant", "tenant-eviction-legal-notice-format"),
    ("Legal Notice to Builder for Delay in Possession", "builder-delay-legal-notice-format"),
    ("Legal Notice Format for Consumer Protection", "consumer-complaint-legal-notice-format"),
    ("Legal Notice Format for Recovery of Dues", "money-recovery-legal-notice-format")
]

for title_topic, slug in templates:
    # Notice we override the base directory locally since create_page enforces "static/"
    full_slug = f"templates/{slug}"
    
    title = f"{title_topic} PDF & Word Download | Lawly"
    desc = f"Looking for a free {title_topic.lower()}? Download our tested draft format or use our AI tool to generate a customized watertight legal notice."
    h1 = f"{title_topic}"
    
    content = f"""<p>If you're searching for a <strong>{title_topic.lower()}</strong> in PDF or Word (Docx) format, it's important to understand that generic templates often fail to capture the specific nuances of your legal dispute.</p>
<p>While you can download hundreds of free formats online, copying and pasting a template poses significant risks. Missing a crucial clause, getting the jurisdiction wrong, or failing to cite the latest governing acts can render your notice legally invalid.</p>

<h3 class="text-xl font-bold mt-6 mb-3 text-gray-900">Essential components your notice MUST have:</h3>
<ul class="list-disc pl-6 space-y-2 text-gray-700">
    <li>Clear identification of the sender and the recipient with registered addresses.</li>
    <li>A precise timeline of events leading up to the dispute.</li>
    <li>Explicit calculation of damages, unpaid sums, and compensation sought.</li>
    <li>A strict deadline (usually 15-30 days) for the recipient to comply before legal action is initiated.</li>
    <li>Proper legal foundation explicitly citing the relevant acts (e.g., Consumer Protection Act, Negotiable Instruments Act).</li>
</ul>

<div class="mt-8 p-6 bg-yellow-50 border border-yellow-200 rounded-lg">
    <h4 class="text-lg font-bold text-yellow-800 mb-2">⚠️ Warning: Don't risk a DIY mistake</h4>
    <p class="text-yellow-700">Instead of downloading a static format and struggling to fill in the blanks correctly, use Lawly. Our intelligent engine asks you plain-English questions and generates a lawyer-grade, fully customized notice in just 3 minutes.</p>
</div>
"""

    faqs = [
        ("Should I send the notice via email or registered post?", 
         "Legally, it is always recommended to send the notice via Registered Post with Acknowledgment Due (RPAD). However, simultaneously emailing the notice to the official grievance or legal desk of the company is a best practice."),
        ("What happens after I send this notice?", 
         "The recipient has a stipulated time (usually 15 to 30 days) to reply or fulfill your demands. If they ignore it or refuse, you can proceed to file a formal case in the appropriate court or forum."),
        (f"Is a lawyer mandatory to send a {title_topic.lower()}?", 
         "No. Any individual can draft and send a legal notice on their own behalf under Indian law. As long as the notice contains the correct legal structure and facts, it holds full validity.")
    ]

    # Temporarily modify create_page to accept subdirectories in slug. 
    # Since create_page natively does filename = f"static/{slug}.html", f"static/templates/..." will work perfectly.
    
    generate_page(full_slug, title, desc, h1, content, faqs=faqs)

print("\\n🎉 Generated 7 template SEO landing pages!")