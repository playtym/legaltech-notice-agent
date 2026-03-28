from create_page import generate_page
import os

cities = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Ahmedabad", 
    "Chennai", "Kolkata", "Surat", "Pune", "Jaipur", 
    "Lucknow", "Kanpur", "Nagpur", "Indore", "Thane", 
    "Bhopal", "Visakhapatnam", "Pimpri-Chinchwad", "Patna", "Vadodara",
    "Ghaziabad", "Ludhiana", "Agra", "Nashik", "Faridabad",
    "Meerut", "Rajkot", "Kalyan-Dombivli", "Vasai-Virar", "Varanasi",
    "Srinagar", "Aurangabad", "Dhanbad", "Amritsar", "Navi Mumbai",
    "Allahabad", "Ranchi", "Howrah", "Coimbatore", "Jabalpur",
    "Gwalior", "Vijayawada", "Jodhpur", "Madurai", "Raipur",
    "Kota", "Guwahati", "Chandigarh", "Solapur", "Hubli-Dharwad"
]

for city in cities:
    slug = f"consumer-court-{city.lower().replace(' ', '-')}"
    title = f"File a Consumer Court Complaint in {city} Online | Lawly"
    desc = f"Looking for consumer court lawyers or need to send a legal notice in {city}? Send a pre-litigation legal notice online instantly without leaving your home."
    h1 = f"How to File a Consumer Complaint & Legal Notice in {city}"
    
    content = f"""<p>If you are facing an unresolved issue with a builder, e-commerce company, telecom operator, or bank in <strong>{city}</strong>, you don't necessarily need to visit the District Consumer Disputes Redressal Forum immediately.</p>
<p>Often, the fastest way to resolve a consumer dispute is by sending a <strong>formal legal notice</strong> under the Consumer Protection Act. Thousands of consumers in {city} use pre-litigation notices to get their refunds or compensation long before a formal court case begins.</p>
<h3 class="text-xl font-bold mt-6 mb-3 text-gray-900">Why send a legal notice first?</h3>
<ul class="list-disc pl-6 space-y-2 text-gray-700">
    <li><strong>It's legally required:</strong> Courts in {city} expect you to give the company a formal 15-30 day warning before filing a case.</li>
    <li><strong>It saves time & money:</strong> Hiring a local lawyer in {city} can be expensive. Companies usually settle once they receive a professional notice.</li>
    <li><strong>It creates a paper trail:</strong> A well-drafted notice acts as strong evidence if you eventually file a complaint with the e-Daakhil portal or the district forum.</li>
</ul>
<p class="mt-6">Skip the hassle of visiting a law firm. You can now draft and send a watertight legal notice from your laptop in minutes.</p>"""

    faqs = [
        (f"Where is the consumer court located in {city}?", 
         f"Depending on your claim amount, you may file in the District Commission (up to ₹50 Lakhs), State Commission (₹50 Lakhs to ₹2 Crores), or National Commission. Most complaints begin at the {city} District Consumer Disputes Redressal Forum."),
        (f"Can I send a legal notice online from {city} without a lawyer?", 
         "Yes! The law does not mandate hiring a lawyer to send a legal notice. Using Lawly, you can instantly generate a legally formatted notice and send it via Speed Post or Email."),
        (f"How much does it cost to file a consumer case in {city}?", 
         "Filing fees are very nominal, often zero for claims up to ₹5 Lakhs. However, sending a legal notice first is the cheapest way to resolve the dispute, as most brands settle out of court to avoid litigation.")
    ]

    generate_page(slug, title, desc, h1, content, faqs=faqs)

print("\\n🎉 Generated 50 city-specific SEO landing pages with FAQ schema!")