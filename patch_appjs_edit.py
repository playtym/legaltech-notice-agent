with open("static/app.js", "r", encoding="utf-8") as f:
    js = f.read()

# 1. Modify fetch email execution and move it to a generic finalize function.
# Wait, renderNotice() has the apiFetch('/notice/deliver...') inside it. We need to extract that out.

finalize_js = """
    async function finalizeNotice() {
        // Save the edited text back to state
        const editedText = document.getElementById('notice-text-editor').value;
        state.noticeResult.legal_notice = editedText;

        // Move to success step
        goTo(9);

        // Trigger delivery
        const companyName = state.companyName || 'Company';
        const isLawyer = state.tier === 'lawyer';
        if (state.complainant && state.complainant.email) {
            apiFetch(`/notice/deliver?to_email=${encodeURIComponent(state.complainant.email)}&to_name=${encodeURIComponent(state.complainant.full_name)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    notice_text: state.noticeResult.legal_notice,
                    company_name: companyName,
                    is_lawyer_tier: isLawyer,
                }),
            }).catch(e => console.warn('Delivery trigger failed:', e));
        }

        // Render result display in step 9
        renderFinalSuccess();
    }

    function renderFinalSuccess() {
        const r = state.noticeResult;
        const id = state.noticeId;

        document.getElementById('notice-id-display').textContent = id ? `Reference: #${id.toUpperCase()}` : '';
        document.getElementById('notice-text').textContent = r.legal_notice || '';
        
        const isSelf = state.tier === 'self_send';
        document.getElementById('self-send-info').classList.toggle('hidden', !isSelf);
        document.getElementById('lawyer-send-info').classList.toggle('hidden', isSelf);
        
        if (!isSelf) {
            // Setup email text
            document.getElementById('notify-email').textContent = state.complainant?.email || '';
        }
    }
"""

if "function finalizeNotice" not in js:
    js = js.replace("function renderNotice() {", finalize_js + "\n    function renderNotice() {")

# 2. Modify renderNotice to just populate the editor and move to step 8
import re

render_notice_replacement = """    function renderNotice() {
        // Setup editing view
        goTo(8);
        document.getElementById('notice-text-editor').value = state.noticeResult?.legal_notice || '';
        document.getElementById('lawyer-nudge-edit').style.display = (state.tier === 'lawyer') ? 'block' : 'none';
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }"""

# Using regex to replace the entire renderNotice function.
js = re.sub(
    r'function renderNotice\(\) \{[\s\S]*?(document\.getElementById\(\'notice\-text\'\)\.parentElement;\s*if\(textContainer\) \{\s*textContainer\.parentElement\.insertBefore\(emailMsg, textContainer\);\s*\}\s*)\}',
    render_notice_replacement,
    js
)

# 3. Expose finalizeNotice
if "finalizeNotice," not in js:
    js = js.replace("return {", "return {\n        finalizeNotice,")


with open("static/app.js", "w", encoding="utf-8") as f:
    f.write(js)

print("Updated app.js for editing step")
