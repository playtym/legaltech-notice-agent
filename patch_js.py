with open("static/app.js", "r") as f:
    js = f.read()

funcs = """
    // ── Pre-fill helpers for better UX ────────────────────────────────
    function setCompany(name, url) {
        document.getElementById('company-name').value = name;
        document.getElementById('company-website').value = url;
    }
    function setIssue(text) {
        const el = document.getElementById('issue-summary');
        el.value = text;
        el.focus();
    }
"""

if "function setCompany" not in js:
    # insert before "const API_BACKEND"
    js = js.replace("const API_BACKEND =", funcs + "\n    const API_BACKEND =")

if "setCompany," not in js:
    # export them in App
    js = js.replace("return {", "return {\n        setCompany,\n        setIssue,")

with open("static/app.js", "w") as f:
    f.write(js)

print("Updated app.js")
