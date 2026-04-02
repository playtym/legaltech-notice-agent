/* ─── Jago Grahak Jago — Frontend Application ───────────────────── */

// ── Global Error Fallbacks ──────────────────────────────────────────
window.addEventListener('error', (event) => {
    console.error('Unhandled UI exception:', event.error || event.message);
    showGlobalError('An unexpected error occurred. Please refresh the page and try again.');
});
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled Promise rejection:', event.reason);
    showGlobalError('A network or server error occurred. Please try your request again.');
});

function showGlobalError(msg) {
    const banner = document.getElementById('global-error-banner');
    if (banner) {
        banner.textContent = msg;
        banner.style.display = 'block';
        setTimeout(() => { banner.style.display = 'none'; }, 8000);
    } else {
        alert(msg);
    }
}

const App = (() => {
    let recognition = null;
    let recognitionField = null;
    let capturedFinalText = '';

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
        companyObjection: '',
        analysisResult: null,
        followUpAnswers: {},
        tier: 'self_send',
        noticeResult: null,
        noticeId: null,
        uploadedFiles: [],  // [{file_id, filename, content_type, size, thumbUrl?}]
    };

    // ── Loading tips (rotate during wait) ─────────────────────────
    
    // ── Safe Local Storage Recovery ───────────────────────────────────
    function recoverDraft() {
        try {
            const raw = localStorage.getItem('lawly_draft');
            if (!raw) return;
            const draft = JSON.parse(raw);
            if (draft.companyName) document.getElementById('company-name').value = draft.companyName;
            if (draft.companyWebsite) document.getElementById('company-website').value = draft.companyWebsite;
            if (draft.issueSummary) document.getElementById('issue-summary').value = draft.issueSummary;
            if (draft.fdName) document.getElementById('fd-name').value = draft.fdName;
            if (draft.fdEmail) document.getElementById('fd-email').value = draft.fdEmail;
            if (draft.fdPhone) document.getElementById('fd-phone').value = draft.fdPhone;
            if (draft.fdAddress) document.getElementById('fd-address').value = draft.fdAddress;
        } catch (e) {
            console.warn("Draft recovery failed", e);
        }
    }

    // Attach listeners to save draft on input
    document.addEventListener('DOMContentLoaded', () => {
        recoverDraft();
        const inputs = ['company-name', 'company-website', 'issue-summary', 'fd-name', 'fd-email', 'fd-phone', 'fd-address'];
        inputs.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('input', saveDraft);
        });
    });

    function saveDraft() {
        try {
            const draft = {
                companyName: document.getElementById('company-name')?.value || '',
                companyWebsite: document.getElementById('company-website')?.value || '',
                issueSummary: document.getElementById('issue-summary')?.value || '',
                fdName: document.getElementById('fd-name')?.value || '',
                fdEmail: document.getElementById('fd-email')?.value || '',
                fdPhone: document.getElementById('fd-phone')?.value || '',
                fdAddress: document.getElementById('fd-address')?.value || '',
            };
            localStorage.setItem('lawly_draft', JSON.stringify(draft));
        } catch (e) {
            console.warn("Draft save failed", e);
        }
    }

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
    function goTo(step, options = {}) {
        const resetTier = options.resetTier !== false;

        // Stop tip rotations when leaving loading screens
        if (_tipInterval4) { clearInterval(_tipInterval4); _tipInterval4 = null; }
        if (_tipInterval7) { clearInterval(_tipInterval7); _tipInterval7 = null; }

        // If user navigates away from generation (step 7) back to an early step,
        // clear the in-flight guard so they can retry.
        if (step < 7 && _generateInFlight) {
            _generateInFlight = false;
        }

        document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
        const el = document.getElementById(`step-${step}`);
        if (el) el.classList.add('active');
        state.currentStep = step;
        updateProgress(step);
        window.scrollTo({ top: 0, behavior: 'smooth' });

        if (step === 6 && resetTier) {
            resetTierSelection();
        }

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
    function start() { goTo(0); }

    // ── API base: dedicated API domain in production, same-origin for local dev ──
    
    // ── Pre-fill helpers for better UX ────────────────────────────────
    
    function setCategory(cat, element) {
        state.category = cat;
        // reset chips and mark selected one with .active class
        document.querySelectorAll('.cat-chip').forEach(el => {
            el.classList.remove('active');
            el.setAttribute('aria-selected', 'false');
        });
        if (element) {
            element.classList.add('active');
            element.setAttribute('aria-selected', 'true');
        }
        updateIssueChips();
    }

    function setCompany(name, url) {
        document.getElementById('company-name').value = name;
        document.getElementById('company-website').value = url;
    }
    
    function updateIssueChips() {
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
                <span class="chip" onclick="App.setIssue('I ordered directly from the brand\'s official website but received a counterfeit/fake product. They are ignoring my refund requests.')" style="cursor:pointer; background:#e0e7ff; color: #3730a3; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; border: 1px solid #c7d2fe; transition: 0.2s;">🛍️ Fake/Counterfeit</span>
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
    }

    function setIssue(text) {
        const el = document.getElementById('issue-summary');
        el.value = text;
        el.focus();
    }

    const API_BACKEND = 'https://api.lawly.store';

    function isLocalHost() {
        return ['localhost', '127.0.0.1'].includes(window.location.hostname);
    }

    function getApiBase() {
        const stored = (localStorage.getItem('legaltech_api_base') || '').trim();
        if (stored) {
            // Never pin production traffic to static website origin.
            if (!isLocalHost() && stored.replace(/\/$/, '') === window.location.origin.replace(/\/$/, '')) {
                localStorage.removeItem('legaltech_api_base');
            } else {
                return stored;
            }
        }
        if (isLocalHost()) return window.location.origin;
        return API_BACKEND;
    }

    function apiBaseCandidates() {
        let stored = (localStorage.getItem('legaltech_api_base') || '').trim();
        // Force drop bad stored origins from recent buggy deployment
        if (stored.includes('lawly.store') && !stored.includes('api.lawly.store')) {
            localStorage.removeItem('legaltech_api_base');
            stored = '';
        }

        const candidates = [];

        if (stored) candidates.push(stored.replace(/\/$/, ''));

        if (isLocalHost()) {
            candidates.push(window.location.origin.replace(/\/$/, ''));
            // Always try localhost backend too when developing
            candidates.push('http://127.0.0.1:8000');
        } else {
            candidates.push(API_BACKEND.replace(/\/$/, ''));
        }

        return [...new Set(candidates)];
    }

    function normalizeBase(base) {
        return `${base || ''}`.replace(/\/$/, '');
    }

    function isWrongOriginResponse(base, path, res) {
        const b = normalizeBase(base);
        const siteOrigin = normalizeBase(window.location.origin);
        const contentType = (res.headers.get('content-type') || '').toLowerCase();
        const expectsBinary = /pdf($|\?)/.test(path);

        if (res.status === 404 || res.status === 405) return true;

        if (!isLocalHost() && b === siteOrigin && (res.status === 401 || res.status === 403)) {
            return true;
        }

        if (!expectsBinary && contentType && !contentType.includes('application/json')) {
            return true;
        }

        return false;
    }

    async function responseErrorMessage(res, fallback) {
        const base = fallback || `Request failed (${res.status})`;
        const contentType = (res.headers.get('content-type') || '').toLowerCase();

        try {
            if (contentType.includes('application/json')) {
                const data = await res.json();
                if (typeof data?.detail === 'string' && data.detail.trim()) return data.detail.trim();
                if (Array.isArray(data?.detail) && data.detail.length) {
                    const msgs = data.detail
                        .map((d) => d?.msg || d?.message || '')
                        .map((s) => `${s}`.trim())
                        .filter(Boolean);
                    if (msgs.length) return msgs.join('; ');
                }
                if (typeof data?.message === 'string' && data.message.trim()) return data.message.trim();
            } else {
                const txt = (await res.text()).trim();
                if (txt) return txt.slice(0, 220);
            }
        } catch (_) {
            // Fall back to generic message.
        }

        return base;
    }

    async function apiFetch(path, options) {
        const candidates = apiBaseCandidates();
        let lastError = null;
        let lastResponse = null;

        for (const base of candidates) {
            try {
                const res = await fetch(`${base}${path}`, options);

                // Even on 200, reject if response is clearly not from the API
                // (e.g. S3/CloudFront SPA fallback returning index.html).
                if (isWrongOriginResponse(base, path, res)) {
                    lastResponse = res;
                    continue;
                }

                if (res.ok) {
                    // Persist the working origin so subsequent calls are fast.
                    localStorage.setItem('legaltech_api_base', base);
                    return res;
                }

                // For valid API-origin client errors (e.g. 400/422), return response.
                if (res.status < 500) {
                    localStorage.setItem('legaltech_api_base', base);
                    return res;
                }

                // 500+ server errors from the right origin: return immediately,
                // don't waste time trying other candidates.
                return res;
            } catch (err) {
                lastError = err;
            }
        }

        if (lastResponse) return lastResponse;
        throw lastError || new Error('Unable to reach API backend');
    }

    function setVoiceStatus(fieldId, message) {
        const status = document.getElementById('voice-status-shared') || document.getElementById(`voice-status-${fieldId}`);
        if (status) status.textContent = message;
    }

    function setVoiceButtonState(isRecording) {
        const btn = document.getElementById('voice-toggle-btn');
        if (!btn) return;
        btn.classList.toggle('recording', !!isRecording);
        btn.setAttribute('aria-label', isRecording ? 'Stop microphone' : 'Start microphone');
    }

    function getVoiceTargetField() {
        const sel = document.getElementById('voice-target');
        return sel ? sel.value : 'issue-summary';
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
        const target = document.getElementById(fieldId);
        const baseText = target ? target.value.trim() : '';
        const mergeWithBase = (spokenText) => {
            if (!target) return;
            const chunk = (spokenText || '').trim();
            target.value = [baseText, chunk].filter(Boolean).join(baseText ? '\n' : '');
        };
        const recogLang = 'en-US';

        recognition = new Ctor();
        recognition.lang = recogLang;
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;

        recognition.onstart = () => {
            setVoiceButtonState(true);
            setVoiceStatus(fieldId, 'Listening... transcribing in real time.');
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
            const liveText = `${capturedFinalText} ${interim}`.trim();
            mergeWithBase(liveText);
            if (interim.trim()) {
                setVoiceStatus(fieldId, `Listening... ${interim.trim()}`);
            }
        };

        recognition.onerror = (event) => {
            setVoiceButtonState(false);
            setVoiceStatus(fieldId, `Mic error: ${event.error || 'unknown error'}`);
        };

        recognition.onend = () => {
            const transcript = capturedFinalText.trim();
            setVoiceButtonState(false);
            if (!transcript) {
                mergeWithBase('');
                setVoiceStatus(fieldId, 'Stopped. No speech detected.');
                recognition = null;
                recognitionField = null;
                capturedFinalText = '';
                return;
            }

            mergeWithBase(transcript);
            setVoiceStatus(fieldId, 'Done.');
            recognition = null;
            recognitionField = null;
            capturedFinalText = '';
        };

        recognition.start();
    }

    function stopVoiceInput(fieldId) {
        if (recognition && recognitionField === fieldId) {
            recognition.stop();
            setVoiceButtonState(false);
            setVoiceStatus(fieldId, 'Stopping...');
        }
    }

    function toggleVoiceInput() {
        const fieldId = getVoiceTargetField();
        if (recognition && recognitionField === fieldId) {
            stopVoiceInput(fieldId);
        } else {
            startVoiceInput(fieldId);
        }
    }

    function saveApiBase() {
        // no-op kept for backwards compat
    }

    // ── File Upload Handling ────────────────────────────────────────
    function handleDragOver(e) {
        e.preventDefault();
        e.currentTarget.classList.add('drag-over');
    }
    function handleDragLeave(e) {
        e.currentTarget.classList.remove('drag-over');
    }
    function handleDrop(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length) uploadFiles(files);
    }
    function handleFileSelect(e) {
        const files = e.target.files;
        if (files.length) uploadFiles(files);
        e.target.value = '';  // reset so same file can be re-selected
    }

    async function uploadFiles(fileList) {
        const statusEl = document.getElementById('upload-status');
        const maxFiles = 10;
        const maxSize = 10 * 1024 * 1024;
        const allowed = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'application/pdf'];

        const toUpload = [];
        for (const f of fileList) {
            if (state.uploadedFiles.length + toUpload.length >= maxFiles) {
                if (statusEl) statusEl.textContent = `Maximum ${maxFiles} files allowed.`;
                break;
            }
            if (!allowed.includes(f.type)) {
                if (statusEl) statusEl.textContent = `${f.name}: unsupported type. Use JPEG, PNG, WebP, GIF, or PDF.`;
                continue;
            }
            if (f.size > maxSize) {
                if (statusEl) statusEl.textContent = `${f.name}: exceeds 10 MB limit.`;
                continue;
            }
            toUpload.push(f);
        }

        if (!toUpload.length) return;

        // Show pending items
        const pendingIds = [];
        for (const f of toUpload) {
            const tempId = `pending-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
            pendingIds.push(tempId);
            state.uploadedFiles.push({
                file_id: tempId,
                filename: f.name,
                content_type: f.type,
                size: f.size,
                status: 'uploading',
                thumbUrl: f.type.startsWith('image/') ? URL.createObjectURL(f) : null,
            });
        }
        renderUploadedFiles();

        try {
            const formData = new FormData();
            for (const f of toUpload) formData.append('files', f);

            if (statusEl) statusEl.textContent = `Uploading ${toUpload.length} file(s)...`;
            const res = await apiFetch('/documents/upload', { method: 'POST', body: formData });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `Upload failed: ${res.status}`);
            }
            const data = await res.json().catch(() => null);
            if (!data || !Array.isArray(data.files)) {
                throw new Error('Upload failed: invalid server response format.');
            }

            // Replace pending entries with server responses
            const completedCount = Math.min(data.files.length, pendingIds.length);
            for (let i = 0; i < completedCount; i++) {
                const srvFile = data.files[i];
                const pendingIdx = state.uploadedFiles.findIndex(f => f.file_id === pendingIds[i]);
                if (pendingIdx >= 0) {
                    const thumbUrl = state.uploadedFiles[pendingIdx].thumbUrl;
                    state.uploadedFiles[pendingIdx] = {
                        ...srvFile,
                        status: 'done',
                        thumbUrl,
                    };
                }
            }
            if (data.files.length !== pendingIds.length) {
                for (let i = completedCount; i < pendingIds.length; i++) {
                    const idx = state.uploadedFiles.findIndex(f => f.file_id === pendingIds[i]);
                    if (idx >= 0) state.uploadedFiles[idx].status = 'error';
                }
            }

            if (statusEl) {
                statusEl.textContent = data.files.length === pendingIds.length
                    ? `${data.files.length} file(s) uploaded successfully.`
                    : `${completedCount} of ${pendingIds.length} file(s) uploaded. Please retry failed uploads.`;
            }
        } catch (err) {
            // Mark pending as error
            for (const tid of pendingIds) {
                const idx = state.uploadedFiles.findIndex(f => f.file_id === tid);
                if (idx >= 0) state.uploadedFiles[idx].status = 'error';
            }
            if (statusEl) statusEl.textContent = `Upload error: ${err.message}`;
        }
        renderUploadedFiles();
    }

    async function removeUploadedFile(fileId) {
        const idx = state.uploadedFiles.findIndex(f => f.file_id === fileId);
        if (idx < 0) return;
        const file = state.uploadedFiles[idx];
        // Release object URL if any
        if (file.thumbUrl) URL.revokeObjectURL(file.thumbUrl);
        state.uploadedFiles.splice(idx, 1);
        renderUploadedFiles();
        // Delete from server if it was successfully uploaded
        if (file.status === 'done') {
            try { await apiFetch(`/documents/${fileId}`, { method: 'DELETE' }); } catch (_) {}
        }
    }

    function renderUploadedFiles() {
        const container = document.getElementById('upload-file-list');
        if (!container) return;
        container.innerHTML = state.uploadedFiles.map(f => {
            const sizeStr = f.size < 1024 ? `${f.size} B`
                : f.size < 1024 * 1024 ? `${(f.size / 1024).toFixed(1)} KB`
                : `${(f.size / (1024 * 1024)).toFixed(1)} MB`;
            const statusCls = f.status || 'done';
            const statusText = statusCls === 'uploading' ? 'Uploading...'
                : statusCls === 'error' ? 'Failed' : '✓';
            const thumb = f.thumbUrl
                ? `<img class="file-thumb" src="${f.thumbUrl}" alt="">`
                : `<div class="file-thumb">${f.content_type === 'application/pdf' ? '📄' : '📎'}</div>`;
            return `<div class="upload-file-item">
                ${thumb}
                <div class="file-info">
                    <div class="file-name">${esc(f.filename)}</div>
                    <div class="file-size">${sizeStr}</div>
                </div>
                <span class="file-status ${statusCls}">${statusText}</span>
                <button type="button" onclick="App.removeUploadedFile('${esc(f.file_id)}')" title="Remove">✕</button>
            </div>`;
        }).join('');
    }

    function getCustomerControls() {
        const tone = document.getElementById('ctrl-tone')?.value || '';
        const cure = document.getElementById('ctrl-cure')?.value || '';
        const comp = document.getElementById('ctrl-compensation')?.value || '';
        const interest = document.getElementById('ctrl-interest')?.value || '';
        return {
            notice_tone: tone || null,
            cure_period_days: cure ? parseInt(cure) : null,
            compensation_amount: comp ? parseInt(comp) : null,
            interest_rate_percent: interest ? parseFloat(interest) : null,
            language: 'English',
        };
    }

    function getUploadIds() {
        return state.uploadedFiles
            .filter(f => f.status === 'done')
            .map(f => f.file_id);
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

    // ── Step 2 → 3: Company ─────────────────────────────────────────
    let _lookupAbort = null;

    async function lookupCompany() {
        const name = val('company-name');
        const website = normalizeWebsite(val('company-website'));
        const resultEl = document.getElementById('company-lookup-result');
        const loadingEl = document.getElementById('company-lookup-loading');
        if (!resultEl || !loadingEl) return;

        resultEl.classList.add('hidden');
        if (!website || !name) return;

        if (_lookupAbort) _lookupAbort.abort();
        _lookupAbort = new AbortController();

        loadingEl.classList.remove('hidden');

        try {
            const res = await apiFetch('/company/lookup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ brand_name: name, website }),
                signal: _lookupAbort.signal,
            });
            loadingEl.classList.add('hidden');

            const data = typeof res.json === 'function' ? await res.json() : res;
            const hasData = data.registered_name || data.cin || data.registered_office || data.grievance_officer_email;
            if (!hasData) return;

            const escHtml = s => {
                const d = document.createElement('div');
                d.textContent = s;
                return d.innerHTML;
            };
            const setRow = (id, label, value) => {
                const el = document.getElementById(id);
                if (!el) return;
                if (value) {
                    el.innerHTML = '<strong>' + escHtml(label) + '</strong><span>' + escHtml(value) + '</span>';
                    el.style.display = '';
                } else {
                    el.style.display = 'none';
                }
            };
            setRow('lookup-registered-name', 'Legal Name', data.registered_name);
            setRow('lookup-cin', 'CIN', data.cin);
            setRow('lookup-office', 'Registered Office', data.registered_office);
            const grievance = [data.grievance_officer_name, data.grievance_officer_email].filter(Boolean).join(' — ');
            setRow('lookup-grievance', 'Grievance Officer', grievance || null);
            resultEl.classList.remove('hidden');
        } catch (e) {
            loadingEl.classList.add('hidden');
            if (e.name !== 'AbortError') console.warn('Company lookup failed:', e);
        }
    }

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

    function getAnalyzeComplainant() {
        const c = state.complainant || {};
        return {
            full_name: c.full_name || 'Pending Customer',
            email: c.email || 'pending@lawly.store',
            phone: c.phone || null,
            address: c.address || 'India',
        };
    }

    // ── Step 3 → 4: Analyze ─────────────────────────────────────────
    let _analyzeInFlight = false;
    async function analyzeCase() {
        if (_analyzeInFlight) return; // prevent double-submit
        const summary = val('issue-summary');
        const resolution = val('desired-resolution');
        const objection = val('company-objection');
        if (!summary || summary.length < 20) return showError('Please describe your issue in at least 20 characters.');
        if (!resolution || resolution.length < 5) return showError('Please describe what resolution you want in at least 5 characters (e.g., "Full refund").');
        if (summary.length > 10000) return showError('Issue summary is too long (max 10,000 characters).');
        if (resolution.length > 2000) return showError('Desired resolution is too long (max 2,000 characters).');
        if (objection && objection.length > 5000) return showError('Company objection is too long (max 5,000 characters).');

        _analyzeInFlight = true;
        state.issueSummary = summary;
        state.desiredResolution = resolution;
        state.companyObjection = objection || '';

        goTo(4); // show loading
        animateStages(['stage-company', 'stage-contacts', 'stage-policies', 'stage-legal', 'stage-strength'], 6000);

        const body = {
            complainant: getAnalyzeComplainant(),
            issue_summary: state.issueSummary,
            desired_resolution: state.desiredResolution,
            company_objection: state.companyObjection || null,
            company_name_hint: state.companyName,
            website: state.companyWebsite,
            timeline: state.timeline,
            evidence: state.evidence,
            previous_answers: Object.keys(state.followUpAnswers).length > 0 ? state.followUpAnswers : null,
            upload_ids: getUploadIds(),
        };

        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 180000); // 3 min

        try {
            const res = await apiFetch('/notice/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                signal: controller.signal,
            });
            clearTimeout(timeout);
            if (!res.ok) {
                const msg = await responseErrorMessage(res, `Analyze failed (${res.status})`);
                throw new Error(msg);
            }
            state.analysisResult = await res.json();
            renderAnalysis();
            goTo(5);
        } catch (err) {
            clearTimeout(timeout);
            goTo(3);
            if (err?.name === 'AbortError') {
                showError('Analysis timed out — the server is under heavy load. Please try again.');
            } else {
                const msg = err?.message || '';
                if (/expected pattern|unexpected token|timeout|504|502/i.test(msg)) {
                    showError('Analysis is taking longer than expected. Our servers are processing complex legal research — please try again in a moment.');
                } else {
                    showError(msg || 'Could not analyze your case right now. Please try again.');
                }
            }
        } finally {
            _analyzeInFlight = false;
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
        items.push(vpItem('Statutory Arguments', 'Legal sections from 15+ Indian acts'));
        items.push(vpItem('Defense Counter-Arguments', 'Pre-emptive rebuttals to company T&Cs'));
        items.push(vpItem('Escalation Strategy', 'Sector regulators & pressure tactics'));
        if (a?.respondent_cin) items.push(vpItem('Company Identity', `CIN: ${a.respondent_cin}`));
        if (sectionCount > 0) items.push(vpItem('Policy Analysis', `${sectionCount} pages of T&Cs analyzed`));
        if (a?.contacts_found?.length > 0) items.push(vpItem('Contact Details', `${a.contacts_found.length} contacts auto-discovered`));
        items.push(vpItem('Court-Ready PDF', 'Formatted for consumer commission filing'));
        items.push(vpItem('Cure Period', 'Statutory deadline for company response'));

        grid.innerHTML = items.join('');
    }

    function vpItem(title, desc) {
        return `<div class="vp-item"><strong>${esc(title)}</strong><span>${esc(desc)}</span></div>`;
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

        // Keep users in control: they should be able to change tier after selecting.
        const backBtn = document.getElementById('tier-back-btn');
        if (backBtn) backBtn.style.display = '';

        const panel = document.getElementById('final-details-panel');
        if (panel) {
            panel.style.display = 'block';

            const c = state.complainant || {};
            const fdName = document.getElementById('fd-name');
            const fdEmail = document.getElementById('fd-email');
            const fdPhone = document.getElementById('fd-phone');
            const fdAddress = document.getElementById('fd-address');
            if (fdName && !fdName.value && c.full_name) fdName.value = c.full_name;
            if (fdEmail && !fdEmail.value && c.email) fdEmail.value = c.email;
            if (fdPhone && !fdPhone.value && c.phone) fdPhone.value = c.phone;
            if (fdAddress && !fdAddress.value && c.address) fdAddress.value = c.address;

            panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    function resetTierSelection() {
        const selfCard = document.getElementById('tier-self');
        const lawyerCard = document.getElementById('tier-lawyer');
        if (selfCard) selfCard.classList.remove('selected');
        if (lawyerCard) lawyerCard.classList.remove('selected');

        const panel = document.getElementById('final-details-panel');
        if (panel) panel.style.display = 'none';

        const backBtn = document.getElementById('tier-back-btn');
        if (backBtn) backBtn.style.display = '';
    }

    // ── Confirm Final Details ───────────────────────────────────────
    function confirmAndGenerate() {
        const name = document.getElementById('fd-name').value.trim();
        const email = document.getElementById('fd-email').value.trim();
        const phone = document.getElementById('fd-phone').value.trim();
        const address = document.getElementById('fd-address').value.trim();

        if (!name || !email || !address) {
            return showError('Please fill in all required fields (Name, Email, Address).');
        }

        // Anti-Spam: Block obvious fake names
        const blockedNames = ['test', 'john doe', 'jane doe', 'asdf', 'demo', 'abc', 'abcd', '123', 'fake', 'anonymous', 'user', 'something'];
        if (blockedNames.includes(name.toLowerCase()) || name.length < 4 || /^[a-zA-Z]$/.test(name) || /test/i.test(name)) {
            return showError('Please enter a valid full name. Legal notices require your real identity.');
        }

        // Anti-Spam: Enforce valid Indian phone format if provided
        if (phone) {
            const cleanPhone = phone.replace(/[\s\-\(\)]/g, '');
            if (!/^(?:\+91|91)?[6789]\d{9}$/.test(cleanPhone)) {
                return showError('Please enter a valid 10-digit Indian mobile number.');
            }
        }

        // Anti-Spam: Ensure address is somewhat realistic
        if (address.length < 10) {
            return showError('Please enter a complete mailing address. This is required for court formatting.');
        }

        state.complainant = {
            full_name: name,
            email: email,
            phone: phone || null,
            address: address,
        };

        if (state.tier === 'lawyer') {
            document.getElementById('payment-amt').innerHTML = '₹599';
        } else {
            document.getElementById('payment-amt').innerHTML = `
                <div style="display: flex; align-items: baseline; justify-content: center; gap: 8px;">
                    <span style="text-decoration: line-through; color: #9ca3af; font-size: 0.6em;">₹199</span>
                    <span>Free</span>
                </div>
                <div style="color: #16a34a; font-size: 0.8rem; text-transform: uppercase;">For a limited time</div>
            `;
        }
        document.getElementById('payment-desc').textContent = `Generate a ${state.tier === 'lawyer' ? 'Lawyer-Assisted' : 'Self-Send'} notice.`;
        document.getElementById('payment-overlay').style.display = 'flex';
        document.getElementById('pay-btn').style.display = 'block';
        document.getElementById('payment-status').style.display = 'none';
    }

    
    async function processPayment() {
        const btn = document.getElementById('pay-btn');
        const status = document.getElementById('payment-status');
        btn.style.display = 'none';
        status.style.display = 'block';
        
        status.style.color = '#2563eb';
        status.textContent = 'Processing via Secure Gateway...';
        
        await new Promise(r => setTimeout(r, 1500));
        
        status.style.color = '#10b981';
        status.textContent = 'Payment Successful! Redirecting...';
        
        try { trackEvent('payment', { tier: state.tier, amount: state.tier === 'lawyer' ? 599 : 199 }); } catch(_) {}
        
        await new Promise(r => setTimeout(r, 800));
        document.getElementById('payment-overlay').style.display = 'none';
        generateNotice();
    }

    // ── Step 7: Generate notice ─────────────────────────────────────
    let _generateInFlight = false;
    async function generateNotice() {
        if (_generateInFlight) return; // prevent double-submit
        _generateInFlight = true;
        goTo(7);
        animateStages(['gen-stage-1', 'gen-stage-2', 'gen-stage-3', 'gen-stage-4', 'gen-stage-5'], 8000);
        animateProgress(60000);

        const controls = getCustomerControls();
        const body = {
            complainant: state.complainant,
            issue_summary: state.issueSummary,
            desired_resolution: state.desiredResolution,
            company_objection: state.companyObjection || null,
            company_name_hint: state.companyName,
            website: state.companyWebsite,
            timeline: state.timeline,
            evidence: state.evidence,
            tier: state.tier,
            follow_up_answers: Object.keys(state.followUpAnswers).length > 0
                ? state.followUpAnswers : null,
            upload_ids: getUploadIds(),
            notice_tone: controls.notice_tone,
            cure_period_days: controls.cure_period_days,
            compensation_amount: controls.compensation_amount,
            interest_rate_percent: controls.interest_rate_percent,
            language: controls.language,
        };

        try {
            // 1. Submit job (returns immediately with job_id)
            const submitController = new AbortController();
            const submitTimeout = setTimeout(() => submitController.abort(), 30000);
            const submitRes = await apiFetch('/notice/typed', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                signal: submitController.signal,
            });
            clearTimeout(submitTimeout);
            if (!submitRes.ok) {
                const msg = await responseErrorMessage(submitRes, `Notice generation failed (${submitRes.status})`);
                throw new Error(msg);
            }
            const submitData = await submitRes.json();
            const jobId = submitData.job_id;
            const pollToken = submitData.poll_token || '';

            // If the server didn't return a job_id, it might be the old synchronous response (e.g. dev environment).
            if (!jobId) {
                state.noticeResult = submitData;
                state.noticeId = submitData.notice_id != null ? String(submitData.notice_id) : null;
                completeProgress();
                renderNotice();
                goTo(8);
                _generateInFlight = false;
                return;
            }

            // 2. Poll for completion
            const maxWaitMs = 300000; // Expanded to 5 mins
            let pollIntervalMs = 3000;
            const pollStart = Date.now();
            let networkFailures = 0;

            while (Date.now() - pollStart < maxWaitMs) {
                await new Promise(r => setTimeout(r, pollIntervalMs));
                try {
                    const pollPath = '/notice/job/' + encodeURIComponent(jobId)
                        + '?poll_token=' + encodeURIComponent(pollToken);
                    const pollRes = await apiFetch(pollPath);
                    networkFailures = 0; // reset on success

                    if (!pollRes.ok) {
                        if (pollRes.status === 404) throw new Error('Job expired or lost. Please try again.');
                        // Sub-backoff on 500 network blips
                        pollIntervalMs = Math.min(pollIntervalMs * 1.5, 10000);
                        continue; 
                    }
                    const pollData = await pollRes.json();
                    if (pollData.status === 'completed' && pollData.result) {
                        state.noticeResult = pollData.result;
                        state.noticeId = pollData.result.notice_id != null
                            ? String(pollData.result.notice_id) : null;
                        completeProgress();
                        renderNotice();
                        goTo(8);
                        _generateInFlight = false;
                        return;
                    }
                    if (pollData.status === 'failed') {
                        throw new Error(pollData.error || 'Notice generation failed on the server.');
                    }
                    // status === 'processing' → keep polling
                } catch (err) {
                    if (err.message.includes('expired or lost') || err.message.includes('failed on the server')) {
                        throw err; 
                    }
                    networkFailures++;
                    if (networkFailures > 5) {
                        throw new Error("Lost connection to processing server. Please refresh your browser or try again.");
                    }
                    pollIntervalMs = Math.min(pollIntervalMs * 1.5, 10000);
                }
            }
            throw new Error('Generation timed out. Please try again.');
        } catch (err) {
            const msg = err?.name === 'AbortError'
                ? 'Generation timed out. Please try again.'
                : (err?.message || 'Could not generate notice right now. Please try again.');
            clearInterval(_progressTimer);
            goTo(6, { resetTier: false });
            showError(msg);
            _generateInFlight = false;
        }
    }

    // ── Step 8: Render result ───────────────────────────────────────
    
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

    function renderNotice() {
        const r = state.noticeResult;
        const id = state.noticeId;

        document.getElementById('notice-id-display').textContent =
            id ? `Reference: #${id.toUpperCase()}` : '';

        // Populate the editable textarea (step 8) — this is what the customer sees
        const editor = document.getElementById('notice-text-editor');
        if (editor) editor.value = r.legal_notice || '';

        // Also populate the read-only display (step 9 final view)
        document.getElementById('notice-text').textContent = r.legal_notice || '';

        const isSelf = state.tier === 'self_send';
        document.getElementById('self-send-info').classList.toggle('hidden', !isSelf);
        document.getElementById('lawyer-send-info').classList.toggle('hidden', isSelf);

        if (!isSelf && state.complainant?.email) {
            document.getElementById('notify-email').textContent = state.complainant.email;
        }
    }

    // ── PDF download ────────────────────────────────────────────────
    async function downloadEDaakhilZip() {
        const payload = {
            company_name: state.company?.name || "Target Company",
            complainant: state.complainant || {},
            evidence_details: state.evidence.length > 0 ? state.evidence.map(e => ({ name: e.doc_type, desc: "" })) : []
        };
        try {
            const btn = document.getElementById("btn-download-edaakhil");
            if (btn) btn.innerHTML = "Packaging ZIP...";

            const res = await apiFetch('/notice/export-edaakhil', {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            if (!res.ok) throw new Error("Failed to generate ZIP");

            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "EDaakhil_Filing_Pack.zip";
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            if (btn) btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg> Download E-Daakhil ZIP';
        } catch (err) {
            console.error(err);
            showError("Could not generate ZIP: " + err.message);
        }
    }

    async function downloadPDF() {
        const noticeText = state.noticeResult?.legal_notice;
        if (!noticeText) {
            showError('No notice text available. Please generate the notice first.');
            return;
        }

        const companyName = state.companyName || 'Company';
        const isLawyer = state.tier === 'lawyer';

        try {
            const res = await apiFetch('/notice/render-pdf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    notice_text: noticeText,
                    company_name: companyName,
                    is_lawyer_tier: isLawyer,
                }),
            });
            if (!res.ok) throw new Error('PDF generation failed');
            const blob = await res.blob();
            downloadBlob(blob, `Legal_Notice_${companyName.replace(/ /g, '_')}.pdf`);
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
    let _progressTimer = null;
    function animateProgress(estimatedMs) {
        const fill = document.getElementById('gen-progress-fill');
        const pct = document.getElementById('gen-progress-pct');
        const label = document.getElementById('gen-progress-label');
        if (!fill) return;
        fill.style.width = '0%';
        if (pct) pct.textContent = '0%';
        if (label) label.textContent = 'Preparing draft\u2026';
        const labels = ['Analyzing complaint\u2026', 'Building legal arguments\u2026', 'Drafting notice\u2026', 'Finalizing\u2026'];
        let progress = 0;
        const interval = 500;
        const step = (90 / (estimatedMs / interval));
        clearInterval(_progressTimer);
        _progressTimer = setInterval(() => {
            progress = Math.min(progress + step, 92);
            fill.style.width = progress + '%';
            if (pct) pct.textContent = Math.round(progress) + '%';
            const li = Math.min(Math.floor(progress / 25), labels.length - 1);
            if (label) label.textContent = labels[li];
            if (progress >= 92) clearInterval(_progressTimer);
        }, interval);
    }
    function completeProgress() {
        clearInterval(_progressTimer);
        const fill = document.getElementById('gen-progress-fill');
        const pct = document.getElementById('gen-progress-pct');
        const label = document.getElementById('gen-progress-label');
        if (fill) fill.style.width = '100%';
        if (pct) pct.textContent = '100%';
        if (label) label.textContent = 'Done!';
    }

    function animateStages(ids, totalMs) {
        const startTime = Date.now();
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.classList.remove('active', 'done');
                const icon = el.querySelector('.stage-icon');
                if (icon) icon.textContent = '';
                const ts = el.querySelector('.stage-ts');
                if (ts) ts.textContent = '';
            }
        });
        const delay = totalMs / ids.length;
        ids.forEach((id, i) => {
            setTimeout(() => {
                const el = document.getElementById(id);
                if (el) el.classList.add('active');
                if (i > 0) {
                    const prev = document.getElementById(ids[i - 1]);
                    if (prev) {
                        prev.classList.remove('active');
                        prev.classList.add('done');
                        const icon = prev.querySelector('.stage-icon');
                        if (icon) icon.textContent = '\u2713';
                        const ts = prev.querySelector('.stage-ts');
                        if (ts) {
                            const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
                            ts.textContent = elapsed + 's';
                        }
                    }
                }
            }, delay * i);
        });
    }

    // --- Autosave logic ---
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
        state.companyObjection = '';
        state.analysisResult = null;
        state.followUpAnswers = {};
        state.tier = 'self_send';
        state.noticeResult = null;
        state.noticeId = null;
        // Release object URLs for uploaded files
        for (const f of state.uploadedFiles) {
            if (f.thumbUrl) URL.revokeObjectURL(f.thumbUrl);
        }
        state.uploadedFiles = [];
        // Clear forms
        document.querySelectorAll('input, textarea').forEach(el => el.value = '');
        document.querySelectorAll('select').forEach(el => el.selectedIndex = 0);
        document.getElementById('timeline-list').innerHTML = '';
        document.getElementById('evidence-list').innerHTML = '';
        const uploadList = document.getElementById('upload-file-list');
        if (uploadList) uploadList.innerHTML = '';
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

        // Auto-trigger company lookup when website field loses focus
        const websiteInput = document.getElementById('company-website');
        if (websiteInput) {
            let _lookupTimer = null;
            websiteInput.addEventListener('blur', () => {
                clearTimeout(_lookupTimer);
                _lookupTimer = setTimeout(() => lookupCompany(), 300);
            });
        }
    });

    
    // ── Public API ──────────────────────────────────────────────────

    return {
        finalizeNotice,
        setCategory,
        setCompany,
        setIssue,
        start, goTo, nextFromCompany, lookupCompany, analyzeCase,
        selectTier, confirmAndGenerate,
        processPayment, generateNotice, downloadEDaakhilZip, downloadPDF, renderNotice, upgradeTier,
        resetTierSelection,
        addTimeline, addEvidence, removeItem, saveAnswer,
        showError, dismissError, reset, saveApiBase,
        startVoiceInput, stopVoiceInput, toggleVoiceInput,
        handleDragOver, handleDragLeave, handleDrop, handleFileSelect,
        removeUploadedFile,
    };
})();
