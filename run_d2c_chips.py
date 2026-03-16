import re

with open("static/app.js", "r") as f:
    text = f.read()

# Add condition for D2C brands
d2c_condition = """} else if (keyword.includes("boat") || keyword.includes("mamaearth") || keyword.includes("sugar") || keyword.includes("noise") || keyword.includes("wow") || keyword.includes("d2c") || keyword.includes("brand") || keyword.includes("nykaa")) {
            chipsHTML = `
                <span class="chip" onclick="App.setIssue('I was charged for a prepaid order but the D2C brand never shipped the product and has stopped responding to my emails.')" style="cursor:pointer; background:#fce7f3; color: #075985; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #fbcfe8; transition: 0.2s;">🚫 Paid but Not Shipped</span>
                <span class="chip" onclick="App.setIssue('I ordered directly from the brand\\'s official website but received a counterfeit/fake product. They are ignoring my refund requests.')" style="cursor:pointer; background:#e0e7ff; color: #3730a3; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #c7d2fe; transition: 0.2s;">🛍️ Fake/Counterfeit</span>
                <span class="chip" onclick="App.setIssue('The brand advertised a false discount/scam. They cancelled my order after payment and refused to refund the amount deducted.')" style="cursor:pointer; background:#e0f2fe; color: #312e81; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #bae6fd; transition: 0.2s;">💸 Sale Fraud/Scam</span>
            `;
        } else {"""

text = text.replace("} else {", d2c_condition, 1)

with open("static/app.js", "w") as f:
    f.write(text)
print("Updated app.js for D2C chips.")
