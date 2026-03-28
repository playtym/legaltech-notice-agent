from create_page import generate_page
import os

companies = [
    ("Vistara", "Airlines", "flight delay and baggage"),
    ("SpiceJet", "Airlines", "flight cancellation and refund"),
    ("Akasa Air", "Airlines", "flight issues and refund"),
    ("Vodafone Idea", "Telecom", "network drop and billing"),
    ("BSNL", "Telecom", "broadband and incorrect billing"),
    ("ACT Fibernet", "ISP", "broadband disconnection and refund"),
    ("Hathway", "ISP", "internet downtime and billing"),
    ("Swiggy", "Food Delivery", "food delivery and refund"),
    ("Zepto", "Quick Commerce", "delayed delivery and missing items"),
    ("Dunzo", "Quick Commerce", "delayed delivery and missing groceries"),
    ("Tata CLiQ", "E-commerce", "order cancellation and refund"),
    ("Ajio", "E-commerce", "defective product and refund"),
    ("Myntra", "E-commerce", "broken product and return"),
    ("Nykaa", "E-commerce", "fake product and return rejection"),
    ("Croma", "Electronics", "defective appliance and warranty"),
    ("Reliance Digital", "Electronics", "defective item and return"),
    ("HDFC Bank", "Banking", "credit card and hidden charges"),
    ("ICICI Bank", "Banking", "unauthorized transaction and card block"),
    ("SBI", "Banking", "failed transaction and loan mis-selling"),
    ("Axis Bank", "Banking", "hidden fee and credit card issues"),
    ("Google Pay", "Payment App", "failed UPI transaction and refund"),
    ("Cred", "Payment App", "payment issue and hidden charge"),
    ("Byjus", "EdTech", "course cancellation and fee refund"),
    ("Unacademy", "EdTech", "subscription cancellation"),
    ("Vedantu", "EdTech", "course fee refund and false promises"),
    ("UpGrad", "EdTech", "course refund and false placements"),
    ("NoBroker", "Real Estate", "deposit refund and fake leads"),
    ("Housing.com", "Real Estate", "paid subscription issue"),
    ("Magicbricks", "Real Estate", "subscription refund and dead leads"),
    ("Samsung", "Electronics", "defective mobile and warranty service denial"),
    ("LG", "Electronics", "defective appliance and AC repair"),
    ("Whirlpool", "Electronics", "defective fridge and warranty limit"),
    ("Sony", "Electronics", "defective TV and warranty service"),
    ("Apple", "Electronics", "defective device and warranty denial"),
    ("Agoda", "Travel", "hotel booking cancellation and refund"),
    ("Yatra", "Travel", "flight refund and booking issue"),
    ("OYO Rooms", "Hospitality", "booking denial at check-in and refund"),
    ("Airbnb", "Hospitality", "host cancellation and refund"),
    ("Uber", "Ride Hailing", "driver cancellation and overcharging"),
    ("Rapido", "Ride Hailing", "accident insurance and overcharging"),
    ("RedBus", "Travel", "bus cancellation and refund"),
    ("Cult.fit", "Fitness", "gym membership cancellation and refund"),
    ("Golds Gym", "Fitness", "membership refund"),
    ("India Post", "Logistics", "lost parcel and delayed delivery"),
    ("IRCTC", "Railways", "ticket cancellation and TDR refund"),
    ("BookMyShow", "Entertainment", "ticket cancellation and missing refund"),
    ("Zudio", "Retail", "defective clothes and return refusal"),
    ("Lenskart", "E-commerce", "wrong product and refund denial"),
    ("Urban Company", "Home Services", "poor service and property damage"),
    ("Delhivery", "Logistics", "lost package and delayed tracking")
]

for brand, category, issue_type in companies:
    slug = f"{brand.lower().replace(' ', '-').replace('.', '')}-complaints"
    title = f"File a Complaint Against {brand} | Lawly"
    desc = f"Unresolved issue with {brand}? Learn how to escalate your {issue_type} complaints and send a legal notice online."
    h1 = f"How to File a {brand} Complaint & Send a Legal Notice"
    
    content = f"""<p>Are you facing <strong>{issue_type}</strong> issues with {brand}? You are not alone. Thousands of consumers struggle with poor customer service every day.</p>
<p>If reaching out to {brand} customer care hasn't solved your problem, it's time to take legal action. Under the Consumer Protection Act, you have the right to claim a refund, replacement, and compensation for mental harassment.</p>
<h3 class="text-xl font-bold mt-6 mb-3 text-gray-900">Steps to escalate your complaint:</h3>
<ol class="list-decimal pl-6 space-y-2 text-gray-700">
    <li>Contact the <strong>{brand} Grievance Officer</strong> via email or registered post.</li>
    <li>Register your grievance on the INGRAM (National Consumer Helpline) portal.</li>
    <li><strong>Send a formal pre-litigation legal notice</strong> to {brand}'s registered office.</li>
</ol>
<p class="mt-6">Sending a legally sound notice is often the fastest way to force companies like {brand} to take your complaint seriously and resolve the matter before it reaches the consumer court.</p>"""

    generate_page(slug, title, desc, h1, content)

print("\n🎉 Generated 50 new landing pages successfully!")
