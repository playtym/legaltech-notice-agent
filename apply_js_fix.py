import re
with open("static/app.js", "r") as f:
    text = f.read()

target = "if (!resolution) return showError('Please describe what resolution you want.');"

replacement = """if (!resolution || resolution.length < 5) return showError('Please describe what resolution you want in at least 5 characters (e.g., \"Full refund\").');
        if (summary.length > 10000) return showError('Issue summary is too long (max 10,000 characters).');
        if (resolution.length > 2000) return showError('Desired resolution is too long (max 2,000 characters).');
        if (objection && objection.length > 5000) return showError('Company objection is too long (max 5,000 characters).');"""

text = text.replace(target, replacement)

with open("static/app.js", "w") as f:
    f.write(text)

print("UI valid patched")
