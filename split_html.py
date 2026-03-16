import re

with open('static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Rename existing step-8 to step-9
html = html.replace('<section class="step" id="step-8">', '<section class="step" id="step-9">')

# 2. Insert new step-8 before step-9
new_step_8 = """<!-- ── Step 8 : Edit Draft ────────────────────────────────── -->
<section class="step" id="step-8">
    <div class="card">
        <div class="card-header">
            <h2>Review & Edit Draft</h2>
            <p class="card-sub">Please review the generated draft below. You can safely edit names, dates, or demands before finalizing.</p>
        </div>
        <div style="padding: 0 24px 24px;">
            <textarea id="notice-text-editor" style="width: 100%; min-height: 500px; padding: 16px; font-family: monospace; font-size: 13px; border: 1px solid var(--border); border-radius: 8px; line-height: 1.6; resize: vertical; margin-bottom: 24px; background: #fafafa;"></textarea>
            
            <div class="lawyer-nudge" id="lawyer-nudge-edit" style="display:none; background: #eef2ff; color: #3730a3; padding: 16px; border-radius: 8px; margin-bottom: 24px; font-size: 0.95rem; border: 1px solid #c7d2fe;">
                <strong>Lawyer-Assisted Tier Active:</strong> Make any personal tweaks here. Once finalized, this draft will be sent securely to our advocate network for formal review and letterhead attestation.
            </div>

            <button class="btn btn-primary btn-block btn-lg" onclick="App.finalizeNotice()">Approve & Finalize Document &rarr;</button>
        </div>
    </div>
</section>

"""

if 'id="notice-text-editor"' not in html:
    html = html.replace('<!-- ── Step 8 : Result ────────────────────────────────────── -->', new_step_8 + '<!-- ── Step 9 : Result ────────────────────────────────────── -->')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Split Step 8 and 9 in html")
