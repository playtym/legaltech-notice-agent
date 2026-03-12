/* ─── Jago Grahak Jago — Frontend Application ───────────────────── */

const App = (() => {
    let recognition = null;
    let recognitionField = null;
    let capturedFinalText = '';
    let smartRecognition = null;
    let smartTranscript = '';

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

    // ── Loading tips (rotate during wait) ─────────────────────────
    const _LOADING_TIPS = [
        "Did you know? Under CPA 2019, companies must resolve complaints within 30 days of receiving a legal notice.",
        "A well-drafted legal notice gets a response from 70% of companies — most prefer to settle than face consumer court.",
        "Consumer courts in India have a 90-day disposal mandate and zero court fees for claims under ₹5 lakh.",
        "Tip: Keep all email confirmations and screenshots. Courts accept digital evidence under IT Act §65B.",
        "Under the Consumer Protection Act, even 'no refund' clauses are invalid if the product/service is defective.",
        "Companies that ignore legal notices face up to ₹10 lakh compensation + litigation costs in consumer court.",
        "Fun fact: India's consumer courts handle 5 lakh+ cases per year — and complainants win more than 60% of them.",
        "Filing on e-daakhil.nic.in after the cure period takes less than 15 minutes. No lawyer required.",
    ];

    function startLoadingTips(elementId) {
        const el = document.getElementById(elementId);
        if (!el) return null;
        let idx = Math.floor(Math.random() * _LOADING_TIPS.length);
        el.textContent = _LOADING_TIPS[idx];
        el.classList.add('visible');
        return setInterval(() => {
            idx = (idx + 1) % _LOADING_TIPS.length;
            el.classList.remove('visible');
            setTimeout(() => {
                el.textContent = _LOADING_TIPS[idx];
                el.classList.add('visible');
            }, 300);
        }, 5000);
    }

    let _tipInterval4 = null;
    let _tipInterval7 = null;

    // ── Step navigation ─────────────────────────────────────────────
    function goTo(step) {
        // Stop tip rotations when leaving loading screens
        if (_tipInterval4) { clearInterval(_tipInterval4); _tipInterval4 = null; }
        if (_tipInterval7) { clearInterval(_tipInterval7); _tipInterval7 = null; }

        document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
        const el = document.getElementById(`step-${step}`);
        if (el) el.classList.add('active');
        state.currentStep = step;
        updateProgress(step);
        window.scrollTo({ top: 0, behavior: 'smooth' });

        // Start tip rotation on loading screens
        if (step === 4) _tipInterval4 = startLoadingTips('loading-tip-4');
        if (step === 7) _tipInterval7 = startLoadingTips('loading-tip-7');
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

    // ── API base: App Runner backend when on GitHub Pages, same-origin when local ──
    const API_BACKEND = 'https://v5pah3m82k.ap-south-1.awsapprunner.com';

    function getApiBase() {
        const stored = (localStorage.getItem('legaltech_api_base') || '').trim();
        if (stored) return stored;
        // GitHub Pages can't serve API — use the deployed App Runner backend
        if (window.location.hostname.endsWith('github.io')) return API_BACKEND;
        return window.location.origin;
    }

    function apiBaseCandidates() {
        const stored = (localStorage.getItem('legaltech_api_base') || '').trim();
        const candidates = [];

        if (stored) candidates.push(stored.replace(/\/$/, ''));

        if (window.location.hostname.endsWith('github.io')) {
            candidates.push(API_BACKEND.replace(/\/$/, ''));
        } else {
            candidates.push(window.location.origin.replace(/\/$/, ''));
        }

        return [...new Set(candidates)];
    }

    function apiUrl(path) {
        return `${getApiBase().replace(/\/$/, '')}${path}`;
    }

    async function apiFetch(path, options) {
        const candidates = apiBaseCandidates();
        let lastError = null;

        for (const base of candidates) {
            try {
                const res = await fetch(`${base}${path}`, options);
                if (res.ok || res.status < 500) {
                    // Persist the working origin so subsequent calls are fast.
                    localStorage.setItem('legaltech_api_base', base);
                    return res;
                }
                lastError = new Error(`Server error: ${res.status} from ${base}`);
            } catch (err) {
                lastError = err;
            }
        }

        throw lastError || new Error('Unable to reach API backend');
    }

    async function translateToEnglish(text) {
        const payload = { text };
        const res = await apiFetch('/translate/to-english', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(`Translation failed: ${res.status}`);
        const data = await res.json();
        return (data.translated_text || '').trim();
    }

    async function refineSpeechTranscript(text) {
        const res = await apiFetch('/speech/refine', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ transcript_text: text }),
        });
        if (!res.ok) throw new Error(`Speech refinement failed: ${res.status}`);
        return res.json();
    }

    function resolveRecognitionLang(raw) {
        const v = `${raw || ''}`.trim();
        if (!v || v === 'auto-hinglish') {
            // en-IN generally performs better for Hinglish/mixed speech in web speech engines.
            return 'en-IN';
        }
        return v;
    }

    function setVoiceStatus(fieldId, message) {
        const status = document.getElementById(`voice-status-${fieldId}`);
        if (status) status.textContent = message;
    }

    function setSmartStatus(message) {
        const el = document.getElementById('smart-intake-status');
        if (el) el.textContent = message;
    }

    function criticalQuestions(analysis) {
        if (!analysis || !Array.isArray(analysis.questions)) return [];
        return analysis.questions.filter((q) => `${q.priority || ''}`.toLowerCase() === 'critical');
    }

    function isHighConfidence(analysis) {
        if (!analysis || !analysis.ready_to_generate) return false;
        const strength = `${analysis.case_strength || ''}`.toLowerCase();
        const criticalCount = criticalQuestions(analysis).length;
        return strength === 'strong' || (strength === 'moderate' && criticalCount === 0);
    }

    async function processSmartTranscript(transcriptText) {
        const payload = {
            transcript_text: transcriptText,
            complainant: state.complainant,
            company_name_hint: state.companyName || null,
            website: state.companyWebsite || null,
            desired_resolution: state.desiredResolution || null,
            timeline: state.timeline,
            evidence: state.evidence,
            jurisdiction: 'India',
        };

        const res = await apiFetch('/intake/from-transcript', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(`Smart intake failed: ${res.status}`);
        const data = await res.json();

        const issueEl = document.getElementById('issue-summary');
        const resEl = document.getElementById('desired-resolution');
        if (issueEl && data.issue_summary) issueEl.value = data.issue_summary;
        if (resEl && data.desired_resolution) resEl.value = data.desired_resolution;

        state.issueSummary = data.issue_summary || state.issueSummary;
        state.desiredResolution = data.desired_resolution || state.desiredResolution;

        if ((!state.companyName || !state.companyName.trim()) && data.company_name_hint) {
            state.companyName = data.company_name_hint;
            const companyInput = document.getElementById('company-name');
            if (companyInput) companyInput.value = data.company_name_hint;
        }

        if ((!state.companyWebsite || !state.companyWebsite.trim()) && data.website) {
            state.companyWebsite = data.website;
            const websiteInput = document.getElementById('company-website');
            if (websiteInput) websiteInput.value = data.website;
        }

        state.timeline = Array.isArray(data.timeline) ? [...new Set(data.timeline.map(x => `${x}`.trim()).filter(Boolean))] : state.timeline;
        state.evidence = Array.isArray(data.evidence) ? [...new Set(data.evidence.map(x => `${x}`.trim()).filter(Boolean))] : state.evidence;
        renderList('timeline-list', state.timeline);
        renderList('evidence-list', state.evidence);

        if (data.auto_answers && typeof data.auto_answers === 'object') {
            state.followUpAnswers = { ...state.followUpAnswers, ...data.auto_answers };
        }

        if (data.analysis) {
            state.analysisResult = data.analysis;
            if (isHighConfidence(data.analysis)) {
                setSmartStatus('High confidence case detected. Generating your notice automatically...');
                state.tier = 'self_send';
                await generateNotice();
                return;
            }

            renderAnalysis();
            goTo(5);

            const remainingCritical = criticalQuestions(data.analysis).length;
            if (remainingCritical > 0) {
                setSmartStatus(`Done. We pre-filled your case. Please answer ${remainingCritical} critical question(s) to strengthen notice generation.`);
            } else {
                setSmartStatus('Done. We auto-filled details and pre-answered follow-up questions from your speech.');
            }
        } else {
            setSmartStatus('Done. We filled the form from your speech.');
        }
    }

    function startSmartIntake() {
        if (!state.complainant?.full_name || !state.complainant?.email || !state.complainant?.address) {
            showError('Please complete Step 1 (your details) before using Speak Once intake.');
            return;
        }
        const Ctor = speechCtor();
        if (!Ctor) {
            showError('Voice input is not supported in this browser. Please use Chrome.');
            return;
        }

        if (smartRecognition) {
            smartRecognition.stop();
        }

        smartTranscript = '';
        smartRecognition = new Ctor();
        smartRecognition.lang = 'en-IN';
        smartRecognition.continuous = true;
        smartRecognition.interimResults = true;

        smartRecognition.onstart = () => setSmartStatus('Listening... describe your entire issue naturally.');

        smartRecognition.onresult = (event) => {
            let interim = '';
            for (let i = event.resultIndex; i < event.results.length; i += 1) {
                const txt = event.results[i][0].transcript;
                if (event.results[i].isFinal) smartTranscript += `${txt} `;
                else interim += txt;
            }
            if (interim.trim()) setSmartStatus(`Listening... ${interim.trim()}`);
        };

        smartRecognition.onerror = (event) => {
            setSmartStatus(`Mic error: ${event.error || 'unknown'}`);
        };

        smartRecognition.onend = async () => {
            const finalText = smartTranscript.trim();
            smartRecognition = null;
            smartTranscript = '';
            if (!finalText) {
                setSmartStatus('Stopped. No speech detected.');
                return;
            }
            try {
                setSmartStatus('Refining mixed Hindi-English speech with AI...');
                const refined = await refineSpeechTranscript(finalText);
                const transcriptForIntake = (refined.english_text || finalText || '').trim();
                await processSmartTranscript(transcriptForIntake);
            } catch (err) {
                setSmartStatus('Could not auto-process speech. Please try again or type manually.');
                showError(`${err?.message || err}`);
            }
        };

        smartRecognition.start();
    }

    function stopSmartIntake() {
        if (smartRecognition) {
            smartRecognition.stop();
            setSmartStatus('Stopping...');
        }
    }

    function speechCtor() {
        return window.SpeechRecognition || window.webkitSpeechRecognition || null;
    }

    async function startVoiceInput(fieldId) {
        const Ctor = speechCtor();
        if (!Ctor) {
            showError('Voice input is not supported in this browser. Please use Chrome on desktop/mobile.');
            return;
        }

        if (recognition && recognitionField && recognitionField !== fieldId) {
            recognition.stop();
        }

        capturedFinalText = '';
        recognitionField = fieldId;
        const langSel = document.getElementById(`voice-lang-${fieldId}`);
        const recogLang = resolveRecognitionLang(langSel ? langSel.value : 'auto-hinglish');

        recognition = new Ctor();
        recognition.lang = recogLang;
        recognition.continuous = true;
        recognition.interimResults = true;

        recognition.onstart = () => {
            setVoiceStatus(fieldId, 'Listening... speak naturally in Hindi or English.');
        };

        recognition.onresult = (event) => {
            let interim = '';
            for (let i = event.resultIndex; i < event.results.length; i += 1) {
                const part = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    capturedFinalText += `${part} `;
                } else {
                    interim += part;
                }
            }
            if (interim.trim()) {
                setVoiceStatus(fieldId, `Listening... ${interim.trim()}`);
            }
        };

        recognition.onerror = (event) => {
            setVoiceStatus(fieldId, `Mic error: ${event.error || 'unknown error'}`);
        };

        recognition.onend = async () => {
            const transcript = capturedFinalText.trim();
            if (!transcript) {
                setVoiceStatus(fieldId, 'Stopped. No speech detected.');
                return;
            }

            try {
                setVoiceStatus(fieldId, 'Refining Hinglish transcript...');
                const refined = await refineSpeechTranscript(transcript);
                const translated = (refined.english_text || '').trim() || await translateToEnglish(transcript);
                const target = document.getElementById(fieldId);
                if (target) {
                    const existing = target.value.trim();
                    target.value = [existing, translated].filter(Boolean).join('\n');
                }
                setVoiceStatus(fieldId, 'Done. Speech added in English script and translated English.');
            } catch (_) {
                const target = document.getElementById(fieldId);
                if (target) {
                    const existing = target.value.trim();
                    target.value = [existing, transcript].filter(Boolean).join('\n');
                }
                setVoiceStatus(fieldId, 'Translation failed, original speech text was added.');
            } finally {
                recognition = null;
                recognitionField = null;
                capturedFinalText = '';
            }
        };

        recognition.start();
    }

    function stopVoiceInput(fieldId) {
        if (recognition && recognitionField === fieldId) {
            recognition.stop();
            setVoiceStatus(fieldId, 'Stopping...');
        }
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
            previous_answers: Object.keys(state.followUpAnswers).length > 0 ? state.followUpAnswers : null,
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
            const attempted = apiBaseCandidates().join(', ');
            showError(`Could not reach backend. Tried: ${attempted}. Please refresh and try again.`);
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
        const allQuestions = Array.isArray(a.questions) ? a.questions : [];
        const criticalOnly = allQuestions.filter((q) => `${q.priority || ''}`.toLowerCase() === 'critical');
        const shownQuestions = !a.ready_to_generate
            ? (criticalOnly.length > 0 ? criticalOnly : allQuestions.slice(0, 3))
            : allQuestions;

        if (shownQuestions.length > 0) {
            qSection.classList.remove('hidden');
            qList.innerHTML = shownQuestions.map(q => `
                <div class="question-card">
                    <span class="q-label ${q.priority}">${q.priority}</span>
                    <div class="q-text">${esc(q.question)}</div>
                    <div class="q-why">${esc(q.why_it_matters)}</div>
                    <textarea rows="2" data-qid="${esc(q.id)}" placeholder="Your answer (optional)..."
                        oninput="App.saveAnswer('${esc(q.id)}', this.value)">${esc(state.followUpAnswers[q.id] || '')}</textarea>
                </div>
            `).join('');
        } else {
            qSection.classList.add('hidden');
        }

        // Strength nudge bar
        renderStrengthNudge(shownQuestions);

        // Value preview
        renderValuePreview();

        // Tier urgency (pre-calculate for step 6)
        renderTierUrgency();
    }

    function foundCard(title, value, found) {
        const cls = found ? 'found-card success' : 'found-card warn';
        const valCls = found ? '' : 'not-found';
        return `<div class="${cls}"><h4>${esc(title)}</h4><p class="${valCls}">${esc(value)}</p></div>`;
    }

    function saveAnswer(qid, value) {
        if (value.trim()) state.followUpAnswers[qid] = value.trim();
        else delete state.followUpAnswers[qid];
        // Re-render strength nudge to reflect progress
        const a = state.analysisResult;
        if (a) {
            const allQ = Array.isArray(a.questions) ? a.questions : [];
            renderStrengthNudge(allQ);
        }
    }

    // ── Strength nudge bar ──────────────────────────────────────────
    function renderStrengthNudge(questions) {
        const nudge = document.getElementById('strength-nudge');
        const fill = document.getElementById('strength-nudge-fill');
        const text = document.getElementById('strength-nudge-text');
        if (!nudge || !fill || !text) return;

        const total = questions.length;
        if (total === 0) { nudge.classList.add('hidden'); return; }
        nudge.classList.remove('hidden');

        const answered = questions.filter(q => state.followUpAnswers[q.id]).length;
        const pct = Math.round((answered / total) * 100);
        const baseStrength = (state.analysisResult?.case_strength || 'moderate').toLowerCase();

        // Base starts at 40 (weak), 60 (moderate), 80 (strong)
        const baseVal = baseStrength === 'strong' ? 80 : baseStrength === 'moderate' ? 60 : 40;
        const bonus = total > 0 ? Math.round(((100 - baseVal) * answered) / total) : 0;
        const effectivePct = Math.min(baseVal + bonus, 100);

        fill.style.width = effectivePct + '%';
        fill.className = 'strength-nudge-fill ' +
            (effectivePct >= 80 ? 'strong' : effectivePct >= 55 ? 'moderate' : 'weak');

        if (answered === total) {
            text.textContent = `Notice strength: ${effectivePct}% — Maximum power!`;
        } else {
            text.textContent = `Notice strength: ${effectivePct}% — answer ${total - answered} more to maximize`;
        }
    }

    // ── Value preview (what the notice will include) ────────────────
    function renderValuePreview() {
        const grid = document.getElementById('value-preview-grid');
        if (!grid) return;
        const a = state.analysisResult;

        const items = [];
        const sectionCount = a?.policies_found?.length || 0;
        items.push(vpItem('⚖️', 'Statutory Arguments', 'Legal sections from 15+ Indian acts'));
        items.push(vpItem('🛡️', 'Defense Counter-Arguments', 'Pre-emptive rebuttals to company T&Cs'));
        items.push(vpItem('🔥', 'Escalation Strategy', 'Sector regulators & pressure tactics'));
        if (a?.respondent_cin) items.push(vpItem('🏛️', 'Company Identity', `CIN: ${a.respondent_cin}`));
        if (sectionCount > 0) items.push(vpItem('📄', 'Policy Analysis', `${sectionCount} pages of T&Cs analyzed`));
        if (a?.contacts_found?.length > 0) items.push(vpItem('📞', 'Contact Details', `${a.contacts_found.length} contacts auto-discovered`));
        items.push(vpItem('📑', 'Court-Ready PDF', 'Formatted for consumer commission filing'));
        items.push(vpItem('⏱️', 'Cure Period', 'Statutory deadline for company response'));

        grid.innerHTML = items.join('');
    }

    function vpItem(icon, title, desc) {
        return `<div class="vp-item"><span class="vp-icon">${icon}</span><div><strong>${esc(title)}</strong><br><small>${esc(desc)}</small></div></div>`;
    }

    // ── Tier urgency messaging ──────────────────────────────────────
    function renderTierUrgency() {
        const el = document.getElementById('tier-urgency');
        if (!el) return;

        // Generate urgency based on case context
        const strength = (state.analysisResult?.case_strength || '').toLowerCase();
        if (strength === 'strong') {
            el.innerHTML = `<p>⚡ <strong>You have a strong case.</strong> Don't weaken it with informal delivery. A lawyer-served notice signals real legal intent.</p>`;
        } else if (strength === 'moderate') {
            el.innerHTML = `<p>⏰ <strong>Act now.</strong> Limitation periods are running. A properly served notice preserves your legal rights and puts the company on formal notice.</p>`;
        } else {
            el.innerHTML = `<p>💡 <strong>Maximize your chances.</strong> Even moderate cases succeed when professionally presented. A lawyer-reviewed notice fills gaps and adds credibility.</p>`;
        }
    }

    // ── Upgrade self-send → lawyer ──────────────────────────────────
    function upgradeTier() {
        state.tier = 'lawyer';
        generateNotice();
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
            const attempted = apiBaseCandidates().join(', ');
            showError(`Could not reach backend. Tried: ${attempted}. Please refresh and try again.`);
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
        selectTier, generateNotice, downloadPDF, renderNotice, upgradeTier,
        addTimeline, addEvidence, removeItem, saveAnswer,
        showError, dismissError, reset, saveApiBase,
        startVoiceInput, stopVoiceInput,
        startSmartIntake, stopSmartIntake,
    };
})();
