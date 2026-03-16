import re

with open("static/app.js", "r") as f:
    text = f.read()

state_target = "complainant: null,"
if "category: null" not in text:
    text = text.replace(state_target, "category: null,\n        " + state_target)

set_cat_func = """
    function setCategory(cat, element) {
        state.category = cat;
        // reset chips
        document.querySelectorAll('.cat-chip').forEach(el => {
            el.style.background = '#f3f4f6';
            el.style.borderColor = '#e5e7eb';
            el.style.color = '#000';
            el.style.fontWeight = 'normal';
        });
        if (element) {
            element.style.background = '#e0e7ff';
            element.style.borderColor = '#818cf8';
            element.style.color = '#3730a3';
            element.style.fontWeight = 'bold';
        }
        updateIssueChips();
    }
"""

if "function setCategory" not in text:
    text = text.replace("function setCompany", set_cat_func + "\n    function setCompany")

# Now rewrite updateIssueChips
new_update_issues = """function updateIssueChips() {
        const container = document.getElementById("issue-chips-container");
        if (!container) return;
        
        let chipsHTML = "";
        let cat = state.category;
        
        if (cat === "ecommerce") {
            chipsHTML = `
                <span class="chip" onclick="App.setIssue('I ordered a product but received a defective/different item. The company is denying my return/refund request.')" style="cursor:pointer; background:#e0e7ff; color: #3730a3; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #c7d2fe; transition: 0.2s;">📦 Defective Product</span>
                <span class="chip" onclick="App.setIssue('I have returned the product via the app but the refund has not been credited to my account despite the passing of the standard timeframe.')" style="cursor:pointer; background:#e0f2fe; color: #312e81; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #bae6fd; transition: 0.2s;">💸 Refund Delayed</span>
                <span class="chip" onclick="App.setIssue('My prepaid order was marked as delivered but I never received the package. Customer support is unhelpful.')" style="cursor:pointer; background:#fce7f3; color: #075985; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #fbcfe8; transition: 0.2s;">🚚 Missing Package</span>
            `;
        } else if (cat === "d2c") {
            chipsHTML = `
                <span class="chip" onclick="App.setIssue('I was charged for a prepaid order but the D2C brand never shipped the product and has stopped responding to my emails.')" style="cursor:pointer; background:#fce7f3; color: #075985; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #fbcfe8; transition: 0.2s;">🚫 Paid but Not Shipped</span>
                <span class="chip" onclick="App.setIssue('I ordered directly from the brand\\'s official website but received a counterfeit/fake product. They are ignoring my refund requests.')" style="cursor:pointer; background:#e0e7ff; color: #3730a3; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #c7d2fe; transition: 0.2s;">🛍️ Fake/Counterfeit</span>
                <span class="chip" onclick="App.setIssue('The brand advertised a false discount/scam. They cancelled my order after payment and refused to refund the amount deducted.')" style="cursor:pointer; background:#e0f2fe; color: #312e81; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #bae6fd; transition: 0.2s;">💸 Sale Fraud/Scam</span>
            `;
        } else if (cat === "quick_commerce") {
            chipsHTML = `
                <span class="chip" onclick="App.setIssue('The food delivered was spoiled, unhygienic, and unfit for consumption. App support refused to refund my money.')" style="cursor:pointer; background:#e0e7ff; color: #3730a3; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #c7d2fe; transition: 0.2s;">🍲 Spoiled Food</span>
                <span class="chip" onclick="App.setIssue('Order was extremely delayed and arrived cold/spilled. Delivery partner and customer support were unresponsive.')" style="cursor:pointer; background:#e0f2fe; color: #312e81; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #bae6fd; transition: 0.2s;">⏱️ Delayed/Spilled</span>
                <span class="chip" onclick="App.setIssue('Several items were missing from my grocery/food order. Customer support closed the ticket without providing a refund.')" style="cursor:pointer; background:#fce7f3; color: #075985; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #fbcfe8; transition: 0.2s;">❌ Missing Items</span>
            `;
        } else if (cat === "mobility") {
            chipsHTML = `
                <span class="chip" onclick="App.setIssue('My EV scooter has severe battery degradation and manufacturing defects within the warranty period. Service centre is non-responsive.')" style="cursor:pointer; background:#e0e7ff; color: #3730a3; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #c7d2fe; transition: 0.2s;">🔋 Battery/Defect Issue</span>
                <span class="chip" onclick="App.setIssue('The vehicle suffered a sudden software failure causing a breakdown. Free service check/repair was unjustly denied.')" style="cursor:pointer; background:#e0f2fe; color: #312e81; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #bae6fd; transition: 0.2s;">💻 Software Failure</span>
                <span class="chip" onclick="App.setIssue('I was charged an unfair cancellation fee by the ride hailing app despite the driver refusing to turn up at the location.')" style="cursor:pointer; background:#fce7f3; color: #075985; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #fbcfe8; transition: 0.2s;">🚕 Unfair Ride Fee</span>
            `;
        } else if (cat === "fintech") {
            chipsHTML = `
                <span class="chip" onclick="App.setIssue('A UPI payment failed and the amount was deducted from my bank account, but it has not been refunded within the RBI mandated turnaround time.')" style="cursor:pointer; background:#fce7f3; color: #075985; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #fbcfe8; transition: 0.2s;">💳 UPI Failure</span>
                <span class="chip" onclick="App.setIssue('Unauthorised and fraudulent transactions were made from my credit card without my consent. Bank has not reversed the charges.')" style="cursor:pointer; background:#e0e7ff; color: #3730a3; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #c7d2fe; transition: 0.2s;">🚨 Fraudulent Charges</span>
                <span class="chip" onclick="App.setIssue('Hidden charges and fees were deducted from my savings account without prior transparent notification.')" style="cursor:pointer; background:#e0f2fe; color: #312e81; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #bae6fd; transition: 0.2s;">🏦 Hidden Fees</span>
            `;
        } else if (cat === "travel") {
            chipsHTML = `
                <span class="chip" onclick="App.setIssue('My flight was cancelled/delayed without prior notice. The airline has not provided the mandatory compensation as per DGCA regulations.')" style="cursor:pointer; background:#e0f2fe; color: #312e81; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #bae6fd; transition: 0.2s;">✈️ Flight Cancelled/Delayed</span>
                <span class="chip" onclick="App.setIssue('My check-in baggage was lost/damaged by the airline. They are refusing to provide standard compensation for the loss.')" style="cursor:pointer; background:#e0e7ff; color: #3730a3; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #c7d2fe; transition: 0.2s;">🧳 Baggage Lost/Damaged</span>
                <span class="chip" onclick="App.setIssue('I cancelled my tickets well within the eligible period, but the platform is charging illegal zero-refund cancellation fees.')" style="cursor:pointer; background:#fce7f3; color: #075985; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #fbcfe8; transition: 0.2s;">❌ Unfair Cancellation Fee</span>
            `;
        } else if (cat === "edtech") {
            chipsHTML = `
                <span class="chip" onclick="App.setIssue('I purchased an online course but it did not match the advertised curriculum. The ed-tech company is denying my rightful refund request.')" style="cursor:pointer; background:#f3e8ff; color: #831843; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #fbcfe8; transition: 0.2s;">🎓 Ed-Tech Refund</span>
                <span class="chip" onclick="App.setIssue('A subscription was force-sold to me with false promises of placement guarantees. They refuse to cancel the emi/loan auto-debit.')" style="cursor:pointer; background:#e0e7ff; color: #3730a3; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #c7d2fe; transition: 0.2s;">🛑 False Promises/EMI Setup</span>
            `;
        } else {
            // Default generic options if no category selected
            chipsHTML = `
                <span class="chip" onclick="App.setIssue('I ordered a product but it was delivered defective. Despite multiple complaints, the company has refused to provide a refund or replacement.')" style="cursor:pointer; background:#e0e7ff; color: #3730a3; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #c7d2fe; transition: 0.2s;">📦 Defective Product</span>
                <span class="chip" onclick="App.setIssue('My flight was cancelled without prior notice. The airline has not provided the mandatory compensation as per DGCA regulations.')" style="cursor:pointer; background:#e0f2fe; color: #312e81; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #bae6fd; transition: 0.2s;">✈️ Flight Cancelled</span>
                <span class="chip" onclick="App.setIssue('A UPI payment failed and the amount was deducted from my bank account, but it has not been refunded within the RBI mandated turnaround time.')" style="cursor:pointer; background:#fce7f3; color: #075985; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #fbcfe8; transition: 0.2s;">💳 UPI Failure</span>
                <span class="chip" onclick="App.setIssue('I purchased an online course but it did not match the advertised curriculum. The ed-tech company is denying my rightful refund request.')" style="cursor:pointer; background:#f3e8ff; color: #831843; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #fbcfe8; transition: 0.2s;">🎓 Ed-Tech Refund</span>
            `;
        }
        
        container.innerHTML = chipsHTML;
    }"""

# Use regex to replace the old function completely
pattern = re.compile(r'function updateIssueChips\(companyName\) \{.*?\n    \}(?=\s*function setCompany|\s*document\.addEventListener)', re.DOTALL)
if pattern.search(text):
    text = pattern.sub(new_update_issues + "\n", text)
else:
    # Try another catch
    parts = text.split('function updateIssueChips(companyName) {')
    if len(parts) > 1:
        end_idx = parts[1].find('container.innerHTML = chipsHTML;\n    }')
        if end_idx != -1:
            end_idx += len('container.innerHTML = chipsHTML;\n    }')
            text = parts[0] + new_update_issues + parts[1][end_idx:]

# Next replace the setCompany definition so it drops the old updateIssueChips call
setCoRegex = re.compile(r"function setCompany\(name, url\) \{\s*document\.getElementById\('company-name'\)\.value = name;\s*document\.getElementById\('company-website'\)\.value = url;\s*updateIssueChips\(name\);\s*\}")
if setCoRegex.search(text):
    text = setCoRegex.sub(r"function setCompany(name, url) {\n        document.getElementById('company-name').value = name;\n        document.getElementById('company-website').value = url;\n    }", text)

# Lastly remove the eventListener that hooked into companyName input
listener_regex = re.compile(r"document\.addEventListener\('DOMContentLoaded', \(\) => \{\s*const compInput = document\.getElementById\('company-name'\);\s*if \(compInput\) \{\s*compInput\.addEventListener\('input', \(e\) => \{\s*updateIssueChips\(e\.target\.value\);\s*\}\);\s*\}\s*\}\);\s*")
text = listener_regex.sub("", text)

# Add setCategory to Public API returns
if "setCategory," not in text:
    text = text.replace("setCompany,", "setCategory,\n        setCompany,")

with open("static/app.js", "w") as f:
    f.write(text)

print("Updated app.js with category flow.")
