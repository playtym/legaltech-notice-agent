import os

path = 'static/index.html'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

objection_html = """
            <!-- ── Company's Response / Objection ── -->
            <div class="form-section">
                <label for="company-objection" class="section-label">Company's Response / Objection <span style="font-weight: normal; color: #6b7280; font-size: 0.75rem; margin-left: 4px;">optional</span></label>
                <textarea id="company-objection" rows="3" placeholder="e.g. They claimed the return window had passed, or simply ignored my emails." maxlength="2000"></textarea>
            </div>

            <hr class="section-divider">

            <!-- ── Resolution ── -->
"""

if 'id="company-objection"' not in text:
    text = text.replace('<!-- ── Resolution ── -->', objection_html.lstrip())
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    print("Added company-objection back!")
else:
    print("company-objection already exists.")
