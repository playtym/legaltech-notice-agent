import re

with open("static/index.html", "r") as f:
    text = f.read()

target_start = '<form id="form-company" onsubmit="return false;">'
target_end = '<!-- Agent lookup result -->'

pattern = re.compile(rf'{re.escape(target_start)}(.*?){re.escape(target_end)}', re.DOTALL)

replacement = """<form id="form-company" onsubmit="return false;">
            <div class="form-group">
                <label>Select Company Category</label>
                <div class="quick-chips" style="margin-top: 8px; margin-bottom: 16px; display: flex; gap: 8px; flex-wrap: wrap;" id="category-selection-chips">
                    <span class="chip cat-chip" onclick="App.setCategory('ecommerce', this)" style="cursor:pointer; background:#f3f4f6; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #e5e7eb; transition: 0.2s;">🛒 E-Commerce / Marketplaces</span>
                    <span class="chip cat-chip" onclick="App.setCategory('d2c', this)" style="cursor:pointer; background:#f3f4f6; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #e5e7eb; transition: 0.2s;">🛍️ D2C Brands</span>
                    <span class="chip cat-chip" onclick="App.setCategory('quick_commerce', this)" style="cursor:pointer; background:#f3f4f6; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #e5e7eb; transition: 0.2s;">🛵 Quick Commerce & Food</span>
                    <span class="chip cat-chip" onclick="App.setCategory('fintech', this)" style="cursor:pointer; background:#f3f4f6; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #e5e7eb; transition: 0.2s;">🏦 Banks & Fintech</span>
                    <span class="chip cat-chip" onclick="App.setCategory('travel', this)" style="cursor:pointer; background:#f3f4f6; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #e5e7eb; transition: 0.2s;">✈️ Airlines & Travel</span>
                    <span class="chip cat-chip" onclick="App.setCategory('edtech', this)" style="cursor:pointer; background:#f3f4f6; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #e5e7eb; transition: 0.2s;">🎓 Ed-Tech</span>
                    <span class="chip cat-chip" onclick="App.setCategory('mobility', this)" style="cursor:pointer; background:#f3f4f6; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #e5e7eb; transition: 0.2s;">🚕 EV & Mobility</span>
                </div>
            </div>
            <div class="form-group" style="margin-top: 24px;">
                <label for="company-name">Company Name <span class="req">*</span></label>
                <input type="text" id="company-name" placeholder="e.g. Amazon, boAt, Swiggy, HDFC" required maxlength="200">
            </div>
            <div class="form-group">
                <label for="company-website">Website <span class="opt">(optional)</span></label>
                <input type="url" id="company-website" placeholder="https://www.example.com">
                <small class="hint">Add the website so our AI agent can look up the legal entity, CIN, and grievance contacts.</small>
            </div>

            <!-- Agent lookup result -->"""

new_text = pattern.sub(replacement, text)

with open("static/index.html", "w") as f:
    f.write(new_text)

print("Updated index.html form successfully.")
