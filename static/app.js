/* ─── Jago Grahak Jago — Frontend Application ───────────────────── */

const App = (() => {
    // ── State ────────────────────────────────────────────────────────
    const state = {
        currentStep: 0,
        complainant: {},
        companyName: '',
        companyWebsite: '',
        issueSummary: '',
        timeline: [],
        evidence: [],
        desiredResolution: '',
        analysisResult: null,
        followUpAnswers: {},
        tier: 'self_send',
        noticeResult: null,
        noticeId: null,
    };

    // ── Step navigation ─────────────────────────────────────────────
    function goTo(step) {
        document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
        const el = document.getElementById(`step-${step}`);
        if (el) el.classList.add('active');
        state.currentStep = step;
        updateProgress(step);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function updateProgress(step) {
        const bar = document.getElementById('progress-bar');
        if (step === 0) {
            bar.classList.add('hidden');
            return;
        }
        bar.classList.remove('hidden');
        document.querySelectorAll('.p-step').forEach(ps => {
            const s = parseInt(ps.dataset.step);
            ps.classList.remove('active', 'done');
            if (s < step) ps.classList.add('done');
            else if (s === step) ps.classList.add('active');
        });
    }

    // ── Start ───────────────────────────────────────────────────────
    function start() { goTo(1); }

    // ── API base: Render backend when on GitHub Pages, same-origin when local ──
    const RENDER_BACKEND = 'https://legaltech-notice-agent.onrender.com';

    function getApiBase() {
        const stored = (localStorage.getItem('legaltech_api_base') || '').trim();
        if (stored) return stored;
        // GitHub Pages can't serve API — use the deployed Render backend
        if (window.location.hostname.endsWith('github.io')) return RENDER_BACKEND;
        return window.location.origin;
    }

    function apiUrl(path) {
        return `${getApiBase().replace(/\/$/, '')}${path}`;
    }

    async function apiFetch(path, options) {
        const base = getApiBase().replace(/\/$/, '');
        const res = await fetch(`${base}${path}`, options);
        return res;
    }

    function saveApiBase() {
        // no-op kept for backwards compat
    }

    function normalizeWebsite(raw) {
        const v = (raw || '').trim();
        if (!v) return null;
        if (/^https?:\/\//i.test(v)) return v;
        return `https://${v}`;
    }

    function isValidHttpUrl(v) {
        if (!v) return true;
        try {
            const u = new URL(v);
            return u.protocol === 'http:' || u.protocol === 'https:';
        } catch (_) {
            return false;
        }
    }

    // ── Step 1 → 2: Complainant ─────────────────────────────────────
    function nextFromComplainant() {
        const name = val('c-name');
        const email = val('c-email');
        const address = val('c-address');
        if (!name || !email || !address) return showError('Please fill in all required fields.');
        state.complainant = {
            full_name: name,
            email: email,
            phone: val('c-phone') || null,
            address: address,
        };
        goTo(2);
    }

    // ── Step 2 → 3: Company ─────────────────────────────────────────
    function nextFromCompany() {
        const name = val('company-name');
        if (!name) return showError('Please enter the company name.');
        state.companyName = name;
        state.companyWebsite = normalizeWebsite(val('company-website'));
        if (!isValidHttpUrl(state.companyWebsite)) {
            return showError('Please enter a valid website URL, e.g. https://example.com');
        }
        goTo(3);
    }

    // ── Step 3 → 4: Analyze ─────────────────────────────────────────
    async function analyzeCase() {
        const summary = val('issue-summary');
        const resolution = val('desired-resolution');
        if (!summary || summary.length < 20) return showError('Please describe your issue in at least 20 characters.');
        if (!resolution) return showError('Please describe what resolution you want.');

        state.issueSummary = summary;
        state.desiredResolution = resolution;

        goTo(4); // show loading
        animateStages(['stage-company', 'stage-contacts', 'stage-policies', 'stage-legal', 'stage-strength'], 6000);

        const body = {
            complainant: state.complainant,
            issue_summary: state.issueSummary,
            desired_resolution: state.desiredResolution,
            company_name_hint: state.companyName,
            website: state.companyWebsite,
            timeline: state.timeline,
            evidence: state.evidence,
        };

        try {
            const res = await apiFetch('/notice/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            if (!res.ok) throw new Error(`Server error: ${res.status}`);
            state.analysisResult = await res.json();
            renderAnalysis();
            goTo(5);
        } catch (err) {
            goTo(3);
            showError('Could not reach the backend server. Please run the app locally: open http://127.0.0.1:8000 in your browser after starting the backend.');
        }
    }

    // ── Render analysis results (step 5) ────────────────────────────
    function renderAnalysis() {
        const a = state.analysisResult;
        const grid = document.getElementById('found-data');

        const cards = [];
        cards.push(foundCard('Company', a.company_name_found || state.companyName, !!a.company_name_found));
        cards.push(foundCard('Website', a.company_domain || state.companyWebsite || 'Not provided', !!a.company_domain));
        cards.push(foundCard('CIN / Registration', a.respondent_cin || 'Not found', !!a.respondent_cin));
        cards.push(foundCard('Registered Name', a.respondent_registered_name || 'Not found', !!a.respondent_registered_name));
        cards.push(foundCard('Grievance Officer Email', a.grievance_officer_email || 'Not found', !!a.grievance_officer_email));
        const contactsStr = a.contacts_found && a.contacts_found.length > 0
            ? a.contacts_found.join(', ') : 'None found';
        cards.push(foundCard('Contacts Found', contactsStr, a.contacts_found && a.contacts_found.length > 0));
        if (a.respondent_registered_office) {
            cards.push(foundCard('Registered Office', a.respondent_registered_office, true));
        }
        const policiesStr = a.policies_found && a.policies_found.length > 0
            ? `${a.policies_found.length} pages scraped` : 'None found';
        cards.push(foundCard('Policies / T&Cs', policiesStr, a.policies_found && a.policies_found.length > 0));

        grid.innerHTML = cards.join('');

        // Case strength
        const csBox = document.getElementById('case-strength-box');
        const level = a.case_strength || 'moderate';
        csBox.className = `case-strength-box ${level}`;
        csBox.innerHTML = `
            <h3>${level === 'strong' ? '💪 Strong Case' : level === 'moderate' ? '⚖️ Moderate Case' : '⚠️ Weak Case'}</h3>
            <p>${a.case_strength_reasoning || ''}</p>
        `;

        // Questions
        const qSection = document.getElementById('questions-section');
        const qList = document.getElementById('questions-list');
        if (a.questions && a.questions.length > 0) {
            qSection.classList.remove('hidden');
            qList.innerHTML = a.questions.map(q => `
                <div class="question-card">
                    <span class="q-label ${q.priority}">${q.priority}</span>
                    <div class="q-text">${esc(q.question)}</div>
                    <div class="q-why">${esc(q.why_it_matters)}</div>
                    <textarea rows="2" data-qid="${esc(q.id)}" placeholder="Your answer (optional)..."
                        oninput="App.saveAnswer('${esc(q.id)}', this.value)"></textarea>
                </div>
            `).join('');
        } else {
            qSection.classList.add('hidden');
        }
    }

    function foundCard(title, value, found) {
        const cls = found ? 'found-card success' : 'found-card warn';
        const valCls = found ? '' : 'not-found';
        return `<div class="${cls}"><h4>${esc(title)}</h4><p class="${valCls}">${esc(value)}</p></div>`;
    }

    function saveAnswer(qid, value) {
        if (value.trim()) state.followUpAnswers[qid] = value.trim();
        else delete state.followUpAnswers[qid];
    }

    // ── Step 6: Select tier ─────────────────────────────────────────
    function selectTier(tier) {
        state.tier = tier;
        document.getElementById('tier-self').classList.toggle('selected', tier === 'self_send');
        document.getElementById('tier-lawyer').classList.toggle('selected', tier === 'lawyer');
        generateNotice();
    }

    // ── Step 7: Generate notice ─────────────────────────────────────
    async function generateNotice() {
        goTo(7);
        animateStages(['gen-stage-1', 'gen-stage-2', 'gen-stage-3', 'gen-stage-4', 'gen-stage-5'], 8000);

        const body = {
            complainant: state.complainant,
            issue_summary: state.issueSummary,
            desired_resolution: state.desiredResolution,
            company_name_hint: state.companyName,
            website: state.companyWebsite,
            timeline: state.timeline,
            evidence: state.evidence,
            tier: state.tier,
            follow_up_answers: Object.keys(state.followUpAnswers).length > 0
                ? state.followUpAnswers : null,
        };

        try {
            const res = await apiFetch('/notice/typed', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            if (!res.ok) throw new Error(`Server error: ${res.status}`);
            state.noticeResult = await res.json();
            state.noticeId = state.noticeResult.notice_id || null;
            renderNotice();
            goTo(8);
        } catch (err) {
            goTo(6);
            showError('Could not reach the backend server. Please run the app locally: open http://127.0.0.1:8000 in your browser after starting the backend.');
        }
    }

    // ── Step 8: Render result ───────────────────────────────────────
    function renderNotice() {
        const r = state.noticeResult;
        const id = state.noticeId;

        document.getElementById('notice-id-display').textContent =
            id ? `Reference: #${id.toUpperCase()}` : '';

        document.getElementById('notice-text').textContent = r.legal_notice || '';

        const isSelf = state.tier === 'self_send';
        document.getElementById('self-send-info').classList.toggle('hidden', !isSelf);
        document.getElementById('lawyer-send-info').classList.toggle('hidden', isSelf);

        if (!isSelf) {
            document.getElementById('notify-email').textContent = state.complainant.email;
        }
    }

    // ── PDF download ────────────────────────────────────────────────
    async function downloadPDF() {
        const body = {
            complainant: state.complainant,
            issue_summary: state.issueSummary,
            desired_resolution: state.desiredResolution,
            company_name_hint: state.companyName,
            website: state.companyWebsite,
            timeline: state.timeline,
            evidence: state.evidence,
            tier: state.tier,
            follow_up_answers: Object.keys(state.followUpAnswers).length > 0
                ? state.followUpAnswers : null,
        };

        // If we have a stored notice_id, use the admin PDF endpoint
        if (state.noticeId) {
            try {
                const res = await apiFetch(`/api/admin/notices/${state.noticeId}/pdf`, {
                    method: 'GET',
                });
                if (res.ok) {
                    const blob = await res.blob();
                    downloadBlob(blob, `Legal_Notice_${state.noticeId}.pdf`);
                    return;
                }
            } catch (_) { /* fall through to typed/pdf */ }
        }

        try {
            const res = await apiFetch('/notice/typed/pdf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            if (!res.ok) throw new Error('PDF generation failed');
            const blob = await res.blob();
            downloadBlob(blob, `Legal_Notice_${state.companyName.replace(/ /g, '_')}.pdf`);
        } catch (err) {
            showError(err.message);
        }
    }

    function downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = filename;
        document.body.appendChild(a); a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // ── Timeline / Evidence dynamic lists ───────────────────────────
    function addTimeline() {
        const input = document.getElementById('timeline-input');
        const v = input.value.trim();
        if (!v) return;
        state.timeline.push(v);
        input.value = '';
        renderList('timeline-list', state.timeline);
    }

    function addEvidence() {
        const input = document.getElementById('evidence-input');
        const v = input.value.trim();
        if (!v) return;
        state.evidence.push(v);
        input.value = '';
        renderList('evidence-list', state.evidence);
    }

    function removeItem(listName, index) {
        state[listName].splice(index, 1);
        renderList(listName === 'timeline' ? 'timeline-list' : 'evidence-list', state[listName]);
    }

    function renderList(containerId, items) {
        const listName = containerId === 'timeline-list' ? 'timeline' : 'evidence';
        document.getElementById(containerId).innerHTML = items.map((item, i) =>
            `<div class="dynamic-item">
                <span>${esc(item)}</span>
                <button type="button" onclick="App.removeItem('${listName}', ${i})">✕</button>
            </div>`
        ).join('');
    }

    // ── Loading stage animation ─────────────────────────────────────
    function animateStages(ids, totalMs) {
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) { el.classList.remove('active', 'done'); }
        });
        const delay = totalMs / ids.length;
        ids.forEach((id, i) => {
            setTimeout(() => {
                const el = document.getElementById(id);
                if (el) el.classList.add('active');
                if (i > 0) {
                    const prev = document.getElementById(ids[i - 1]);
                    if (prev) { prev.classList.remove('active'); prev.classList.add('done'); }
                }
            }, delay * i);
        });
    }

    // ── Error handling ──────────────────────────────────────────────
    function showError(msg) {
        document.getElementById('error-message').textContent = msg;
        document.getElementById('error-overlay').classList.remove('hidden');
    }
    function dismissError() {
        document.getElementById('error-overlay').classList.add('hidden');
    }

    // ── Reset ───────────────────────────────────────────────────────
    function reset() {
        state.currentStep = 0;
        state.complainant = {};
        state.companyName = '';
        state.companyWebsite = '';
        state.issueSummary = '';
        state.timeline = [];
        state.evidence = [];
        state.desiredResolution = '';
        state.analysisResult = null;
        state.followUpAnswers = {};
        state.tier = 'self_send';
        state.noticeResult = null;
        state.noticeId = null;
        // Clear forms
        document.querySelectorAll('input, textarea').forEach(el => el.value = '');
        document.getElementById('timeline-list').innerHTML = '';
        document.getElementById('evidence-list').innerHTML = '';
        goTo(0);
    }

    // ── Utilities ───────────────────────────────────────────────────
    function val(id) { return (document.getElementById(id)?.value || '').trim(); }
    function esc(s) {
        if (!s) return '';
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    // Handle Enter key on dynamic add inputs
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            if (e.target.id === 'timeline-input') { e.preventDefault(); addTimeline(); }
            if (e.target.id === 'evidence-input') { e.preventDefault(); addEvidence(); }
        }
    });

    document.addEventListener('DOMContentLoaded', () => {
        const input = document.getElementById('api-base');
        if (input) input.value = localStorage.getItem('legaltech_api_base') || '';
    });

    // ── Public API ──────────────────────────────────────────────────
    return {
        start, goTo, nextFromComplainant, nextFromCompany, analyzeCase,
        selectTier, generateNotice, downloadPDF, renderNotice,
        addTimeline, addEvidence, removeItem, saveAnswer,
        showError, dismissError, reset, saveApiBase,
    };
})();
