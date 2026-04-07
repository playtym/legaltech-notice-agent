#!/usr/bin/env python3
"""
gen_competitor_gap_pages.py
Generates 8 pages to fill SEO gaps vs VakilSearch, eDrafter, IndiaFilings.

Consumer Complaint Sectors (new):
  consumer-complaint-insurance
  consumer-complaint-automobile
  consumer-complaint-medical
  consumer-complaint-courier

Legal Notice Types (new):
  legal-notice-salary-not-paid
  legal-notice-property-dispute
  legal-notice-defamation
  legal-notice-medical-negligence
"""

from pathlib import Path

STATIC = Path(__file__).parent / "static"
GA = "G-F63GR76DSR"

# ─────────────────────────────────────────────────────────────────────────────
# SECTOR PAGE TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────

def sector_html(cfg: dict) -> str:
    slug = cfg["slug"]
    title = cfg["title"]
    meta_desc = cfg["meta_desc"]
    h1 = cfg["h1"]
    sector_name = cfg["sector_name"]
    regulator = cfg["regulator"]
    regulator_note = cfg["regulator_note"]
    rights = cfg["rights"]          # list of (right_name, legal_basis, desc)
    complaints = cfg["complaints"]  # list of strings
    steps = cfg["steps"]           # list of (step_title, step_desc)
    companies = cfg["companies"]   # list of (name, slug_or_none)
    faqs = cfg["faqs"]             # list of (q, a)
    governing_law = cfg["governing_law"]
    compensation_note = cfg["compensation_note"]

    rights_rows = "\n".join(
        f"""<tr class="border-b"><td class="py-3 px-4 font-medium text-gray-800">{r[0]}</td>
<td class="py-3 px-4 text-xs text-indigo-700 font-mono">{r[1]}</td>
<td class="py-3 px-4 text-gray-600">{r[2]}</td></tr>"""
        for r in rights
    )

    complaint_items = "\n".join(
        f'<li class="flex items-start gap-2"><span class="text-red-500 mt-1">✗</span><span>{c}</span></li>'
        for c in complaints
    )

    steps_html = "\n".join(
        f"""<div class="flex gap-4 items-start">
  <div class="bg-indigo-600 text-white w-8 h-8 rounded-full flex items-center justify-center font-bold flex-shrink-0">{i+1}</div>
  <div><p class="font-semibold text-gray-800">{s[0]}</p><p class="text-gray-600 text-sm mt-1">{s[1]}</p></div>
</div>"""
        for i, s in enumerate(steps)
    )

    company_cards = "\n".join(
        f"""<a href="/{c[1]}" class="border rounded-lg p-3 text-center hover:border-indigo-400 hover:bg-indigo-50 transition">
  <p class="font-semibold text-gray-800 text-sm">{c[0]}</p>
  <p class="text-xs text-indigo-600 mt-1">File Complaint →</p>
</a>"""
        if c[1] else
        f"""<div class="border rounded-lg p-3 text-center bg-gray-50">
  <p class="font-semibold text-gray-700 text-sm">{c[0]}</p>
  <p class="text-xs text-gray-400 mt-1">Via Consumer Commission</p>
</div>"""
        for c in companies
    )

    faq_items = "\n".join(
        f"""<div class="border-b pb-4">
  <button class="w-full text-left font-semibold text-gray-800 flex justify-between items-center" onclick="this.nextElementSibling.classList.toggle('hidden');this.querySelector('span').textContent=this.nextElementSibling.classList.contains('hidden')?'+':'−'">
    {q}<span class="text-indigo-600 text-xl">+</span>
  </button>
  <p class="mt-3 text-gray-600 text-sm hidden">{a}</p>
</div>"""
        for q, a in faqs
    )

    faq_schema = ",\n".join(
        f'''{{"@type":"Question","name":{repr(q)},"acceptedAnswer":{{"@type":"Answer","text":{repr(a)}}}}}'''
        for q, a in faqs
    )

    sector_nav_links = [
        ("E-Commerce", "consumer-complaint-ecommerce"),
        ("Bank", "consumer-complaint-bank"),
        ("Telecom", "consumer-complaint-telecom"),
        ("Travel", "consumer-complaint-travel"),
        ("Education", "consumer-complaint-education"),
        ("Home Appliances", "consumer-complaint-home-appliances"),
        ("Food Delivery", "consumer-complaint-food-delivery"),
        ("Real Estate", "consumer-complaint-real-estate"),
        ("Insurance", "consumer-complaint-insurance"),
        ("Automobile", "consumer-complaint-automobile"),
        ("Medical", "consumer-complaint-medical"),
        ("Courier & Logistics", "consumer-complaint-courier"),
    ]
    sector_nav = "\n".join(
        f'<a href="/{s[1]}" class="text-sm {"font-bold text-indigo-700 underline" if s[1]==slug else "text-indigo-600 hover:underline"}">{s[0]}</a>'
        for s in sector_nav_links
        if s[1] != slug or True
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | Lawly</title>
<meta name="description" content="{meta_desc}">
<link rel="canonical" href="https://lawly.store/{slug}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdn.tailwindcss.com"></script>
<script async src="https://www.googletagmanager.com/gtag/js?id={GA}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','{GA}');</script>
<script type="application/ld+json">
{{
  "@context":"https://schema.org",
  "@graph":[
    {{
      "@type":"BreadcrumbList",
      "itemListElement":[
        {{"@type":"ListItem","position":1,"name":"Home","item":"https://lawly.store/"}},
        {{"@type":"ListItem","position":2,"name":"Consumer Complaint India","item":"https://lawly.store/consumer-complaint-india"}},
        {{"@type":"ListItem","position":3,"name":"{sector_name} Complaint","item":"https://lawly.store/{slug}"}}
      ]
    }},
    {{
      "@type":"FAQPage",
      "mainEntity":[{faq_schema}]
    }},
    {{
      "@type":"Service",
      "name":"{h1}",
      "provider":{{"@type":"Organization","name":"Lawly","url":"https://lawly.store"}},
      "areaServed":{{"@type":"Country","name":"India"}},
      "description":"{meta_desc}",
      "offers":[
        {{"@type":"Offer","name":"AI Legal Notice (Self-Send)","price":"199","priceCurrency":"INR"}},
        {{"@type":"Offer","name":"Lawyer-Drafted Legal Notice","price":"599","priceCurrency":"INR"}}
      ]
    }}
  ]
}}
</script>
<style>body{{font-family:'Inter',sans-serif}}</style>
</head>
<body class="bg-gray-50 text-gray-900">

<!-- NAV -->
<nav class="bg-white border-b sticky top-0 z-50">
  <div class="max-w-6xl mx-auto px-4 py-3 flex justify-between items-center">
    <a href="/" class="text-xl font-black text-indigo-700">Lawly</a>
    <div class="hidden md:flex gap-6 text-sm font-medium">
      <a href="/consumer-complaint-india" class="text-gray-600 hover:text-indigo-600">Consumer Complaints</a>
      <a href="/send-legal-notice-india" class="text-gray-600 hover:text-indigo-600">Send Legal Notice</a>
    </div>
    <a href="/" class="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700">Send Notice ₹199</a>
  </div>
</nav>

<!-- HERO -->
<section class="bg-gradient-to-br from-indigo-700 to-indigo-900 text-white py-12 px-4">
  <div class="max-w-4xl mx-auto">
    <nav class="text-indigo-200 text-xs mb-4">
      <a href="/" class="hover:text-white">Home</a> › <a href="/consumer-complaint-india" class="hover:text-white">Consumer Complaint India</a> › {sector_name}
    </nav>
    <h1 class="text-3xl md:text-4xl font-black mb-4">{h1}</h1>
    <p class="text-indigo-100 text-lg max-w-2xl">{meta_desc}</p>
    <div class="mt-6 flex flex-wrap gap-3">
      <a href="/" class="bg-yellow-400 text-gray-900 px-6 py-3 rounded-xl font-bold hover:bg-yellow-300">Send Legal Notice — ₹199</a>
      <a href="/" class="border border-white text-white px-6 py-3 rounded-xl font-semibold hover:bg-white hover:text-indigo-700">Lawyer-Drafted — ₹599</a>
    </div>
    <div class="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="bg-white/10 rounded-lg p-3 text-center"><p class="text-2xl font-black">15,000+</p><p class="text-xs text-indigo-200">Disputes Resolved</p></div>
      <div class="bg-white/10 rounded-lg p-3 text-center"><p class="text-2xl font-black">₹199</p><p class="text-xs text-indigo-200">Starting Price</p></div>
      <div class="bg-white/10 rounded-lg p-3 text-center"><p class="text-2xl font-black">5 min</p><p class="text-xs text-indigo-200">Notice Ready</p></div>
      <div class="bg-white/10 rounded-lg p-3 text-center"><p class="text-2xl font-black">87%</p><p class="text-xs text-indigo-200">Pre-Court Resolution</p></div>
    </div>
  </div>
</section>

<!-- MAIN -->
<main class="max-w-4xl mx-auto px-4 py-10">

  <!-- QUICK WINS BOX -->
  <div class="bg-green-50 border border-green-200 rounded-xl p-5 mb-8">
    <p class="font-bold text-green-800 mb-1">Quick Answer: Your rights under {governing_law}</p>
    <p class="text-green-700 text-sm">{compensation_note}</p>
  </div>

  <!-- REGULATOR CALLOUT -->
  <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-8 rounded-r-xl">
    <p class="font-semibold text-yellow-800">Governing Body: {regulator}</p>
    <p class="text-yellow-700 text-sm mt-1">{regulator_note}</p>
  </div>

  <!-- RIGHTS TABLE -->
  <h2 class="text-2xl font-bold mb-4">Your Legal Rights as a Consumer</h2>
  <div class="overflow-x-auto mb-8 rounded-xl border">
    <table class="w-full text-sm">
      <thead class="bg-indigo-600 text-white">
        <tr>
          <th class="py-3 px-4 text-left">Your Right</th>
          <th class="py-3 px-4 text-left">Legal Basis</th>
          <th class="py-3 px-4 text-left">What It Means</th>
        </tr>
      </thead>
      <tbody class="bg-white">
        {rights_rows}
      </tbody>
    </table>
  </div>

  <!-- COMMON COMPLAINTS -->
  <h2 class="text-2xl font-bold mb-4">Common {sector_name} Consumer Complaints</h2>
  <div class="bg-white border rounded-xl p-6 mb-8">
    <ul class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
      {complaint_items}
    </ul>
  </div>

  <!-- HOW TO FILE -->
  <h2 class="text-2xl font-bold mb-4">How to File a {sector_name} Consumer Complaint</h2>
  <div class="bg-white border rounded-xl p-6 space-y-5 mb-8">
    {steps_html}
  </div>

  <!-- COMPANY GRID -->
  <h2 class="text-2xl font-bold mb-4">File Complaint Against Specific Companies</h2>
  <div class="grid grid-cols-2 md:grid-cols-3 gap-3 mb-8">
    {company_cards}
  </div>

  <!-- LAWLY CTA -->
  <div class="bg-indigo-50 border border-indigo-200 rounded-xl p-6 mb-8">
    <h2 class="text-xl font-bold text-indigo-900 mb-2">Skip the Wait — Send a Legal Notice in 5 Minutes</h2>
    <p class="text-indigo-700 text-sm mb-4">A legal notice forces companies to respond within 15–30 days or face Consumer Commission proceedings. <strong>Lawly is 7–20× cheaper than VakilSearch or IndiaFilings.</strong></p>
    <div class="flex flex-wrap gap-3">
      <a href="/" class="bg-indigo-600 text-white px-5 py-2.5 rounded-lg font-semibold hover:bg-indigo-700">AI Self-Send — ₹199</a>
      <a href="/" class="bg-white border border-indigo-600 text-indigo-600 px-5 py-2.5 rounded-lg font-semibold hover:bg-indigo-50">Lawyer-Drafted — ₹599</a>
    </div>
  </div>

  <!-- FAQ -->
  <h2 class="text-2xl font-bold mb-6">Frequently Asked Questions</h2>
  <div class="space-y-4 mb-10">
    {faq_items}
  </div>

  <!-- SECTOR NAV -->
  <div class="bg-gray-100 rounded-xl p-5">
    <p class="font-bold text-gray-700 mb-3 text-sm">All Consumer Complaint Sectors</p>
    <div class="flex flex-wrap gap-3">
      {sector_nav}
    </div>
  </div>

</main>

<!-- FOOTER -->
<footer class="bg-gray-900 text-gray-400 py-10 mt-10">
  <div class="max-w-6xl mx-auto px-4">
    <div class="grid grid-cols-2 md:grid-cols-4 gap-6 text-sm mb-8">
      <div>
        <p class="text-white font-bold mb-3">Legal Notice Types</p>
        <div class="space-y-2">
          <a href="/legal-notice-for-refund" class="block hover:text-white">Refund Not Received</a>
          <a href="/legal-notice-cheque-bounce" class="block hover:text-white">Cheque Bounce</a>
          <a href="/legal-notice-recovery-of-money" class="block hover:text-white">Money Recovery</a>
          <a href="/legal-notice-tenant-landlord" class="block hover:text-white">Tenant / Landlord</a>
          <a href="/legal-notice-salary-not-paid" class="block hover:text-white">Salary Not Paid</a>
          <a href="/legal-notice-property-dispute" class="block hover:text-white">Property Dispute</a>
        </div>
      </div>
      <div>
        <p class="text-white font-bold mb-3">Consumer Complaints</p>
        <div class="space-y-2">
          <a href="/consumer-complaint-ecommerce" class="block hover:text-white">E-Commerce</a>
          <a href="/consumer-complaint-bank" class="block hover:text-white">Banking</a>
          <a href="/consumer-complaint-insurance" class="block hover:text-white">Insurance</a>
          <a href="/consumer-complaint-automobile" class="block hover:text-white">Automobile</a>
          <a href="/consumer-complaint-medical" class="block hover:text-white">Medical</a>
          <a href="/consumer-complaint-courier" class="block hover:text-white">Courier & Logistics</a>
        </div>
      </div>
      <div>
        <p class="text-white font-bold mb-3">More Sectors</p>
        <div class="space-y-2">
          <a href="/consumer-complaint-telecom" class="block hover:text-white">Telecom</a>
          <a href="/consumer-complaint-travel" class="block hover:text-white">Travel</a>
          <a href="/consumer-complaint-education" class="block hover:text-white">Education</a>
          <a href="/consumer-complaint-food-delivery" class="block hover:text-white">Food Delivery</a>
          <a href="/consumer-complaint-home-appliances" class="block hover:text-white">Home Appliances</a>
          <a href="/consumer-complaint-real-estate" class="block hover:text-white">Real Estate</a>
        </div>
      </div>
      <div>
        <p class="text-white font-bold mb-3">Lawly</p>
        <div class="space-y-2">
          <a href="/" class="block hover:text-white">Home</a>
          <a href="/send-legal-notice-india" class="block hover:text-white">Send Legal Notice</a>
          <a href="/consumer-complaint-india" class="block hover:text-white">Consumer Complaint India</a>
          <a href="/how-to-send-legal-notice-india" class="block hover:text-white">How to Send Notice</a>
          <a href="/reply-to-legal-notice" class="block hover:text-white">Reply to Notice</a>
        </div>
      </div>
    </div>
    <p class="text-center text-xs text-gray-500">© 2026 Lawly (lawly.store). AI-powered legal notices in India. Not a law firm. Starting ₹199.</p>
  </div>
</footer>

<script>
// accordion: allow only one open
document.querySelectorAll('[onclick]').forEach(btn => {{
  btn.addEventListener('click', () => {{
    const panel = btn.nextElementSibling;
    const isHidden = panel.classList.contains('hidden');
    document.querySelectorAll('[onclick]').forEach(b => {{
      b.nextElementSibling.classList.add('hidden');
      b.querySelector('span').textContent = '+';
    }});
    if (isHidden) {{
      panel.classList.remove('hidden');
      btn.querySelector('span').textContent = '−';
    }}
  }});
}});
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# LEGAL NOTICE PAGE TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────

def notice_html(cfg: dict) -> str:
    slug = cfg["slug"]
    title = cfg["title"]
    meta_desc = cfg["meta_desc"]
    h1 = cfg["h1"]
    notice_type = cfg["notice_type"]
    law_basis = cfg["law_basis"]
    quick_answer = cfg["quick_answer"]
    when_to_send = cfg["when_to_send"]    # list of strings
    checklist = cfg["checklist"]          # list of strings
    steps = cfg["steps"]                  # list of (title, desc)
    faqs = cfg["faqs"]                    # list of (q, a)
    limitation = cfg["limitation"]        # string: time limit to send notice
    governing_laws = cfg["governing_laws"]  # list of (law_name, section, what_it_covers)

    checklist_items = "\n".join(
        f'<li class="flex items-start gap-2"><span class="text-green-500">✓</span><span>{c}</span></li>'
        for c in checklist
    )

    when_items = "\n".join(
        f'<li class="flex items-start gap-2"><span class="text-orange-500 mt-0.5">→</span><span>{w}</span></li>'
        for w in when_to_send
    )

    steps_html = "\n".join(
        f"""<div class="flex gap-4 items-start">
  <div class="bg-indigo-600 text-white w-8 h-8 rounded-full flex items-center justify-center font-bold flex-shrink-0">{i+1}</div>
  <div><p class="font-semibold text-gray-800">{s[0]}</p><p class="text-gray-600 text-sm mt-1">{s[1]}</p></div>
</div>"""
        for i, s in enumerate(steps)
    )

    law_rows = "\n".join(
        f"""<tr class="border-b"><td class="py-3 px-4 font-medium text-gray-800">{l[0]}</td>
<td class="py-3 px-4 text-xs text-indigo-700 font-mono">{l[1]}</td>
<td class="py-3 px-4 text-gray-600">{l[2]}</td></tr>"""
        for l in governing_laws
    )

    faq_items = "\n".join(
        f"""<div class="border-b pb-4">
  <button class="w-full text-left font-semibold text-gray-800 flex justify-between items-center" onclick="this.nextElementSibling.classList.toggle('hidden');this.querySelector('span').textContent=this.nextElementSibling.classList.contains('hidden')?'+':'−'">
    {q}<span class="text-indigo-600 text-xl">+</span>
  </button>
  <p class="mt-3 text-gray-600 text-sm hidden">{a}</p>
</div>"""
        for q, a in faqs
    )

    faq_schema = ",\n".join(
        f'''{{"@type":"Question","name":{repr(q)},"acceptedAnswer":{{"@type":"Answer","text":{repr(a)}}}}}'''
        for q, a in faqs
    )

    how_to_schema_steps = ",\n".join(
        f'''{{"@type":"HowToStep","name":{repr(s[0])},"text":{repr(s[1])}}}'''
        for s in steps
    )

    notice_type_links = [
        ("Refund Not Received", "legal-notice-for-refund"),
        ("Cheque Bounce", "legal-notice-cheque-bounce"),
        ("Money Recovery", "legal-notice-recovery-of-money"),
        ("Insurance Claim", "legal-notice-insurance-claim-rejected"),
        ("Builder Delay (RERA)", "legal-notice-builder-delay"),
        ("UPI Payment Failure", "legal-notice-upi-payment-failure"),
        ("Flight Cancellation", "legal-notice-flight-cancellation"),
        ("Tenant / Landlord", "legal-notice-tenant-landlord"),
        ("Consumer Protection Act", "legal-notice-consumer-protection-act"),
        ("Salary Not Paid", "legal-notice-salary-not-paid"),
        ("Property Dispute", "legal-notice-property-dispute"),
        ("Defamation", "legal-notice-defamation"),
        ("Medical Negligence", "legal-notice-medical-negligence"),
    ]
    notice_nav = "\n".join(
        f'<a href="/{n[1]}" class="text-sm {"font-bold text-indigo-700 underline" if n[1]==slug else "text-indigo-600 hover:underline"}">{n[0]}</a>'
        for n in notice_type_links
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | Lawly</title>
<meta name="description" content="{meta_desc}">
<link rel="canonical" href="https://lawly.store/{slug}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdn.tailwindcss.com"></script>
<script async src="https://www.googletagmanager.com/gtag/js?id={GA}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','{GA}');</script>
<script type="application/ld+json">
{{
  "@context":"https://schema.org",
  "@graph":[
    {{
      "@type":"BreadcrumbList",
      "itemListElement":[
        {{"@type":"ListItem","position":1,"name":"Home","item":"https://lawly.store/"}},
        {{"@type":"ListItem","position":2,"name":"Send Legal Notice India","item":"https://lawly.store/send-legal-notice-india"}},
        {{"@type":"ListItem","position":3,"name":"{notice_type} Legal Notice","item":"https://lawly.store/{slug}"}}
      ]
    }},
    {{
      "@type":"HowTo",
      "name":"How to Send a {notice_type} Legal Notice in India",
      "step":[{how_to_schema_steps}]
    }},
    {{
      "@type":"FAQPage",
      "mainEntity":[{faq_schema}]
    }}
  ]
}}
</script>
<style>body{{font-family:'Inter',sans-serif}}</style>
</head>
<body class="bg-gray-50 text-gray-900">

<!-- NAV -->
<nav class="bg-white border-b sticky top-0 z-50">
  <div class="max-w-6xl mx-auto px-4 py-3 flex justify-between items-center">
    <a href="/" class="text-xl font-black text-indigo-700">Lawly</a>
    <div class="hidden md:flex gap-6 text-sm font-medium">
      <a href="/send-legal-notice-india" class="text-gray-600 hover:text-indigo-600">Legal Notices</a>
      <a href="/consumer-complaint-india" class="text-gray-600 hover:text-indigo-600">Consumer Complaints</a>
    </div>
    <a href="/" class="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700">Send Notice ₹199</a>
  </div>
</nav>

<!-- HERO -->
<section class="bg-gradient-to-br from-gray-900 to-indigo-900 text-white py-12 px-4">
  <div class="max-w-4xl mx-auto">
    <nav class="text-indigo-200 text-xs mb-4">
      <a href="/" class="hover:text-white">Home</a> › <a href="/send-legal-notice-india" class="hover:text-white">Legal Notices</a> › {notice_type}
    </nav>
    <h1 class="text-3xl md:text-4xl font-black mb-4">{h1}</h1>
    <p class="text-indigo-100 text-lg max-w-2xl">{meta_desc}</p>
    <div class="mt-6 flex flex-wrap gap-3">
      <a href="/" class="bg-yellow-400 text-gray-900 px-6 py-3 rounded-xl font-bold hover:bg-yellow-300">AI Draft — ₹199</a>
      <a href="/" class="border border-white text-white px-6 py-3 rounded-xl font-semibold hover:bg-white hover:text-indigo-700">Lawyer-Drafted — ₹599</a>
    </div>
    <div class="mt-6 bg-white/10 rounded-xl p-4 text-sm">
      <span class="text-yellow-300 font-semibold">⚠ Time Limit:</span> {limitation}
    </div>
  </div>
</section>

<!-- MAIN -->
<main class="max-w-4xl mx-auto px-4 py-10">

  <!-- QUICK ANSWER -->
  <div class="bg-green-50 border border-green-200 rounded-xl p-5 mb-8">
    <p class="font-bold text-green-800 mb-1">Quick Answer</p>
    <p class="text-green-700 text-sm">{quick_answer}</p>
  </div>

  <!-- WHEN TO SEND -->
  <h2 class="text-2xl font-bold mb-4">When to Send a {notice_type} Legal Notice</h2>
  <div class="bg-white border rounded-xl p-5 mb-8">
    <ul class="space-y-3 text-sm">
      {when_items}
    </ul>
  </div>

  <!-- LAW TABLE -->
  <h2 class="text-2xl font-bold mb-4">Governing Laws</h2>
  <div class="overflow-x-auto mb-8 rounded-xl border">
    <table class="w-full text-sm">
      <thead class="bg-indigo-600 text-white">
        <tr>
          <th class="py-3 px-4 text-left">Law / Act</th>
          <th class="py-3 px-4 text-left">Section</th>
          <th class="py-3 px-4 text-left">What It Covers</th>
        </tr>
      </thead>
      <tbody class="bg-white">
        {law_rows}
      </tbody>
    </table>
  </div>

  <!-- CHECKLIST -->
  <h2 class="text-2xl font-bold mb-4">What to Include in the Notice</h2>
  <div class="bg-white border rounded-xl p-6 mb-8">
    <ul class="space-y-3 text-sm">
      {checklist_items}
    </ul>
  </div>

  <!-- STEPS -->
  <h2 class="text-2xl font-bold mb-4">How to Send This Legal Notice</h2>
  <div class="bg-white border rounded-xl p-6 space-y-5 mb-8">
    {steps_html}
  </div>

  <!-- CTA -->
  <div class="bg-indigo-50 border border-indigo-200 rounded-xl p-6 mb-8">
    <h2 class="text-xl font-bold text-indigo-900 mb-2">Send Your Legal Notice in 5 Minutes — ₹199</h2>
    <p class="text-indigo-700 text-sm mb-4">Lawly's AI drafts a legally valid {notice_type} notice citing exact statute sections. 87% of cases resolved before reaching court. <strong>IndiaFilings charges ₹3,899 for the same service.</strong></p>
    <div class="flex flex-wrap gap-3">
      <a href="/" class="bg-indigo-600 text-white px-5 py-2.5 rounded-lg font-semibold hover:bg-indigo-700">Start Now — ₹199</a>
      <a href="/" class="bg-white border border-indigo-600 text-indigo-600 px-5 py-2.5 rounded-lg font-semibold hover:bg-indigo-50">Lawyer-Drafted — ₹599</a>
    </div>
  </div>

  <!-- FAQ -->
  <h2 class="text-2xl font-bold mb-6">Frequently Asked Questions</h2>
  <div class="space-y-4 mb-10">
    {faq_items}
  </div>

  <!-- NOTICE TYPE NAV -->
  <div class="bg-gray-100 rounded-xl p-5">
    <p class="font-bold text-gray-700 mb-3 text-sm">All Legal Notice Types</p>
    <div class="flex flex-wrap gap-3">
      {notice_nav}
    </div>
  </div>

</main>

<!-- FOOTER -->
<footer class="bg-gray-900 text-gray-400 py-10 mt-10">
  <div class="max-w-6xl mx-auto px-4">
    <div class="grid grid-cols-2 md:grid-cols-4 gap-6 text-sm mb-8">
      <div>
        <p class="text-white font-bold mb-3">Legal Notice Types</p>
        <div class="space-y-2">
          <a href="/legal-notice-for-refund" class="block hover:text-white">Refund Not Received</a>
          <a href="/legal-notice-cheque-bounce" class="block hover:text-white">Cheque Bounce</a>
          <a href="/legal-notice-recovery-of-money" class="block hover:text-white">Money Recovery</a>
          <a href="/legal-notice-salary-not-paid" class="block hover:text-white">Salary Not Paid</a>
          <a href="/legal-notice-property-dispute" class="block hover:text-white">Property Dispute</a>
          <a href="/legal-notice-defamation" class="block hover:text-white">Defamation</a>
          <a href="/legal-notice-medical-negligence" class="block hover:text-white">Medical Negligence</a>
        </div>
      </div>
      <div>
        <p class="text-white font-bold mb-3">Consumer Complaints</p>
        <div class="space-y-2">
          <a href="/consumer-complaint-insurance" class="block hover:text-white">Insurance</a>
          <a href="/consumer-complaint-automobile" class="block hover:text-white">Automobile</a>
          <a href="/consumer-complaint-medical" class="block hover:text-white">Medical</a>
          <a href="/consumer-complaint-courier" class="block hover:text-white">Courier & Logistics</a>
          <a href="/consumer-complaint-ecommerce" class="block hover:text-white">E-Commerce</a>
          <a href="/consumer-complaint-bank" class="block hover:text-white">Banking</a>
        </div>
      </div>
      <div>
        <p class="text-white font-bold mb-3">More Sectors</p>
        <div class="space-y-2">
          <a href="/consumer-complaint-telecom" class="block hover:text-white">Telecom</a>
          <a href="/consumer-complaint-travel" class="block hover:text-white">Travel</a>
          <a href="/consumer-complaint-education" class="block hover:text-white">Education</a>
          <a href="/consumer-complaint-food-delivery" class="block hover:text-white">Food Delivery</a>
          <a href="/consumer-complaint-home-appliances" class="block hover:text-white">Home Appliances</a>
          <a href="/consumer-complaint-real-estate" class="block hover:text-white">Real Estate</a>
        </div>
      </div>
      <div>
        <p class="text-white font-bold mb-3">Lawly</p>
        <div class="space-y-2">
          <a href="/" class="block hover:text-white">Home</a>
          <a href="/send-legal-notice-india" class="block hover:text-white">Send Legal Notice</a>
          <a href="/consumer-complaint-india" class="block hover:text-white">Consumer Complaint India</a>
          <a href="/consumer-complaint-india" class="block hover:text-white">All Sectors</a>
          <a href="/reply-to-legal-notice" class="block hover:text-white">Reply to Notice</a>
        </div>
      </div>
    </div>
    <p class="text-center text-xs text-gray-500">© 2026 Lawly (lawly.store). AI-powered legal notices in India. Not a law firm. Starting ₹199.</p>
  </div>
</footer>

<script>
document.querySelectorAll('[onclick]').forEach(btn => {{
  btn.addEventListener('click', () => {{
    const panel = btn.nextElementSibling;
    const isHidden = panel.classList.contains('hidden');
    document.querySelectorAll('[onclick]').forEach(b => {{
      b.nextElementSibling.classList.add('hidden');
      b.querySelector('span').textContent = '+';
    }});
    if (isHidden) {{
      panel.classList.remove('hidden');
      btn.querySelector('span').textContent = '−';
    }}
  }});
}});
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIGS
# ─────────────────────────────────────────────────────────────────────────────

SECTOR_PAGES = [

    # ── INSURANCE ────────────────────────────────────────────────────────────
    {
        "slug": "consumer-complaint-insurance",
        "title": "Insurance Consumer Complaint India — LIC, Star Health, IRDAI Ombudsman",
        "meta_desc": "File an insurance consumer complaint against LIC, Star Health, Bajaj Allianz, HDFC Ergo in India. IRDAI Ombudsman is free. Send a legal notice in 5 min at ₹199.",
        "h1": "Insurance Consumer Complaint India — IRDAI Ombudsman + Legal Notice",
        "sector_name": "Insurance",
        "regulator": "IRDAI (Insurance Regulatory and Development Authority of India)",
        "regulator_note": "IRDAI Integrated Grievance Management System (IGMS) at igms.irda.gov.in allows online complaints against any registered insurer. IRDAI Insurance Ombudsman handles disputes up to ₹50 lakh FREE of cost. A prior legal notice to the insurer strengthens your Ombudsman case.",
        "governing_law": "Insurance Act 1938 + CPA 2019",
        "compensation_note": "Under CPA 2019 §2(11) and §36, insurance claim rejection counts as 'deficiency in service'. You can claim: full settlement amount + interest + compensation up to ₹1 crore in District Commission or directly via IRDAI Ombudsman (free, up to ₹50L).",
        "rights": [
            ("Right to Claim Settlement", "Insurance Act 1938 §45", "Insurer cannot reject claims after 3 years on grounds of mis-statement"),
            ("Right Against Unfair Rejection", "CPA 2019 §2(11)", "Unjust rejection of valid claim = deficiency in service"),
            ("Right to Ombudsman Grievance", "Insurance Ombudsman Rules 2017 Rule 14", "Free dispute resolution up to ₹50 lakh without going to court"),
            ("Right to IRDAI IGMS Complaint", "IRDAI (IGMS) Regulations 2010", "Online complaint portal; insurer must respond within 14 days"),
            ("Right to Consumer Commission", "CPA 2019 §35", "File in DCDRC (up to ₹1 crore) or SCDRC/NCDRC for larger claims"),
        ],
        "complaints": [
            "Health insurance claim fully or partially rejected without valid reason",
            "Life insurance maturity/death benefit payment delayed or denied",
            "Motor insurance claim rejected citing 'policy lapse' or 'exclusion clause'",
            "Cashless hospital treatment denied despite valid policy",
            "Insurer cancelling policy without notice or refunding incorrect premium",
            "TPA (Third Party Administrator) not processing claim within 30 days",
            "Insurance agent misselling policy; features misrepresented at time of sale",
            "Surrender value / ULIP fund value not returned within stipulated period",
        ],
        "steps": [
            ("Lodge Internal Grievance with Insurer", "Email the insurer's Grievance Redressal Officer (GRO) with policy number, claim ID, and problem details. Insurers are required by IRDAI to respond within 15 days."),
            ("Send a Formal Legal Notice", "If the GRO response is unsatisfactory, send a legal notice via Lawly citing CPA 2019 §2(11) and Insurance Act §45. This creates a legal record and often triggers faster settlement (87% resolution rate)."),
            ("File with IRDAI Ombudsman", "If unresolved after 30 days (or GRO rejection), file at igms.irda.gov.in or contact your regional Insurance Ombudsman. Free process, up to ₹50 lakh disputes."),
            ("Approach Consumer Commission", "For rejected Ombudsman cases or amounts above ₹50L: file in DCDRC under CPA 2019 §35. Attach legal notice + GRO response + claim documents."),
        ],
        "companies": [
            ("LIC of India", None),
            ("Star Health Insurance", None),
            ("Bajaj Allianz", None),
            ("HDFC Ergo", None),
            ("New India Assurance", None),
            ("SBI Life Insurance", None),
            ("ICICI Lombard", None),
            ("Reliance General Insurance", None),
            ("Max Life Insurance", None),
            ("Niva Bupa (Max Bupa)", None),
        ],
        "faqs": [
            ("Can I complain against my insurance company without going to court?", "Yes. The IRDAI Insurance Ombudsman handles insurance disputes up to ₹50 lakh for FREE. File at igms.irda.gov.in or through the regional Ombudsman office. A legal notice before filing strengthens your case significantly."),
            ("My health insurance claim was rejected. What can I do?", "Step 1: Request a written rejection citing specific policy clause. Step 2: Send a legal notice to insurer's GRO via Lawly (₹199). Step 3: File with IRDAI Ombudsman if unresolved in 30 days. Step 4: Consumer Commission for compensation beyond ₹50L."),
            ("How long does an insurer have to settle a claim?", "As per IRDAI regulations, a health insurer must settle a claim within 30 days of receiving all documents. Life insurance maturity claims must be paid within 30 days of the policy anniversary. Delays attract interest at 2% above bank rate."),
            ("Can I file a consumer complaint for insurance mis-selling?", "Yes. Insurance mis-selling — where the agent falsely described policy features — is an unfair trade practice under CPA 2019 §2(47). You can claim full refund of premium + compensation. File via IRDAI Ombudsman or District Consumer Commission."),
            ("What is the IRDAI Complaint Toll-Free Number?", "IRDAI Bima Bharosa helpline: 155255 (toll-free). Online complaints: igms.irda.gov.in. You can also email complaints@irdai.gov.in. For Insurance Ombudsman contacts, visit cioins.co.in."),
        ],
    },

    # ── AUTOMOBILE ───────────────────────────────────────────────────────────
    {
        "slug": "consumer-complaint-automobile",
        "title": "Automobile Consumer Complaint India — Car/Bike Dealer & Service Center Fraud",
        "meta_desc": "File a car or bike consumer complaint in India against Maruti, Hyundai, Tata, Hero, Bajaj dealers and service centers. Legal notice in 5 min at ₹199.",
        "h1": "Automobile Consumer Complaint India — Car & Bike Dealer Fraud Legal Notice",
        "sector_name": "Automobile",
        "regulator": "Consumer Protection Act 2019 + Motor Vehicles Act 1988 + BIS Standards",
        "regulator_note": "Vehicle-related disputes fall under CPA 2019. Manufacturing defects in vehicles are covered under CPA 2019 Chapter VI (Product Liability, §83–§87). The MoRTH (Ministry of Road Transport) handles recalls. SIAM (Society of Indian Automobile Manufacturers) issues quality certifications but consumer redressal goes through Consumer Commissions.",
        "governing_law": "CPA 2019 + Motor Vehicles Act 1988",
        "compensation_note": "Under CPA 2019 §83–§87 (product liability), a manufacturer is strictly liable for defects causing harm. You can claim: repair/replacement cost + compensation for mental agony + difference in actual vs promised value. Manufacturing defects proven by an independent technical expert get full replacement value under 'lemon law' principles.",
        "rights": [
            ("Right to Defect-Free Vehicle", "CPA 2019 §2(10)", "Any manufacturing defect = 'defect in goods' entitling repair, replacement, or refund"),
            ("Right Against Unfair Trade Practice", "CPA 2019 §2(47)", "False promises about mileage, features, safety ratings"),
            ("Product Liability for Manufacturing Defect", "CPA 2019 §83–§87", "Manufacturer liable for defects causing harm; strict liability without need to prove negligence"),
            ("Right to Warranty Service", "Sale of Goods Act 1930 §41", "Dealers must honour manufacturer warranties; denial = breach of contract"),
            ("Right to Replacement/Refund", "CPA 2019 §39(1)(b)", "Commission can award replacement of defective vehicle if defect cannot be rectified"),
        ],
        "complaints": [
            "New vehicle has manufacturing defect (recurring breakdown, rattling, engine issues) within warranty period",
            "Dealer refusing warranty service or demanding extra payment for warranty repairs",
            "Mileage / fuel efficiency significantly lower than ARAI-certified figures advertised",
            "Dealership delivered wrong variant or colour than what was booked",
            "Unauthorized additional charges: anti-rust coating, accessories, insurance forced bundling",
            "Service center using duplicate/inferior parts instead of OEM parts",
            "Vehicle recall defect not fixed despite manufacturer announcement",
            "Accidental damage not repaired properly; vehicle returned with new issues from service center",
        ],
        "steps": [
            ("Document the Defect with Evidence", "Get an independent mechanic's report or take the vehicle to another authorised service center to document the defect in writing. Photographs and videos are critical."),
            ("Send Legal Notice to Dealer + Manufacturer", "A legal notice must go to BOTH the dealer (who sold/serviced the vehicle) and the manufacturer (corporate registered address). Lawly drafts this automatically. Cite CPA 2019 §2(10) for defect in goods."),
            ("Escalate to Manufacturer's Customer Care", "Most manufacturers (Maruti: 1800 102 1800; Hyundai: 1800 11 4645; Tata Motors: 1800 209 7979) have escalation desks. Follow up in writing via email after every call."),
            ("File in Consumer District Commission", "File in DCDRC for the dispute value. Attach: purchase invoice, warranty card, legal notice + proof of dispatch, service records, and defect documentation. No lawyer required for filing."),
        ],
        "companies": [
            ("Maruti Suzuki", None),
            ("Hyundai India", None),
            ("Tata Motors", None),
            ("Honda Cars India", None),
            ("Kia India", None),
            ("Hero MotoCorp", None),
            ("Bajaj Auto", None),
            ("Honda Motorcycles", None),
            ("TVS Motor Company", None),
            ("Royal Enfield", None),
            ("Mahindra & Mahindra", None),
            ("Toyota India", None),
        ],
        "faqs": [
            ("My new car has a manufacturing defect. Can I get a full replacement?", "Yes. Under CPA 2019 §39(1)(b), a Consumer Commission can order replacement of a defective vehicle if the defect cannot be rectified. You need to produce an expert technical report as evidence. The 'lemon law' principle applies — repeated unresolved defects after adequate repair attempts."),
            ("Can I complain about mileage being lower than advertised?", "Yes. ARAI-certified mileage figures advertised by manufacturers constitute trade claims. If actual mileage is significantly lower, this is an unfair trade practice under CPA 2019 §2(47). A technical expert's comparison report strengthens your case."),
            ("The dealer forced me to buy insurance or accessories. Is this legal?", "No. Bundling insurance or accessories as a mandatory condition for vehicle delivery is an unfair trade practice under CPA 2019 §2(47). You can demand a refund for forced add-ons."),
            ("What is the time limit to file an automobile consumer complaint?", "Under CPA 2019, a consumer complaint must be filed within 2 years of the defection/deficiency occurring. For manufacturing defects, this typically runs from the date you discover the defect, not the purchase date."),
            ("Can I file against both the dealer and the manufacturer?", "Yes. You should name both the dealer (OP 1) and the manufacturer/principal (OP 2) as Opposite Parties in your Consumer Commission complaint. Both are jointly and severally liable under CPA 2019."),
        ],
    },

    # ── MEDICAL ──────────────────────────────────────────────────────────────
    {
        "slug": "consumer-complaint-medical",
        "title": "Medical Consumer Complaint India — Hospital & Doctor Negligence Legal Notice",
        "meta_desc": "File a consumer complaint against hospital or doctor negligence in India — Apollo, Fortis, Max, AIIMS. Send a legal notice in 5 min at ₹199. NMC + Consumer Commission.",
        "h1": "Medical Consumer Complaint India — Hospital Negligence Legal Notice",
        "sector_name": "Medical",
        "regulator": "National Medical Commission (NMC) + Consumer Protection Act 2019 (CPA 2019)",
        "regulator_note": "The Supreme Court (Indian Medical Association v. V.P. Shantha, 1995) held that medical services fall under CPA. Patients are 'consumers'. Doctors/hospitals providing services for payment must compensate for negligence. NMC can revoke medical licence. State Medical Councils handle ethics violations. Consumer Commissions award financial compensation.",
        "governing_law": "CPA 2019 + NMC Act 2020",
        "compensation_note": "Medical negligence compensation covers: cost of corrective treatment + loss of income during recovery + pain and suffering + punitive damages in grossly negligent cases. In V.P. Shantha (1995), the SC established the 'reasonable doctor' standard. Awards up to ₹1+ crore in high-profile cases. File in 2-year limitation period from date of negligence.",
        "rights": [
            ("Right to Compensation for Negligence", "CPA 2019 §2(11) + IMA v VP Shantha 1995", "Patients are consumers; medical services = services; negligence = deficiency"),
            ("Right to Informed Consent", "NMC Professional Conduct Regulations 2002 Reg 7.16", "Doctor must explain risks; surgery without informed consent = battery"),
            ("Right to Medical Records", "PC&PNDT Act §5 + MCI Regulations", "Hospitals must provide medical records within 72 hours of request; denial is punishable"),
            ("Right to Second Opinion", "NMC Code of Medical Ethics 2002", "Patient has right to seek second opinion; doctor cannot refuse to share records"),
            ("Right to NMC/State Council Complaint", "NMC Act 2020 §30", "Complaint against doctor's licence to State Medical Council; NMC for appeal"),
        ],
        "complaints": [
            "Surgical error, wrong-site surgery, or instruments left inside patient's body",
            "Misdiagnosis leading to incorrect treatment and worsening of condition",
            "Delayed diagnosis of critical condition (cancer, cardiac, stroke) resulting in harm",
            "Hospital refusing to provide copies of medical records or discharge summary",
            "Unnecessary surgery performed or unnecessary expensive tests prescribed",
            "Death of patient due to avoidable complication; family denied death summary",
            "Overcharging: billing for procedures not performed; charging beyond government rate lists",
            "ICU/COVID patient billing fraud; charging for medicines not administered",
        ],
        "steps": [
            ("Obtain All Medical Records First", "Request (in writing) all records: OPD notes, surgery notes, test reports, nursing notes, discharge summary, bills. Hospitals must provide within 72 hours. If denied, file a police complaint and NMC complaint."),
            ("Get an Independent Medical Expert Opinion", "Take your medical records to an independent specialist. Their written opinion establishing negligence or sub-standard care is the most critical piece of evidence. Without expert evidence, medical negligence cases are difficult to win."),
            ("Send Legal Notice to Hospital + Treating Doctor", "Send via Lawly to both the hospital's CEO/Medical Director and the treating doctor's personal address. Cite CPA 2019 §2(11) and NMC Professional Conduct Regulations. Demand: explanation + compensation."),
            ("File NMC/State Medical Council Complaint", "Simultaneously file with the State Medical Council to initiate disciplinary proceedings against the doctor's licence. This creates pressure independent of the consumer case."),
            ("File Consumer Commission Case", "File in DCDRC (up to ₹1 crore) with: expert opinion, medical records, legal notice + proof, bills. Commission will appoint its own medical board if needed."),
        ],
        "companies": [
            ("Apollo Hospitals", None),
            ("Fortis Healthcare", None),
            ("Max Healthcare", None),
            ("Narayana Health", None),
            ("Medanta", None),
            ("Aster DM Healthcare", None),
            ("Columbia Asia", None),
            ("Manipal Hospitals", None),
            ("AIIMS (Govt)", None),
            ("Government District Hospitals", None),
            ("Practo (Online Consultation)", None),
            ("PharmEasy / NetMeds", None),
        ],
        "faqs": [
            ("Is medical negligence a consumer complaint in India?", "Yes. The Supreme Court in Indian Medical Association v. V.P. Shantha (1995) held that medical services, when provided for payment, fall within CPA. Patients are 'consumers' and doctors/hospitals are 'service providers'. Government hospital services are FREE and hence outside CPA but can be argued in some state courts."),
            ("What is the time limit to file a medical negligence complaint?", "Under CPA 2019 §69, a consumer complaint must be filed within 2 years of the cause of action. For medical negligence, this is typically from the date the patient discovered (or should have discovered) the negligence — known as the 'discovery rule'."),
            ("Do I need a doctor's expert opinion to win?", "Yes. Consumer Commissions require expert medical evidence to establish that the standard of care was breached. Without this, the commission will not find negligence. NCDRC/State Commissions can also appoint their own medical boards."),
            ("Can I complain if a private hospital overcharged me?", "Yes. Billing for procedures not performed, charging above CGHS rates in empanelled hospitals, or charging above the government rate card in regulated hospitals constitutes unfair trade practice under CPA 2019 §2(47). Attach itemized bills as evidence."),
            ("Can I complain against a doctor on Practo or online consultation platforms?", "Yes. Online medical consultation platforms and the doctors on them are bound by the same standards. If negligent advice caused harm, both the platform (as facilitator) and the doctor can be named as Opposite Parties. File with the National Medical Commission as well."),
        ],
    },

    # ── COURIER / LOGISTICS ──────────────────────────────────────────────────
    {
        "slug": "consumer-complaint-courier",
        "title": "Courier & Logistics Consumer Complaint India — Lost or Damaged Parcel",
        "meta_desc": "File a consumer complaint against Blue Dart, DTDC, Delhivery, Ekart, India Post for lost or damaged parcels. Legal notice in 5 min at ₹199. Free Consumer Commission.",
        "h1": "Courier & Logistics Consumer Complaint India — Lost Parcel Legal Notice",
        "sector_name": "Courier & Logistics",
        "regulator": "Consumer Protection Act 2019 + Indian Contract Act 1872 + Carriage by Air Act 1972",
        "regulator_note": "Courier companies are 'service providers' under CPA 2019. Losing or damaging a parcel = deficiency in service under CPA §2(11). India Post grievances go through PG Portal (pgportal.gov.in) or District Superintendent of Posts. Private couriers face Consumer Commission jurisdiction.",
        "governing_law": "CPA 2019 §2(11) + Indian Contract Act §73",
        "compensation_note": "You can claim: declared value of lost/damaged goods + consequential losses (e.g., cost of re-ordering) + mental agony compensation. Couriers often limit liability to ₹100–₹500 in their T&C, but Consumer Commissions have repeatedly held such clauses void under CPA 2019 §2(47) (unfair contract terms). Full declared value recovery is possible.",
        "rights": [
            ("Right to Safe Delivery", "CPA 2019 §2(11)", "Courier must deliver goods safely and on time; loss/damage = deficiency"),
            ("Right Against Unreasonable Liability Caps", "CPA 2019 §2(47)(x)", "Liability limitation clauses that are 'one-sided' are unfair contract terms and void"),
            ("Right to Declared Value Compensation", "Indian Contract Act §73", "Carrier liable for loss arising from breach of contract (carrying obligation)"),
            ("Right Against Delayed Delivery", "CPA 2019 §2(11)", "Unreasonable delivery delays causing loss = deficiency in service"),
            ("Right to India Post Grievance Redressal", "Post Office Act 1898 + PG Portal", "India Post disputes must first go through Superintendent of Posts → PG Portal"),
        ],
        "complaints": [
            "Parcel marked 'delivered' but not received; delivery attempted at wrong address",
            "Package arrived damaged; fragile items broken during transit",
            "Courier lost high-value parcel; refusing to pay declared/actual value",
            "Cash on Delivery (COD) amount collected but not remitted to seller",
            "Return pickup not done; reverse logistics not initiated on time",
            "Parcel stuck in transit / in customs for unreasonable period",
            "Delivery person demanding extra charges for delivery to higher floors",
            "Courier opened and tampered with sealed parcel; contents missing",
        ],
        "steps": [
            ("File Internal Complaint with Courier", "Use the courier's app/website to file a complaint with your tracking number. Note the complaint number. Couriers are required to respond within 7 days per their own policies."),
            ("Send Legal Notice to Courier Company", "Send via Lawly to the courier's registered corporate office address. Cite CPA 2019 §2(11) for deficiency in service. Demand: full cost of lost/damaged item + delivery charges refund + compensation. 87% of cases resolve here."),
            ("Escalate to Consumer Commission", "File in DCDRC in the city where you booked the consignment. Attach: booking receipt/airway bill, parcel value proof (invoice), complaint filed with courier + their response, and legal notice."),
            ("For India Post: Go to Superintendent of Posts", "India Post disputes first go to the Superintendent of Posts of the relevant postal division, then to PG Portal (pgportal.gov.in). India Post has partial immunity under the Post Office Act 1898, but courts have allowed Consumer Commission complaints for registered articles."),
        ],
        "companies": [
            ("Blue Dart (DHL)", "blue-dart-complaints" if Path(STATIC / "blue-dart-complaints.html").exists() else None),
            ("DTDC Courier", None),
            ("Delhivery", None),
            ("Ekart Logistics (Flipkart)", None),
            ("Amazon Logistics", "amazon-complaints" if Path(STATIC / "amazon-complaints.html").exists() else None),
            ("Ecom Express", None),
            ("XpressBees", None),
            ("India Post", None),
            ("Shadowfax", None),
            ("Borzo (WeFast)", None),
            ("FedEx India", None),
            ("Shiprocket", None),
        ],
        "faqs": [
            ("My courier is lost. Can I get full value compensation?", "Yes. Despite couriers' T&C limiting liability to ₹100–₹500, Consumer Commissions have repeatedly held such clauses as unfair contract terms under CPA 2019 §2(47). You can claim the full declared/actual value of the lost item. Attach the invoice as proof of value."),
            ("The courier shows 'delivered' but I never got it. What should I do?", "File an internal complaint immediately asking for proof of delivery (signature, photo). If proof is inadequate, send a legal notice within 15 days. The courier bears the burden of proving actual delivery. If they cannot, they are liable."),
            ("Can I claim compensation for consequential losses (e.g., missed order, client issue)?", "Yes, under Indian Contract Act §73. If the courier was aware (or should have been) of the significance of the shipment and the delay/loss caused consequential loss, you can claim it. Courts have awarded such claims, especially in B2B contexts."),
            ("Against which city's Consumer Commission do I file?", "You can file in the city where you booked the consignment (cause of action arose) OR where the courier company has a branch/office. Choose the more convenient one."),
            ("Is India Post covered by consumer protection laws?", "Partly. India Post has immunity under the Post Office Act 1898 for ordinary articles. But for registered posts, speed posts, and COD, Consumer Commissions have accepted complaints. Also, PG Portal (pgportal.gov.in) is the mandatory first step for India Post grievances."),
        ],
    },
]

NOTICE_PAGES = [

    # ── SALARY NOT PAID ───────────────────────────────────────────────────────
    {
        "slug": "legal-notice-salary-not-paid",
        "title": "Legal Notice for Salary Not Paid India — Unpaid Salary Notice to Employer",
        "meta_desc": "Send a legal notice for unpaid salary in India. Payment of Wages Act + ID Act. Lawly drafts legally valid employment notices in 5 min at ₹199. 87% resolution rate.",
        "h1": "Legal Notice for Salary Not Paid — Unpaid Salary Notice to Employer in India",
        "notice_type": "Salary Not Paid / Employment",
        "law_basis": "Payment of Wages Act 1936 + Industrial Disputes Act 1947 + CPA 2019",
        "quick_answer": "If your employer has not paid your salary, you can send a legal notice under the Payment of Wages Act 1936 (for wages up to ₹24,000/month) or the Industrial Disputes Act 1947. You must first send the notice to give the employer a chance to pay. If unpaid within 15–30 days, you can file with the Labour Commissioner or Civil Court. Small claims can go via Consumer Commission if services were rendered for non-professional employers.",
        "limitation": "Payment of Wages Act applications must be filed within 1 year of wage denial. Industrial Disputes Act references must be made within 3 years. Civil court suit for recovery of salary: 3 years from due date. Send your legal notice IMMEDIATELY — don't wait.",
        "when_to_send": [
            "Employer has not paid salary for 1 or more months despite repeated requests",
            "Employer paid partial salary without explanation or approval",
            "Salary was deducted without valid reason or due process (disciplinary cuts, arbitrary deductions)",
            "Employer is delaying final settlement (F&F) after resignation or termination",
            "Commission, incentives, or overtime pay agreed upon but not paid",
            "Employer issued a cheque that bounced (combine with NI Act §138 cheque bounce notice)",
            "Startup founder / employer claiming 'company has no funds' — still legally liable to pay",
        ],
        "governing_laws": [
            ("Payment of Wages Act 1936", "§3 + §15", "Wages up to ₹24,000/month must be paid on time; late payment attracts 10× compensation"),
            ("Industrial Disputes Act 1947", "§33C + §2A", "Workmen can claim unpaid wages as money dues; wrongful termination remedy"),
            ("Minimum Wages Act 1948", "§3 + §20", "Employer must pay minimum wages for the state/industry; Inspector has powers"),
            ("POSH Act 2013", "§13", "If non-payment follows sexual harassment complaint, it is retaliatory and separately actionable"),
            ("Indian Contract Act 1872", "§55 + §73", "Employment contract breach; claim unpaid dues + damages for breach"),
            ("CPC 1908", "Order 37", "Summary suit for recovery of liquidated money due under contract (fast-track)"),
        ],
        "checklist": [
            "Full legal name and designation of employee (you) + employer (company name + CIN)",
            "Period of non-payment with specific months and exact amount owed",
            "Reference to employment contract / offer letter confirming agreed salary",
            "Evidence of salary previously paid (last salary slip) to establish the pay rate",
            "All communications (WhatsApp, emails) where you requested payment",
            "Bank statement showing salary not credited for the mentioned period",
            "Demand for full unpaid amount + interest at 18% per annum from due date",
            "15–30 day deadline for payment before Labour Commissioner / court filing",
        ],
        "steps": [
            ("Compile Evidence of Non-Payment", "Gather: salary slips for previous months, offer letter / employment contract, bank statements for months where salary was not credited, email/WhatsApp threads demanding payment."),
            ("Draft and Send Legal Notice via Lawly", "Send via registered post to the company's registered address (find via MCA21 portal) AND the employer/HR's personal address. Lawly's AI cites exact sections of Payment of Wages Act 1936 and Industrial Disputes Act 1947. Cost: ₹199."),
            ("File with Labour Commissioner (if unresolved)", "If no response in 15–30 days, approach the Labour Commissioner of your district. Bring the legal notice + postal proof + employment documents. For wages up to ₹24,000/month, the Labour Commissioner can order 10× compensation."),
            ("File Civil Suit / DCDRC for Higher Amounts", "For salary above ₹24,000/month: file a Civil Court recovery suit (CPC Order 37 for summary judgment — fast track). Alternatively, Consumer Commission if employer–employee relationship is non-standard (consultant, freelancer scenario)."),
            ("Claim Provident Fund and Gratuity Separately", "File a separate PF complaint with EPFO if employer deducted PF from salary but didn't remit it. Gratuity (if >5 years service) via the Payment of Gratuity Controlling Authority."),
        ],
        "faqs": [
            ("What is the fastest way to recover unpaid salary in India?", "The fastest route: (1) Send a legal notice via Lawly (₹199) — most employers settle at this stage to avoid Labour Commissioner action. (2) If unresolved, file with District Labour Commissioner — cheaper and faster than court. (3) For salaried employees, CPC Order 37 summary suit in Civil Court is the most conclusive."),
            ("Can I send a legal notice for unpaid salary to a startup that says it has no money?", "Yes. The existence of funds is irrelevant to the legal obligation to pay salary. A company's financial distress does not extinguish employee wage rights. The Payment of Wages Act 1936 creates personal liability on the company's directors and managers for wage violations."),
            ("My employer deducted salary as 'notice period penalty'. Is this legal?", "Only valid notice period deductions are legal, and only if clearly stated in the employment contract. Deductions exceeding the notice period's salary equivalent — or deductions without a contract clause — are unlawful under the Payment of Wages Act 1936 §7. You can demand refund."),
            ("Can I also claim for mental harassment caused by salary non-payment?", "Yes. Under CPA 2019 and civil law, prolonged non-payment causing financial distress and mental agony can attract compensation beyond the missed salary. Consumer Commissions and civil courts have awarded such amounts."),
            ("What if my employer asks me to quit before paying?", "This is a pressure tactic. Do not resign before receiving all dues. If you resign before receiving full and final settlement, your legal position weakens. While waiting, send a legal notice specifying the amount owed and document all communications."),
        ],
    },

    # ── PROPERTY DISPUTE ──────────────────────────────────────────────────────
    {
        "slug": "legal-notice-property-dispute",
        "title": "Legal Notice for Property Dispute India — Encroachment, Illegal Possession",
        "meta_desc": "Send a legal notice for property dispute in India — encroachment, illegal possession, co-owner dispute. CPC + TPA 1882 + Specific Relief Act. Lawly at ₹199.",
        "h1": "Legal Notice for Property Dispute India — Encroachment & Illegal Possession",
        "notice_type": "Property Dispute",
        "law_basis": "Transfer of Property Act 1882 + Specific Relief Act 1963 + CPC 1908",
        "quick_answer": "Property disputes in India — whether encroachment, illegal possession, or co-owner conflict — require a formal legal notice before approaching court. The notice triggers a 30-day opportunity for resolution. For urgent threats (imminent demolition, forced eviction), you can also apply for an interim injunction in Civil Court simultaneously. Key laws: Transfer of Property Act 1882, Specific Relief Act 1963, and CPC 1908 Order 39.",
        "limitation": "Civil suits for property recovery: 12 years from date of dispossession (Limitation Act 1963 Art. 65). Suits for injunction: 3 years from cause of action. Act quickly — adverse possession (12 years of uncontested possession) can bar your claim.",
        "when_to_send": [
            "Someone has illegally occupied or encroached on your land or property",
            "Co-owner is claiming more than their rightful share or preventing your access",
            "Builder/developer has wrongfully transferred your property or delayed possession",
            "Neighbour has built construction crossing the plot boundary (encroachment)",
            "Joint family property dispute — one member claiming exclusive possession",
            "Dispute over property inherited through will or intestate succession",
            "Tenant refusing to vacate after tenancy agreement expiry (also see: tenant-landlord notice)",
            "Fraudulent sale or registration of your property by an impersonator",
        ],
        "governing_laws": [
            ("Transfer of Property Act 1882", "§5, §7, §54, §58, §105", "Defines valid transfer, sale, mortgage, lease of property; basis for ownership claims"),
            ("Specific Relief Act 1963", "§6 + §38", "§6: summary suit for recovery of possession within 6 months; §38: perpetual injunction against encroachment"),
            ("Indian Contract Act 1872", "§10 + §17", "Fraud in property transactions; voidable contracts"),
            ("Limitation Act 1963", "Art. 65 + Art. 58", "12 years for recovery of immovable property; 3 years for injunction"),
            ("Code of Civil Procedure 1908", "Order 39 (Interim Injunction)", "Temporary injunction to prevent dispossession or construction during litigation"),
            ("Registration Act 1908", "§17", "Compulsory registration of property sale deeds; unregistered sale void against third parties"),
        ],
        "checklist": [
            "Your full name, address, and basis of ownership (sale deed, inheritance, gift deed) with registration details",
            "Detailed description of the property: survey number, plot number, area, Khasra number (for agricultural land)",
            "Nature of dispute: encroachment, illegal possession, fraudulent transfer — specific facts and dates",
            "Name and address of the opposite party (encroacher/dispossessor)",
            "Cite specific legal provisions: Specific Relief Act §6 for summary possession; TPA §106 for tenancy",
            "Demand requiring the party to vacate / cease encroachment / restore access",
            "14–30 day deadline before filing in Civil Court / Revenue Court",
            "Warning of injunction application under CPC Order 39 if no compliance",
        ],
        "steps": [
            ("Gather Property Documents", "Compile: registered title deed, latest property tax receipts, mutation/khata certificate, survey maps, and any evidence of your possession (utility bills, photographs). These are your primary evidence of ownership."),
            ("Send Legal Notice via Lawly", "A formal notice sent via registered post to the encroacher/opponent. Cite TPA, Specific Relief Act §6 (if dispossessed in the last 6 months — fast track), and CPC Order 39 for injunction warning. ₹199 via Lawly."),
            ("Apply for Interim Injunction if Urgent", "If the opposite party is making construction, demolishing structures, or about to sell the property, simultaneously file an ex-parte injunction application in Civil Court under CPC Order 39 Rule 1 & 2. Courts can grant same-day orders in urgent cases."),
            ("File Title Suit in Civil Court", "If the notice doesn't resolve the dispute, file a title suit in the Civil Court of the jurisdiction where the property is located. Attach: property documents, legal notice + postal receipt, and photographs of encroachment."),
            ("Revenue Court for Agriculture Land", "Agricultural land disputes in many states go to Revenue Courts (Tehsildar / Additional District Magistrate) rather than Civil Courts. Consult the Jamabandi (land record) before filing."),
        ],
        "faqs": [
            ("What is the fastest way to recover my property from an encroacher in India?", "If you were dispossessed in the last 6 months: file under Specific Relief Act §6 for a summary possession suit — this is the fastest property recovery mechanism (no need to prove title, just prove recent possession). For older disputes: file a regular title suit with an interim injunction under CPC Order 39."),
            ("Can I send a property dispute legal notice without a lawyer?", "Yes. A legal notice can be sent without a lawyer, but it must cite specific statutes to be taken seriously. Lawly's AI generates a notice citing TPA §5, Specific Relief Act §6 or §38, and CPC Order 39 as appropriate. At ₹199, it's cost-effective before deciding to hire a lawyer."),
            ("My neighbour is building on my plot boundary. What should I do?", "Send an immediate legal notice demanding halt to construction and removal of encroachment. Simultaneously apply for a temporary injunction in Civil Court under CPC Order 39 Rule 1 & 2 to stop the construction. Courts can grant an ex-parte (one-sided, immediate) injunction if you prove irreparable harm."),
            ("What is adverse possession and how does it affect my property claim?", "Adverse possession (Limitation Act Art. 65): if someone openly, continuously, and exclusively possesses your property for 12 years without your objection, they can claim title through court. This means you MUST act when you discover encroachment — delays can extinguish your claim."),
            ("Can I file a criminal FIR for property encroachment?", "Yes, in addition to civil proceedings. Criminal trespass (BNS §329) and mischief (BNS §324) can apply. However, police often refuse to register FIRs in civil property disputes. A civil injunction + legal notice is usually the more effective path. For fraud (forged documents), FIR is definitely appropriate."),
        ],
    },

    # ── DEFAMATION ────────────────────────────────────────────────────────────
    {
        "slug": "legal-notice-defamation",
        "title": "Legal Notice for Defamation India — Online & Offline Defamation Notice",
        "meta_desc": "Send a legal notice for defamation in India — social media defamation, false reviews, reputation damage. BNS §356 + civil law. Lawly at ₹199. 5 min.",
        "h1": "Legal Notice for Defamation India — Online & Offline Defamation",
        "notice_type": "Defamation",
        "law_basis": "Bharatiya Nyaya Sanhita 2023 §356 (criminal) + Civil Law (civil defamation)",
        "quick_answer": "Defamation in India can be pursued as both a criminal offence (BNS §356 — up to 2 years imprisonment) and a civil tort (damages for reputation loss). A defamation legal notice serves two purposes: (1) demands retraction and apology, (2) creates a record before filing criminal complaint or civil suit. Online defamation (social media posts, fake reviews, WhatsApp forwards) is also covered under IT Act §67 and BNS §356.",
        "limitation": "Criminal defamation complaint: within 3 years of the defamatory statement (CrPC §468). Civil suit for damages: within 1 year of publication (Limitation Act Art. 75). Act quickly — online content can be deleted, making evidence collection harder.",
        "when_to_send": [
            "Someone posted false and damaging statements about you on social media (Facebook, Instagram, Twitter/X, YouTube)",
            "Fake negative reviews on Google, Zomato, Amazon, or other review platforms causing business harm",
            "WhatsApp forward or group message circulating false, defamatory content",
            "Newspaper, news website, or podcast published factually incorrect damaging story",
            "Ex-employer or business partner made defamatory statements to clients / industry contacts",
            "Online harassment campaign with fabricated content to damage professional reputation",
            "Competitor's false advertisement making direct or implied defamatory claims about your business",
        ],
        "governing_laws": [
            ("Bharatiya Nyaya Sanhita 2023", "§356 (Criminal Defamation)", "Making/publishing false statement harming reputation: up to 2 years imprisonment + fine"),
            ("Civil Law (Law of Torts)", "Defamation Tort", "Civil remedy: damages for reputation loss, loss of business, mental anguish"),
            ("IT Act 2000", "§67 + §67A", "Publishing obscene/sexually explicit defamatory content online — up to 5 years imprisonment"),
            ("IT Act 2000", "§66E + §66C", "Violation of privacy / identity theft in context of digital defamation"),
            ("Code of Criminal Procedure 1973", "§199", "Defamation cases cognizable only on Magistrate's complaint; police cannot file FIR directly"),
            ("Press Council of India Act 1978", "§14", "Complaints against newspapers/publications for irresponsible reporting"),
        ],
        "checklist": [
            "Screenshot/copy of the exact defamatory content with URL, date, and time clearly visible",
            "Your name and how the statement identifies you (even if not named directly)",
            "Explanation of why the statement is false — what the truth actually is",
            "Evidence of harm: lost business, cancelled contracts, social/professional consequences",
            "Explicit demand: take down the content + issue public retraction + written apology",
            "Demand for compensation specifying the amount claimed",
            "15–30 day deadline before filing criminal complaint (Magistrate) or civil suit",
        ],
        "steps": [
            ("Preserve Evidence Immediately", "Screenshot/web archive the defamatory content (use archive.org or screenshot with URL visible). Download posts, comments, videos. Preserve all metadata. Defamatory content is often deleted quickly after receiving a notice."),
            ("Send Legal Notice via Lawly", "Notice must go to: (1) the individual who posted the content, (2) the platform (if they refuse to take down after 36 hours of notice per IT Act). Cite BNS §356 for criminal exposure + civil defamation. Demand: content removal + apology + compensation."),
            ("File for Content Takedown via Platform", "Simultaneously use the platform's reporting mechanism (Twitter/X, Facebook, Google) to report the defamatory content. If the platform is an intermediary under IT Act §79, they must act on takedown notice within 36 hours for sexual content, 72 hours for other content."),
            ("Send Legal Takedown to Platform CEO (Section 79 IT Act)", "If the platform ignores your takedown request, send a formal notice to the platform's Grievance Officer. All major platforms in India are required under IT Rules 2021 to appoint a Grievance Officer and respond within 15 days."),
            ("File Criminal Complaint with Magistrate (BNS §356)", "For serious defamation (business destruction, sexual defamation), file a private criminal complaint directly with a Judicial Magistrate under CrPC §199. Police cannot file FIR for defamation — you must approach the Magistrate. The legal notice serves as a prerequisite in many Magistrate's views."),
        ],
        "faqs": [
            ("Is defamation a criminal offence in India?", "Yes. Under Bharatiya Nyaya Sanhita 2023 §356 (previously IPC §499–500), criminal defamation is punishable with imprisonment up to 2 years, a fine, or both. However, it is a non-cognizable, bailable offence — police cannot arrest without a Magistrate's order. You must file a private complaint with a Judicial Magistrate."),
            ("Can I sue someone for writing a fake negative Google review?", "Yes. Fake reviews that are false and damage your business reputation are defamation. You can: (1) Request Google's Grievance Officer to take down the review (under IT Rules 2021); (2) Send a legal notice to the reviewer (if their identity is known); (3) File a civil defamation suit for damages."),
            ("What is 'online defamation' and how is it different from offline defamation?", "Online defamation (social media, review sites, messaging apps) is treated at least as seriously as offline defamation because it has a wider reach and is easier to prove (can be recorded/archived). BNS §356 applies to both. Additionally, IT Act §67 can apply if the content is obscene."),
            ("Can a company (not just a person) file a defamation case?", "Yes. A company's reputation is a legal interest worth protecting. Companies can file civil defamation suits for false statements damaging their business reputation and brand. Criminal defamation (BNS §356) is only for individuals, not companies."),
            ("What are the defences to a defamation claim?", "Truth (Justification): if the statement is true, it is a complete defence in civil cases. Fair Comment: opinion on a matter of public interest. Privilege: statements in court, Parliament, or good-faith reports to authorities are privileged. Good-faith publication for public benefit is also a defence."),
        ],
    },

    # ── MEDICAL NEGLIGENCE (LEGAL NOTICE) ─────────────────────────────────────
    {
        "slug": "legal-notice-medical-negligence",
        "title": "Legal Notice for Medical Negligence India — Hospital & Doctor Negligence",
        "meta_desc": "Send a legal notice for medical negligence in India — hospital, doctor, or surgical error. CPA 2019 + NMC Act. Lawly at ₹199. 5 min. 87% resolution before court.",
        "h1": "Legal Notice for Medical Negligence India — Hospital & Doctor",
        "notice_type": "Medical Negligence",
        "law_basis": "CPA 2019 + NMC Act 2020 + IMA v. VP Shantha (1995 SC)",
        "quick_answer": "Medical negligence legal notices are sent to hospitals and doctors to formally demand explanation and compensation for sub-standard care. The Supreme Court's 1995 ruling (IMA v. V.P. Shantha) confirmed that medical services fall under consumer protection law. Before filing in Consumer Commission, a legal notice is advisable — it creates a record and often triggers settlement negotiations.",
        "limitation": "Consumer complaint for medical negligence: 2 years from date of negligence or date of discovery (whichever is later, per 'discovery rule'). Civil suit for medical negligence: 3 years. File your legal notice IMMEDIATELY — evidence (medical records) must be preserved before hospitals delete/modify electronic records.",
        "when_to_send": [
            "Surgical error — wrong site surgery, retained surgical instrument, post-operative infection from negligence",
            "Misdiagnosis resulted in wrong treatment and worsening of condition",
            "Death of patient due to suspected medical negligence; family denied death summary",
            "Hospital performed surgery without obtaining informed consent",
            "Overcharging — billed for procedures not performed or medicines not administered",
            "Delay in diagnosis of critical condition (cancer, cardiac arrest, stroke) causing preventable harm",
            "Hospital denied or delayed emergency treatment citing payment issues",
            "Pharmacy dispensed wrong medication causing adverse effect",
        ],
        "governing_laws": [
            ("Consumer Protection Act 2019", "§2(11) + §35 + §39", "Medical services = services; negligence = deficiency; Consumer Commission has jurisdiction"),
            ("NMC Act 2020", "§30 + §57", "National Medical Commission; disciplinary action against doctor's licence"),
            ("IMA v. VP Shantha 1995", "SC 5-Judge Bench", "Landmark: medical services for payment fall under Consumer Protection Act"),
            ("Indian Penal Code / BNS 2023", "§304A BNS / §106 BNS", "Criminal negligence causing death through negligent act — up to 5 years imprisonment"),
            ("CGHS / NABH Regulations", "Ministry of H&FW Orders", "Government hospital rate lists; NABH standards for accredited hospitals"),
            ("Medical Termination of Pregnancy Act 1971", "§4 + §5", "Botched MTP = medical negligence; liability on registered medical practitioner"),
        ],
        "checklist": [
            "Patient's name, age, address and hospital patient ID / case number",
            "Hospital name, address, and name of treating doctor(s)",
            "Detailed timeline: admission date, procedure/treatment, when negligence occurred",
            "Specific negligent act or omission with evidence (medical records, test reports)",
            "Expert medical opinion (if available) establishing the breach of standard of care",
            "Harm caused: physical injury, death, additional cost of corrective treatment",
            "Compensation demanded: corrective treatment cost + loss of income + mental anguish + punitive damages",
            "Demand for copies of: case history, operation notes, nursing notes, ICU charts, pharmacy records",
            "30-day deadline before filing Consumer Commission complaint + NMC complaint",
        ],
        "steps": [
            ("Request All Medical Records Immediately", "Send a written request (email + registered letter) to the hospital's Medical Records Department for all records: case history, nursing notes, OT notes, test reports, drug charts, discharge summary. Hospitals must provide within 72 hours. If denied, this itself is a ground for complaint."),
            ("Get an Independent Medical Expert Opinion", "Take records to an independent specialist in the same field. Their written report establishing the standard of care and how it was breached is the most critical evidence. Without this, winning a medical negligence case is extremely difficult."),
            ("Send Legal Notice via Lawly to Hospital + Doctor", "Notice must go to: (1) Hospital's CEO/Medical Director at registered address, (2) Treating doctor's personal address. Cite CPA 2019 §2(11), IMA v. VP Shantha, and Indian Medical Degree Act. Demand: explanation + compensation + records. ₹199 via Lawly."),
            ("File NMC / State Medical Council Complaint", "Simultaneously file a complaint with the State Medical Council of the doctor's state requesting disciplinary action. Appeal lies with NMC. This creates parallel pressure and can result in suspension of the doctor's licence."),
            ("File Consumer Commission Case", "File in DCDRC (up to ₹1 crore) with: expert opinion, medical records, legal notice + postal receipt, hospital bills, and evidence of harm. The Commission will conduct its own inquiry and may appoint an independent medical board."),
        ],
        "faqs": [
            ("Is medical negligence covered by consumer law in India?", "Yes. The Supreme Court's landmark ruling in Indian Medical Association v. V.P. Shantha (1995) held that medical services, when availed for payment (private hospitals), are 'services' under the Consumer Protection Act. Patients who pay for treatment are 'consumers'. Government hospitals where treatment is free are generally outside CPA but can be argued in some cases."),
            ("How do I prove medical negligence in India?", "You need to prove: (1) The doctor owed you a duty of care, (2) They breached the standard of care expected of a reasonably skilled doctor, (3) This breach caused harm. The key is an independent medical expert's written report. Without expert evidence, consumer commissions typically will not find negligence."),
            ("Can I file both a criminal case and a consumer complaint for medical negligence?", "Yes. Criminal negligence causing death: BNS §106 (formerly IPC §304A) — up to 5 years imprisonment. Consumer complaint: for financial compensation. NMC/State Medical Council: for licence revocation. These are parallel proceedings and each can proceed independently."),
            ("What compensation can I get for medical negligence?", "Courts and Consumer Commissions have awarded: corrective treatment costs, loss of income during recovery, permanent disability compensation, pain and suffering, mental agony, punitive damages (in grossly negligent cases). NCDRC has awarded amounts ranging from ₹5 lakh to ₹2+ crore in serious cases."),
            ("My relative died due to hospital negligence. Who can file the complaint?", "Legal heirs (spouse, children, parents) of the deceased can file as 'complainant' in the Consumer Commission. The estate of the deceased is entitled to compensation. Add all legal heirs as co-complainants."),
        ],
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# GENERATE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    STATIC.mkdir(exist_ok=True)

    for cfg in SECTOR_PAGES:
        html = sector_html(cfg)
        path = STATIC / f"{cfg['slug']}.html"
        path.write_text(html, encoding="utf-8")
        print(f"✓ {cfg['slug']}.html  ({len(html):,} chars)")

    for cfg in NOTICE_PAGES:
        html = notice_html(cfg)
        path = STATIC / f"{cfg['slug']}.html"
        path.write_text(html, encoding="utf-8")
        print(f"✓ {cfg['slug']}.html  ({len(html):,} chars)")

    print(f"\nTotal: {len(SECTOR_PAGES) + len(NOTICE_PAGES)} pages generated.")
