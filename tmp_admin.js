const Admin = (() => {
    /* ── State ──────────────────────────────────────────── */
    let token = sessionStorage.getItem('admin_token') || null;
    let currentNoticeId = null;
    let editingSlug = null;   // blog
    let editingPage = null;   // page
    let quill = null;         // Quill editor instance
    let lineChart = null;     // Chart.js instances
    let doughnutChart = null;
    let noticesCache = [];    // for CSV export + filtering

    const API_BACKEND = 'https://api.lawly.store';

    /* ── Helpers ────────────────────────────────────────── */
    function isLocal() { return ['localhost','127.0.0.1'].includes(location.hostname); }

    function apiBase() {
        const saved = (localStorage.getItem('legaltech_api_base') || '').trim();
        return saved || (isLocal() ? location.origin : API_BACKEND);
    }

    function esc(s) {
        if (!s) return '';
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML.replace(/'/g, '&#39;').replace(/"/g, '&quot;');
    }
    function qs(sel) { return document.querySelector(sel); }
    function formatDate(iso) { return iso ? new Date(iso).toLocaleDateString('en-IN', {year:'numeric',month:'short',day:'numeric'}) : '—'; }

    /* ── Toast notifications ────────────────────────────── */
    function showToast(message, type = 'info') {
        const container = qs('#toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.animation = 'toastOut .3s ease-in forwards';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    /* ── API fetch wrapper ──────────────────────────────── */
    async function apiFetch(path, opts = {}) {
        const url = `${apiBase().replace(/\/$/,'')}${path}`;
        const headers = { ...(opts.headers || {}) };
        if (token) headers['Authorization'] = `Bearer ${token}`;
        if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof Blob)) {
            headers['Content-Type'] = 'application/json';
            opts.body = JSON.stringify(opts.body);
        }
        const res = await fetch(url, { ...opts, headers });
        if (res.status === 401) { logout(); throw new Error('Session expired'); }
        return res;
    }

    /* ── AI Helper ─────────────────────────────────────── */
    async function aiGenerate(tool, context, btn) {
        if (btn) { btn.classList.add('loading'); btn.disabled = true; }
        try {
            const res = await apiFetch('/api/admin/ai/generate', {
                method: 'POST',
                body: JSON.stringify({ tool, context }),
            });
            const data = await res.json();
            if (!res.ok) { showToast(data.detail || 'AI generation failed', 'error'); return null; }
            showToast('AI content generated!', 'success');
            return data.result;
        } catch (err) {
            showToast('AI generation failed: ' + err.message, 'error');
            return null;
        } finally {
            if (btn) { btn.classList.remove('loading'); btn.disabled = false; }
        }
    }

    /* ── Auth ───────────────────────────────────────────── */
    async function login(e) {
        e.preventDefault();
        const pw = qs('#login-pw').value;
        const errEl = qs('#login-error');
        errEl.classList.add('hidden');
        try {
            const res = await fetch(`${apiBase().replace(/\/$/,'')}/api/admin/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: pw }),
            });
            if (!res.ok) { errEl.textContent = 'Invalid password'; errEl.classList.remove('hidden'); return; }
            const data = await res.json();
            token = data.token;
            sessionStorage.setItem('admin_token', token);
            showAdmin();
        } catch (err) {
            errEl.textContent = 'Connection failed'; errEl.classList.remove('hidden');
        }
    }

    function logout() {
        token = null;
        sessionStorage.removeItem('admin_token');
        qs('#admin-panel').classList.add('hidden');
        qs('#login-screen').classList.remove('hidden');
        qs('#login-pw').value = '';
    }

    async function showAdmin() {
        qs('#login-screen').classList.add('hidden');
        qs('#admin-panel').classList.remove('hidden');
        loadDashboard();
    }

    /* ── Tabs ───────────────────────────────────────────── */
    function switchTab(tabName) {
        document.querySelectorAll('.admin-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tabName));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === `tab-${tabName}`));
        const loaders = {
            dashboard: loadDashboard,
            notices: loadNotices,
            blog: loadBlog,
            pages: loadPages,
            seo: loadSEO,
            aeo: loadAEO,
            email: loadEmail,
            analytics: loadAnalytics,
            insights: loadInsights,
            support: loadSupport,
            activity: loadActivity,
            lawyer: loadLawyer,
            settings: loadSettings,
            database: loadDatabase,
            versions: loadVersions,
        };
        if (loaders[tabName]) loaders[tabName]();
    }

    /* ── Dashboard ──────────────────────────────────────── */
    async function loadDashboard() {
        try {
            const [statsRes, actRes] = await Promise.all([
                apiFetch('/api/admin/stats'),
                apiFetch('/api/admin/activity?limit=10'),
            ]);
            const stats = await statsRes.json();
            const activity = await actRes.json();
            renderStats(stats);
            renderCharts(stats);
            renderDashActivity(activity);
        } catch (err) { showToast('Failed to load dashboard', 'error'); }
    }

    function renderStats(s) {
        qs('#st-total').textContent = s.total_notices;
        qs('#st-pending').textContent = s.pending;
        qs('#st-approved').textContent = s.approved;
        qs('#st-blog').textContent = `${s.published_posts}/${s.total_blog_posts}`;
    }

    function renderCharts(s) {
        if (typeof Chart === 'undefined') return;

        const dates = Object.keys(s.notices_by_date);
        const counts = Object.values(s.notices_by_date);
        if (lineChart) lineChart.destroy();
        lineChart = new Chart(qs('#chart-line'), {
            type: 'line',
            data: {
                labels: dates.length ? dates : ['No data'],
                datasets: [{
                    label: 'Notices',
                    data: counts.length ? counts : [0],
                    borderColor: '#DC2626',
                    backgroundColor: 'rgba(220,38,38,.1)',
                    fill: true, tension: 0.3,
                }]
            },
            options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
        });

        if (doughnutChart) doughnutChart.destroy();
        doughnutChart = new Chart(qs('#chart-doughnut'), {
            type: 'doughnut',
            data: {
                labels: ['₹599 Lawyer', '₹199 Self'],
                datasets: [{ data: [s.lawyer_tier, s.self_tier], backgroundColor: ['#DC2626','#F59E0B'] }]
            },
            options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
        });
    }

    function renderDashActivity(items) {
        const el = qs('#dash-activity');
        if (!items || !items.length) { el.innerHTML = '<div class="empty-state">No activity yet</div>'; return; }
        el.innerHTML = items.map(a =>
            `<div class="activity-item">
                <div class="activity-dot"></div>
                <div>
                    <div><strong>${esc(a.action)}</strong> ${esc(a.details)}</div>
                    <div class="activity-time">${formatDate(a.timestamp)}</div>
                </div>
            </div>`
        ).join('');
    }

    /* ── Notices ─────────────────────────────────────────── */
    let pdfLookup = {};  // noticeId -> true, for quick PDF availability check

    async function loadNotices() {
        try {
            const [storeRes, dbRes, pdfsRes] = await Promise.all([
                apiFetch('/api/admin/notices'),
                apiFetch('/api/admin/db/notices').catch(() => null),
                apiFetch('/api/admin/db/pdfs').catch(() => null),
            ]);
            noticesCache = await storeRes.json();
            // Build PDF lookup from DB
            pdfLookup = {};
            if (pdfsRes && pdfsRes.ok) {
                const pdfs = await pdfsRes.json();
                pdfs.forEach(p => { pdfLookup[p.notice_id] = true; });
            }
            // Merge has_pdf from DB notices into store notices
            if (dbRes && dbRes.ok) {
                const dbNotices = await dbRes.json();
                const dbMap = {};
                dbNotices.forEach(n => {
                    if (n.has_pdf) dbMap[n.id] = true;
                    // Also check by matching company + date
                    const key = (n.company_name || '').toLowerCase();
                    if (key) dbMap[key] = n;
                });
                noticesCache.forEach(n => {
                    // Check if this notice has a PDF stored in DB
                    if (pdfLookup[n.id]) { n._has_db_pdf = true; n._db_notice_id = n.id; }
                    if (n.db_notice_id && pdfLookup[n.db_notice_id]) { n._has_db_pdf = true; n._db_notice_id = n.db_notice_id; }
                });
            }
            filterNotices();
        } catch (err) {
            qs('#notices-container').innerHTML = '<div class="empty-state">Failed to load notices.</div>';
        }
    }

    function filterNotices() {
        const q = (qs('#notice-search')?.value || '').toLowerCase().trim();
        const statusFilter = qs('#notice-status-filter')?.value || '';
        let filtered = noticesCache;
        if (q) {
            filtered = filtered.filter(n =>
                (n.id || '').toLowerCase().includes(q) ||
                (n.complainant_name || '').toLowerCase().includes(q) ||
                (n.company_name || '').toLowerCase().includes(q) ||
                (n.complainant_email || '').toLowerCase().includes(q)
            );
        }
        if (statusFilter) {
            filtered = filtered.filter(n => n.status === statusFilter);
        }
        renderNotices(filtered);
    }

    function renderNotices(notices) {
        const c = qs('#notices-container');
        if (!notices || !notices.length) { c.innerHTML = '<div class="empty-state">No notices match your filters.</div>'; return; }
        const statusLabel = s => ({ pending_review: 'Pending Review', approved: 'Approved', sent: 'Sent', rejected: 'Rejected', delivered: 'Delivered' }[s] || s);
        const statusClass = s => ({ pending_review: 'pending', approved: 'approved', sent: 'sent', rejected: 'rejected', delivered: 'delivered' }[s] || 'delivered');
        const rows = notices.map(n => {
            const pdfCell = n._has_db_pdf
                ? `<button class="btn btn-primary btn-sm" onclick="event.stopPropagation(); Admin.downloadDbPdf('${esc(n._db_notice_id || n.id)}')">⬇ PDF</button>`
                : '<span style="color:var(--gray-400)">—</span>';
            return `<tr onclick="Admin.openNotice('${esc(n.id)}')">
                <td><strong>#${esc((n.id||'').toUpperCase())}</strong></td>
                <td>${esc(n.complainant_name)}</td>
                <td>${esc(n.company_name)}</td>
                <td>${esc(n.tier==='lawyer'?'₹599 Lawyer':'₹199 Self')}</td>
                <td><span class="badge ${statusClass(n.status)}">${statusLabel(n.status)}</span></td>
                <td>${formatDate(n.created_at)}</td>
                <td>${pdfCell}</td>
            </tr>`;
        }).join('');
        c.innerHTML = `<table class="data-table"><thead><tr>
            <th>ID</th><th>Complainant</th><th>Company</th><th>Tier</th><th>Status</th><th>Date</th><th>PDF</th>
        </tr></thead><tbody>${rows}</tbody></table>`;
    }

    async function openNotice(id) {
        currentNoticeId = id;
        try {
            const res = await apiFetch(`/api/admin/notices/${id}`);
            const n = await res.json();
            qs('#modal-n-title').textContent = `Notice #${id.toUpperCase()}`;
            qs('#modal-n-complainant').textContent = n.complainant_name || '';
            qs('#modal-n-company').textContent = n.company_name || '';
            qs('#modal-n-tier').textContent = n.tier === 'lawyer' ? '₹599 Lawyer-Assisted' : '₹199 Self-Send';
            qs('#modal-n-status').textContent = n.status || '';
            qs('#modal-n-email').textContent = n.complainant_email || '—';
            qs('#modal-n-date').textContent = formatDate(n.created_at);
            qs('#modal-n-notice').textContent = n.legal_notice || '';
            const isPending = n.status === 'pending_review';
            qs('#modal-btn-approve').classList.toggle('hidden', !isPending);
            qs('#modal-btn-reject').classList.toggle('hidden', !isPending);
            // Show stored PDF download button if available
            const dbNoticeId = n.db_notice_id || id;
            const hasDbPdf = pdfLookup[id] || pdfLookup[dbNoticeId];
            qs('#modal-btn-db-pdf').classList.toggle('hidden', !hasDbPdf);
            if (hasDbPdf) qs('#modal-btn-db-pdf').dataset.noticeId = dbNoticeId;
            // Try to load analysis data from DB
            const analysisEl = qs('#modal-n-analysis');
            const analysisGrid = qs('#modal-n-analysis-grid');
            analysisEl.classList.add('hidden');
            try {
                const dbRes = await apiFetch(`/api/admin/db/notices/${dbNoticeId}`);
                if (dbRes.ok) {
                    const db = await dbRes.json();
                    const fields = [
                        ['Jurisdiction', db.jurisdiction_analysis],
                        ['Claim Elements', db.claim_elements],
                        ['Arbitration', db.arbitration_analysis],
                        ['Evidence Scoring', db.evidence_scoring],
                        ['Gap Analysis', db.gap_analysis],
                        ['Cure Period', db.cure_period],
                        ['Escalation', db.escalation_roadmap],
                        ['Respondent ID', db.respondent_id],
                        ['T&C Counter', db.tc_counter_args],
                        ['Legal Analysis', db.legal_analysis],
                    ];
                    const hasAny = fields.some(([, v]) => v);
                    if (hasAny) {
                        analysisGrid.innerHTML = fields.map(([k, v]) =>
                            `<div class="modal-card"><h4>${k}</h4><p>${v ? '✅ Available' : '—'}</p></div>`
                        ).join('');
                        analysisEl.classList.remove('hidden');
                    }
                }
            } catch (_) { /* DB detail not available, that's fine */ }
            qs('#notice-modal').classList.remove('hidden');
        } catch (err) { showToast('Failed to load notice', 'error'); }
    }

    function closeNoticeModal() { qs('#notice-modal').classList.add('hidden'); currentNoticeId = null; }

    async function approveNotice() {
        if (!currentNoticeId) return;
        try {
            await apiFetch(`/api/admin/notices/${currentNoticeId}/status`, { method: 'PUT', body: { status: 'approved', reviewer_notes: 'Approved by admin' } });
            showToast('Notice approved', 'success');
            closeNoticeModal();
            loadNotices();
        } catch (err) { showToast('Failed to approve notice', 'error'); }
    }

    async function rejectNotice() {
        if (!currentNoticeId) return;
        const reason = prompt('Rejection reason (optional):') || '';
        try {
            await apiFetch(`/api/admin/notices/${currentNoticeId}/status`, { method: 'PUT', body: { status: 'rejected', reviewer_notes: reason } });
            showToast('Notice rejected', 'success');
            closeNoticeModal();
            loadNotices();
        } catch (err) { showToast('Failed to reject notice', 'error'); }
    }

    async function downloadPDF() {
        if (!currentNoticeId) return;
        try {
            const res = await apiFetch(`/api/admin/notices/${currentNoticeId}/pdf`);
            if (!res.ok) throw new Error('PDF failed');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = `Legal_Notice_${currentNoticeId}.pdf`;
            document.body.appendChild(a); a.click(); document.body.removeChild(a);
            URL.revokeObjectURL(url);
            showToast('PDF downloaded', 'success');
        } catch (err) { showToast('PDF download failed', 'error'); }
    }

    function exportCSV() {
        if (!noticesCache.length) { showToast('No notices to export', 'info'); return; }
        const headers = ['ID','Complainant','Email','Company','Tier','Status','Created'];
        const rows = noticesCache.map(n => [
            n.id, n.complainant_name, n.complainant_email, n.company_name,
            n.tier === 'lawyer' ? 'Lawyer ₹599' : 'Self ₹199',
            n.status, (n.created_at || '').slice(0, 10)
        ]);
        const csv = [headers, ...rows].map(r => r.map(c => `"${String(c||'').replace(/"/g,'""')}"`).join(',')).join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = 'notices_export.csv';
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast('CSV exported', 'success');
    }

    /* ── Blog ────────────────────────────────────────────── */
    async function loadBlog() {
        try {
            const res = await apiFetch('/api/admin/blog');
            const posts = await res.json();
            renderBlog(posts);
        } catch (err) {
            qs('#blog-list').innerHTML = '<div class="empty-state">Failed to load blog posts.</div>';
        }
    }

    function renderBlog(posts) {
        const el = qs('#blog-list');
        if (!posts || !posts.length) { el.innerHTML = '<div class="empty-state">No blog posts yet.</div>'; return; }
        el.innerHTML = `<table class="data-table"><thead><tr>
            <th>Title</th><th>Status</th><th>Updated</th><th>Actions</th>
        </tr></thead><tbody>${posts.map(p =>
            `<tr>
                <td><strong>${esc(p.title)}</strong><br><small style="color:var(--gray-400)">/${esc(p.slug)}</small></td>
                <td><span class="badge ${p.status==='published'?'published':'draft'}">${esc(p.status)}</span></td>
                <td>${formatDate(p.updated_at)}</td>
                <td style="white-space:nowrap" onclick="event.stopPropagation()">
                    <button class="btn btn-ghost btn-sm" onclick="Admin.editBlog('${esc(p.slug)}')">✏️</button>
                    <button class="btn btn-ghost btn-sm" onclick="Admin.deleteBlog('${esc(p.slug)}')" style="color:var(--primary)">🗑</button>
                    ${p.status==='published'?`<a class="btn btn-ghost btn-sm" href="/blog/${esc(p.slug)}" target="_blank">👁</a>`:''}
                </td>
            </tr>`
        ).join('')}</tbody></table>`;
    }

    function initQuill() {
        if (quill) return;
        quill = new Quill('#blog-editor', {
            theme: 'snow',
            modules: {
                toolbar: [
                    [{ header: [1, 2, 3, false] }],
                    ['bold', 'italic', 'underline', 'strike'],
                    [{ list: 'ordered' }, { list: 'bullet' }],
                    ['blockquote', 'code-block'],
                    ['link', 'image'],
                    [{ align: [] }],
                    ['clean'],
                ],
            },
            placeholder: 'Write your blog post here...',
        });
    }

    function openBlogEditor(slug) {
        editingSlug = slug || null;
        qs('#blog-modal-title').textContent = slug ? 'Edit Blog Post' : 'New Blog Post';
        qs('#b-title').value = '';
        qs('#b-slug').value = '';
        qs('#b-meta-desc').value = '';
        qs('#b-meta-kw').value = '';
        qs('#b-author').value = 'Jago Grahak Jago';
        qs('#b-status').value = 'draft';
        qs('#blog-modal').classList.remove('hidden');
        initQuill();
        quill.root.innerHTML = '';
        if (slug) loadBlogPost(slug);
    }

    async function loadBlogPost(slug) {
        try {
            const res = await apiFetch(`/api/admin/blog/${slug}`);
            const p = await res.json();
            qs('#b-title').value = p.title || '';
            qs('#b-slug').value = p.slug || '';
            qs('#b-meta-desc').value = p.meta_description || '';
            qs('#b-meta-kw').value = p.meta_keywords || '';
            qs('#b-author').value = p.author || 'Jago Grahak Jago';
            qs('#b-status').value = p.status || 'draft';
            quill.root.innerHTML = p.content || '';
        } catch (err) { showToast('Failed to load blog post', 'error'); }
    }

    function editBlog(slug) { openBlogEditor(slug); }

    function closeBlogModal() { qs('#blog-modal').classList.add('hidden'); editingSlug = null; }

    async function saveBlog() {
        const title = qs('#b-title').value.trim();
        if (!title) { showToast('Title is required', 'error'); return; }
        const body = {
            title,
            slug: qs('#b-slug').value.trim() || null,
            content: quill.root.innerHTML,
            meta_description: qs('#b-meta-desc').value.trim(),
            meta_keywords: qs('#b-meta-kw').value.trim(),
            author: qs('#b-author').value.trim(),
            status: qs('#b-status').value,
        };
        try {
            const method = editingSlug ? 'PUT' : 'POST';
            const path = editingSlug ? `/api/admin/blog/${editingSlug}` : '/api/admin/blog';
            const res = await apiFetch(path, { method, body });
            if (res.ok) {
                showToast(editingSlug ? 'Blog post updated' : 'Blog post created', 'success');
                closeBlogModal(); loadBlog();
            } else {
                const err = await res.json().catch(() => ({}));
                showToast(err.detail || 'Save failed', 'error');
            }
        } catch (err) { showToast('Failed to save blog post', 'error'); }
    }

    async function deleteBlog(slug) {
        if (!confirm(`Delete blog post "${slug}"?`)) return;
        try {
            await apiFetch(`/api/admin/blog/${slug}`, { method: 'DELETE' });
            showToast('Blog post deleted', 'success');
            loadBlog();
        } catch (err) { showToast('Failed to delete', 'error'); }
    }

    /* ── Pages ───────────────────────────────────────────── */
    async function loadPages() {
        try {
            const res = await apiFetch('/api/admin/pages');
            const pages = await res.json();
            renderPages(pages);
        } catch (err) {
            qs('#pages-list').innerHTML = '<div class="empty-state">Failed to load.</div>';
        }
    }

    function renderPages(pages) {
        const el = qs('#pages-list');
        if (!pages || !pages.length) { el.innerHTML = '<div class="empty-state">No pages yet.</div>'; return; }
        el.innerHTML = `<table class="data-table"><thead><tr>
            <th>Path</th><th>Title</th><th>Priority</th><th>Sitemap</th><th>Actions</th>
        </tr></thead><tbody>${pages.map(p =>
            `<tr>
                <td><strong>${esc(p.path)}</strong></td>
                <td>${esc(p.title)}</td>
                <td>${p.priority}</td>
                <td>${p.include_in_sitemap?'✅':'—'}</td>
                <td style="white-space:nowrap" onclick="event.stopPropagation()">
                    <button class="btn btn-ghost btn-sm" onclick="Admin.editPage('${esc(p.path)}')">✏️</button>
                    <button class="btn btn-ghost btn-sm" onclick="Admin.deletePage('${esc(p.path)}')" style="color:var(--primary)">🗑</button>
                </td>
            </tr>`
        ).join('')}</tbody></table>`;
    }

    function openPageEditor(path) {
        editingPage = path || null;
        qs('#page-modal-title').textContent = path ? 'Edit Page' : 'Add Page';
        qs('#pg-path').value = '';
        qs('#pg-title').value = '';
        qs('#pg-desc').value = '';
        qs('#pg-keywords').value = '';
        qs('#pg-og-title').value = '';
        qs('#pg-og-desc').value = '';
        qs('#pg-priority').value = '0.5';
        qs('#pg-freq').value = 'weekly';
        qs('#pg-sitemap').checked = true;
        if (path) loadPageData(path);
        qs('#page-modal').classList.remove('hidden');
    }

    async function loadPageData(path) {
        try {
            const res = await apiFetch('/api/admin/pages');
            const pages = await res.json();
            const p = pages.find(pg => pg.path === path);
            if (!p) return;
            qs('#pg-path').value = p.path || '';
            qs('#pg-title').value = p.title || '';
            qs('#pg-desc').value = p.meta_description || '';
            qs('#pg-keywords').value = p.meta_keywords || '';
            qs('#pg-og-title').value = p.og_title || '';
            qs('#pg-og-desc').value = p.og_description || '';
            qs('#pg-priority').value = p.priority || 0.5;
            qs('#pg-freq').value = p.changefreq || 'weekly';
            qs('#pg-sitemap').checked = p.include_in_sitemap !== false;
        } catch (err) { showToast('Failed to load page data', 'error'); }
    }

    function editPage(path) { openPageEditor(path); }
    function closePageModal() { qs('#page-modal').classList.add('hidden'); editingPage = null; }

    async function savePage() {
        const path = qs('#pg-path').value.trim();
        if (!path) { showToast('Path is required', 'error'); return; }
        const body = {
            path,
            title: qs('#pg-title').value.trim(),
            meta_description: qs('#pg-desc').value.trim(),
            meta_keywords: qs('#pg-keywords').value.trim(),
            og_title: qs('#pg-og-title').value.trim(),
            og_description: qs('#pg-og-desc').value.trim(),
            priority: parseFloat(qs('#pg-priority').value) || 0.5,
            changefreq: qs('#pg-freq').value,
            include_in_sitemap: qs('#pg-sitemap').checked,
        };
        try {
            const method = editingPage ? 'PUT' : 'POST';
            const apiPath = editingPage ? `/api/admin/pages${editingPage}` : '/api/admin/pages';
            const res = await apiFetch(apiPath, { method, body });
            if (res.ok) {
                showToast(editingPage ? 'Page updated' : 'Page created', 'success');
                closePageModal(); loadPages();
            } else showToast('Save failed', 'error');
        } catch (err) { showToast('Failed to save page', 'error'); }
    }

    async function deletePage(path) {
        if (!confirm(`Delete page "${path}"?`)) return;
        try {
            await apiFetch(`/api/admin/pages${path}`, { method: 'DELETE' });
            showToast('Page deleted', 'success');
            loadPages();
        } catch (err) { showToast('Failed to delete', 'error'); }
    }

    /* ── SEO ─────────────────────────────────────────────── */
    async function loadSEO() {
        try {
            const res = await apiFetch('/api/admin/seo');
            const d = await res.json();
            qs('#seo-title').value = d.site_title || '';
            qs('#seo-desc').value = d.meta_description || '';
            qs('#seo-keywords').value = d.meta_keywords || '';
            qs('#seo-og-title').value = d.og_title || '';
            qs('#seo-og-desc').value = d.og_description || '';
            qs('#seo-canonical').value = d.canonical_url || '';
            qs('#seo-ga').value = d.google_analytics_id || '';
            qs('#seo-gsc').value = d.google_search_console_verification || '';
            qs('#seo-custom-head').value = d.custom_head_tags || '';
            qs('#seo-og-image').value = d.og_image || '';
            qs('#seo-bing').value = d.bing_verification || '';
            qs('#seo-robots').value = d.default_robots || 'index, follow';
            renderFaqEntries(d.faq_schema || []);
            renderHreflangEntries(d.hreflang_entries || []);
            updateSEOPreview();
            loadSEOAudit();
            loadRedirects();
        } catch (err) { showToast('Failed to load SEO settings', 'error'); }
    }

    async function saveSEO() {
        const body = {
            site_title: qs('#seo-title').value.trim(),
            meta_description: qs('#seo-desc').value.trim(),
            meta_keywords: qs('#seo-keywords').value.trim(),
            og_title: qs('#seo-og-title').value.trim(),
            og_description: qs('#seo-og-desc').value.trim(),
            canonical_url: qs('#seo-canonical').value.trim(),
            google_analytics_id: qs('#seo-ga').value.trim(),
            google_search_console_verification: qs('#seo-gsc').value.trim(),
            custom_head_tags: qs('#seo-custom-head').value.trim(),
            og_image: qs('#seo-og-image').value.trim(),
            bing_verification: qs('#seo-bing').value.trim(),
            default_robots: qs('#seo-robots').value,
            faq_schema: collectFaqEntries(),
            hreflang_entries: collectHreflangEntries(),
        };
        try {
            const res = await apiFetch('/api/admin/seo', { method: 'PUT', body });
            if (res.ok) { showToast('SEO settings saved', 'success'); loadSEOAudit(); }
            else showToast('Failed to save SEO settings', 'error');
        } catch (err) { showToast('Failed to save SEO settings', 'error'); }
    }

    function updateSEOPreview() {
        const title = qs('#seo-title').value || 'Your Site Title';
        const desc = qs('#seo-desc').value || 'Your meta description...';
        const url = qs('#seo-canonical').value || 'https://lawly.store';
        const ogTitle = qs('#seo-og-title').value || title;
        const ogDesc = qs('#seo-og-desc').value || desc;
        const ogImage = qs('#seo-og-image')?.value || '';
        const keywords = qs('#seo-keywords').value;

        qs('#serp-title').textContent = title.length > 60 ? title.slice(0, 57) + '...' : title;
        qs('#serp-url').textContent = url;
        qs('#serp-desc').textContent = desc.length > 160 ? desc.slice(0, 157) + '...' : desc;

        qs('#og-prev-title').textContent = ogTitle;
        qs('#og-prev-desc').textContent = ogDesc;

        const imgEl = qs('#og-prev-img');
        if (ogImage) {
            imgEl.innerHTML = `<img src="${esc(ogImage)}" alt="OG Preview" style="width:100%;height:100%;object-fit:cover;border-radius:8px 8px 0 0;">`;
        } else {
            imgEl.textContent = 'Image preview (set OG Image URL above)';
        }

        charCount('seo-title-count', title.length, 50, 60);
        charCount('seo-desc-count', desc.length, 120, 160);

        analyzeKeywords(keywords, title + ' ' + desc);
    }

    function charCount(elId, len, good, max) {
        const el = qs(`#${elId}`);
        const cls = len <= good ? 'char-ok' : len <= max ? 'char-warn' : 'char-over';
        el.className = `char-counter ${cls}`;
        el.textContent = `${len}/${max} characters`;
    }

    function analyzeKeywords(kwStr, content) {
        const el = qs('#keyword-analysis');
        if (!kwStr.trim()) {
            el.innerHTML = '<h4>Keyword Density</h4><p style="color:var(--gray-400);font-size:.82rem;">Add keywords above to see density analysis</p>';
            return;
        }
        const keywords = kwStr.split(',').map(k => k.trim().toLowerCase()).filter(Boolean);
        const words = content.toLowerCase().split(/\s+/).filter(Boolean);
        const totalWords = words.length || 1;
        let html = '<h4>Keyword Density</h4>';
        keywords.slice(0, 10).forEach(kw => {
            const count = words.filter(w => w.includes(kw)).length;
            const pct = ((count / totalWords) * 100).toFixed(1);
            const barW = Math.min(pct * 10, 100);
            html += `<div class="kw-bar">
                <span style="min-width:120px;color:var(--gray-600)">${esc(kw)}</span>
                <div style="flex:1;background:var(--gray-200);border-radius:3px;height:6px;overflow:hidden">
                    <div class="kw-bar-fill" style="width:${barW}%"></div>
                </div>
                <span style="min-width:40px;text-align:right;color:var(--gray-500)">${pct}%</span>
            </div>`;
        });
        el.innerHTML = html;
    }

    /* ── SEO Audit ───────────────────────────────────────── */
    async function loadSEOAudit() {
        try {
            const res = await apiFetch('/api/admin/seo/audit');
            const data = await res.json();
            renderSEOAudit(data);
        } catch (err) { console.warn('SEO audit load failed:', err); }
    }

    async function runSEOAudit() {
        const btn = qs('#btn-run-audit');
        if (btn) btn.classList.add('loading');
        const btn2 = qs('#btn-reaudit');
        if (btn2) btn2.classList.add('loading');
        try {
            const res = await apiFetch('/api/admin/seo/audit');
            const data = await res.json();
            renderSEOAudit(data);
            showToast(`SEO Audit: ${data.score}/100 (${data.grade})`, data.score >= 70 ? 'success' : 'error');
        } catch (err) {
            showToast('Failed to run SEO audit', 'error');
        } finally {
            if (btn) btn.classList.remove('loading');
            if (btn2) btn2.classList.remove('loading');
        }
    }

    function renderSEOAudit(data) {
        const scoreBox = qs('#audit-score-box');
        scoreBox.style.display = 'flex';
        qs('#btn-run-audit').style.display = 'none';

        const circle = qs('#audit-circle');
        circle.textContent = data.score;
        circle.className = `audit-circle grade-${data.grade.toLowerCase()}`;

        qs('#audit-grade-label').textContent = `Grade: ${data.grade} — ${data.score}/100`;
        const s = data.summary || {};
        qs('#audit-stats').textContent = `${s.published_posts || 0} blog posts · ${s.total_pages || 0} pages · ${s.total_redirects || 0} redirects`;

        const checksEl = qs('#audit-checks');
        checksEl.innerHTML = data.checks.map(c =>
            `<div class="audit-check ${c.passed ? 'pass' : 'fail'}">
                <span class="check-icon">${c.passed ? '✅' : '❌'}</span>
                <div style="flex:1"><strong>${esc(c.name)}</strong><div class="check-tip">${esc(c.tip)}</div></div>
            </div>`
        ).join('');
    }

    /* ── FAQ Schema Editor ───────────────────────────────── */
    let faqItems = [];

    function renderFaqEntries(items) {
        faqItems = items || [];
        const el = qs('#faq-entries');
        if (!faqItems.length) { el.innerHTML = '<p style="color:var(--gray-400);font-size:.82rem;">No FAQ items yet.</p>'; return; }
        el.innerHTML = faqItems.map((item, i) =>
            `<div class="faq-entry">
                <button class="faq-remove" onclick="Admin.removeFaqItem(${i})" title="Remove">✕</button>
                <div class="form-group" style="margin-bottom:8px;">
                    <label>Question</label>
                    <input type="text" value="${esc(item.question || '')}" onchange="Admin.updateFaqItem(${i},'question',this.value)">
                </div>
                <div class="form-group" style="margin-bottom:0;">
                    <label>Answer</label>
                    <textarea rows="2" onchange="Admin.updateFaqItem(${i},'answer',this.value)">${esc(item.answer || '')}</textarea>
                </div>
            </div>`
        ).join('');
    }

    function addFaqItem() {
        faqItems.push({ question: '', answer: '' });
        renderFaqEntries(faqItems);
    }

    function removeFaqItem(idx) {
        faqItems.splice(idx, 1);
        renderFaqEntries(faqItems);
    }

    function updateFaqItem(idx, field, value) {
        if (faqItems[idx]) faqItems[idx][field] = value;
    }

    function collectFaqEntries() {
        return faqItems.filter(f => f.question && f.answer);
    }

    /* ── Hreflang Editor ─────────────────────────────────── */
    let hreflangItems = [];

    function renderHreflangEntries(items) {
        hreflangItems = items || [];
        const el = qs('#hreflang-entries');
        if (!hreflangItems.length) { el.innerHTML = '<p style="color:var(--gray-400);font-size:.82rem;">No hreflang entries yet.</p>'; return; }
        el.innerHTML = hreflangItems.map((item, i) =>
            `<div class="hreflang-row">
                <input type="text" value="${esc(item.lang || '')}" placeholder="en-IN" onchange="Admin.updateHreflangItem(${i},'lang',this.value)">
                <input type="url" value="${esc(item.href || '')}" placeholder="https://lawly.store/" onchange="Admin.updateHreflangItem(${i},'href',this.value)">
                <button class="btn btn-outline btn-sm" onclick="Admin.removeHreflangItem(${i})" style="color:var(--primary);">✕</button>
            </div>`
        ).join('');
    }

    function addHreflangItem() {
        hreflangItems.push({ lang: '', href: '' });
        renderHreflangEntries(hreflangItems);
    }

    function removeHreflangItem(idx) {
        hreflangItems.splice(idx, 1);
        renderHreflangEntries(hreflangItems);
    }

    function updateHreflangItem(idx, field, value) {
        if (hreflangItems[idx]) hreflangItems[idx][field] = value;
    }

    function collectHreflangEntries() {
        return hreflangItems.filter(h => h.lang && h.href);
    }

    /* ── 301 Redirect Manager ────────────────────────────── */
    async function loadRedirects() {
        try {
            const res = await apiFetch('/api/admin/redirects');
            const items = await res.json();
            renderRedirects(items);
        } catch (err) {}
    }

    function renderRedirects(items) {
        const el = qs('#redirects-list');
        if (!items || !items.length) { el.innerHTML = '<p style="color:var(--gray-400);font-size:.82rem;">No redirects configured.</p>'; return; }
        el.innerHTML = items.map(r =>
            `<div class="redirect-row">
                <code style="font-size:.82rem;">${esc(r.from_path)}</code>
                <span class="arrow">→</span>
                <code style="font-size:.82rem;">${esc(r.to_path)}</code>
                <button class="btn btn-outline btn-sm" onclick="Admin.deleteRedirect('${esc(r.id)}')" style="color:var(--primary);font-size:.75rem;">Delete</button>
            </div>`
        ).join('');
    }

    async function addRedirect() {
        const from = qs('#redir-from').value.trim();
        const to = qs('#redir-to').value.trim();
        if (!from || !to) { showToast('Enter both from and to paths', 'error'); return; }
        try {
            const res = await apiFetch('/api/admin/redirects', { method: 'POST', body: { from_path: from, to_path: to, status_code: 301 } });
            if (res.ok) {
                showToast('Redirect added', 'success');
                qs('#redir-from').value = '';
                qs('#redir-to').value = '';
                loadRedirects();
            } else {
                const err = await res.json().catch(() => ({}));
                showToast(err.detail || 'Failed to add redirect', 'error');
            }
        } catch (err) { showToast('Failed to add redirect', 'error'); }
    }

    async function deleteRedirect(id) {
        try {
            const res = await apiFetch(`/api/admin/redirects/${encodeURIComponent(id)}`, { method: 'DELETE' });
            if (res.ok) { showToast('Redirect deleted', 'success'); loadRedirects(); }
            else showToast('Failed to delete redirect', 'error');
        } catch (err) { showToast('Failed to delete redirect', 'error'); }
    }

    /* ── Sitemap Ping ────────────────────────────────────── */
    async function pingSitemap() {
        const el = qs('#ping-result');
        el.textContent = 'Pinging Google & Bing...';
        try {
            const res = await apiFetch('/api/admin/seo/ping-sitemap', { method: 'POST' });
            const data = await res.json();
            const parts = Object.entries(data).map(([engine, r]) =>
                `${engine}: ${r.ok ? '✅' : '❌ ' + (r.error || 'failed')}`);
            el.textContent = parts.join(' · ');
            showToast('Sitemap pinged', 'success');
        } catch (err) {
            el.textContent = 'Ping failed';
            showToast('Failed to ping sitemap', 'error');
        }
    }

    /* ── AEO (AI Engine Optimization) ────────────────────── */
    let aeoData = {};
    let sameAsItems = [];
    let snippetItems = [];
    let howtoItems = [];
    let clusterItems = [];
    let speakableItems = [];
    let sourceItems = [];

    async function loadAEO() {
        try {
            const res = await apiFetch('/api/admin/aeo');
            aeoData = await res.json();
            qs('#aeo-llms-txt').value = aeoData.llms_txt || '';
            qs('#aeo-llms-full').value = aeoData.llms_full_txt || '';
            const org = aeoData.org_schema || {};
            qs('#org-name').value = org.name || '';
            qs('#org-url').value = org.url || '';
            qs('#org-logo').value = org.logo || '';
            qs('#org-founding').value = org.founding_date || '';
            qs('#org-desc').value = org.description || '';
            qs('#org-email').value = org.contact_email || '';
            qs('#org-phone').value = org.contact_phone || '';
            qs('#org-founders').value = org.founders || '';
            renderSameAs(org.same_as || []);
            renderSnippets(aeoData.ai_snippets || []);
            renderHowTos(aeoData.howto_schemas || []);
            renderClusters(aeoData.topic_clusters || []);
            renderSpeakable(aeoData.speakable_selectors || []);
            renderSources(aeoData.cite_sources || []);
            loadAEOAudit();
        } catch (err) { showToast('Failed to load AEO settings', 'error'); }
    }

    async function saveAEO() {
        const body = {
            llms_txt: qs('#aeo-llms-txt').value,
            llms_full_txt: qs('#aeo-llms-full').value,
            org_schema: {
                name: qs('#org-name').value.trim(),
                url: qs('#org-url').value.trim(),
                logo: qs('#org-logo').value.trim(),
                description: qs('#org-desc').value.trim(),
                founding_date: qs('#org-founding').value.trim(),
                founders: qs('#org-founders').value.trim(),
                contact_email: qs('#org-email').value.trim(),
                contact_phone: qs('#org-phone').value.trim(),
                same_as: collectSameAs(),
            },
            ai_snippets: collectSnippets(),
            howto_schemas: collectHowTos(),
            topic_clusters: collectClusters(),
            speakable_selectors: collectSpeakable(),
            cite_sources: collectSources(),
        };
        try {
            const res = await apiFetch('/api/admin/aeo', { method: 'PUT', body });
            if (res.ok) { showToast('AEO settings saved', 'success'); loadAEOAudit(); }
            else showToast('Failed to save AEO settings', 'error');
        } catch (err) { showToast('Failed to save AEO settings', 'error'); }
    }

    /* AEO Audit */
    async function loadAEOAudit() {
        try {
            const res = await apiFetch('/api/admin/aeo/audit');
            const data = await res.json();
            renderAEOAudit(data);
        } catch (err) { console.warn('AEO audit load failed:', err); }
    }

    async function runAEOAudit() {
        const btn = qs('#btn-run-aeo-audit');
        if (btn) btn.classList.add('loading');
        const btn2 = qs('#btn-reaudit-aeo');
        if (btn2) btn2.classList.add('loading');
        try {
            const res = await apiFetch('/api/admin/aeo/audit');
            const data = await res.json();
            renderAEOAudit(data);
            showToast(`AEO Audit: ${data.score}/100 (${data.grade})`, data.score >= 70 ? 'success' : 'error');
        } catch (err) {
            showToast('Failed to run AEO audit', 'error');
        } finally {
            if (btn) btn.classList.remove('loading');
            if (btn2) btn2.classList.remove('loading');
        }
    }

    function renderAEOAudit(data) {
        const scoreBox = qs('#aeo-score-box');
        scoreBox.style.display = 'flex';
        qs('#btn-run-aeo-audit').style.display = 'none';

        const circle = qs('#aeo-circle');
        circle.textContent = data.score;
        circle.className = `audit-circle grade-${data.grade.toLowerCase()}`;

        qs('#aeo-grade-label').textContent = `Grade: ${data.grade} — ${data.score}/100`;
        const s = data.summary || {};
        qs('#aeo-stats').textContent = `${s.llms_txt_lines || 0} llms.txt lines · ${s.snippet_count || 0} snippets · ${s.howto_count || 0} HowTos · ${s.topic_clusters || 0} clusters`;

        const checksEl = qs('#aeo-checks');
        checksEl.innerHTML = data.checks.map(c =>
            `<div class="audit-check ${c.passed ? 'pass' : 'fail'}">
                <span class="check-icon">${c.passed ? '✅' : '❌'}</span>
                <div style="flex:1"><strong>${esc(c.name)}</strong><div class="check-tip">${esc(c.tip)}</div></div>
            </div>`
        ).join('');

        // KPIs
        const kpiEl = qs('#aeo-kpis');
        kpiEl.style.display = 'grid';
        kpiEl.innerHTML = [
            { val: data.score, label: 'AEO Score' },
            { val: s.snippet_count || 0, label: 'AI Snippets' },
            { val: s.howto_count || 0, label: 'HowTo Guides' },
            { val: s.topic_clusters || 0, label: 'Topic Clusters' },
            { val: s.blog_posts || 0, label: 'Blog Posts' },
        ].map(k => `<div class="aeo-kpi"><div class="kpi-val">${k.val}</div><div class="kpi-label">${k.label}</div></div>`).join('');
    }

    /* sameAs links */
    function renderSameAs(items) {
        sameAsItems = items.map(i => typeof i === 'string' ? i : (i.url || ''));
        const el = qs('#sameas-entries');
        if (!sameAsItems.length) { el.innerHTML = ''; return; }
        el.innerHTML = sameAsItems.map((url, i) =>
            `<div class="sameas-row">
                <input type="url" value="${esc(url)}" placeholder="https://twitter.com/..." onchange="Admin.updateSameAs(${i},this.value)">
                <button class="btn btn-outline btn-sm" onclick="Admin.removeSameAs(${i})" style="color:var(--primary);">✕</button>
            </div>`
        ).join('');
    }
    function addSameAs() { sameAsItems.push(''); renderSameAs(sameAsItems); }
    function removeSameAs(i) { sameAsItems.splice(i, 1); renderSameAs(sameAsItems); }
    function updateSameAs(i, v) { sameAsItems[i] = v; }
    function collectSameAs() { return sameAsItems.filter(Boolean); }

    /* AI Snippets */
    function renderSnippets(items) {
        snippetItems = items || [];
        const el = qs('#snippet-entries');
        if (!snippetItems.length) { el.innerHTML = '<p style="color:var(--gray-400);font-size:.82rem;">No AI snippets yet. Add concise answers to common queries.</p>'; return; }
        el.innerHTML = snippetItems.map((s, i) =>
            `<div class="snippet-entry">
                <button class="snippet-remove" onclick="Admin.removeSnippet(${i})" title="Remove">✕</button>
                <div class="form-group" style="margin-bottom:8px;">
                    <label>Query <small>(what users ask AI)</small></label>
                    <input type="text" value="${esc(s.query || '')}" placeholder="What is Lawly?" onchange="Admin.updateSnippet(${i},'query',this.value)">
                </div>
                <div class="form-group" style="margin-bottom:0;">
                    <label>Answer <small>(concise, authoritative \u2014 2-3 sentences)</small></label>
                    <textarea rows="2" onchange="Admin.updateSnippet(${i},'answer',this.value)">${esc(s.answer || '')}</textarea>
                </div>
            </div>`
        ).join('');
    }
    function addSnippet() { snippetItems.push({ query: '', answer: '' }); renderSnippets(snippetItems); }
    function removeSnippet(i) { snippetItems.splice(i, 1); renderSnippets(snippetItems); }
    function updateSnippet(i, f, v) { if (snippetItems[i]) snippetItems[i][f] = v; }
    function collectSnippets() { return snippetItems.filter(s => s.query && s.answer); }

    /* HowTo Schema */
    function renderHowTos(items) {
        howtoItems = (items || []).map(h => ({ ...h, steps: h.steps || [] }));
        const el = qs('#howto-entries');
        if (!howtoItems.length) { el.innerHTML = '<p style="color:var(--gray-400);font-size:.82rem;">No HowTo guides yet.</p>'; return; }
        el.innerHTML = howtoItems.map((h, i) =>
            `<div class="howto-entry">
                <button class="howto-remove" onclick="Admin.removeHowTo(${i})" title="Remove">✕</button>
                <div class="form-group" style="margin-bottom:8px;">
                    <label>Guide Title</label>
                    <input type="text" value="${esc(h.name || '')}" placeholder="How to send a consumer legal notice in India" onchange="Admin.updateHowTo(${i},'name',this.value)">
                </div>
                <div class="form-group" style="margin-bottom:8px;">
                    <label>Description <small>(optional)</small></label>
                    <input type="text" value="${esc(h.description || '')}" onchange="Admin.updateHowTo(${i},'description',this.value)">
                </div>
                <label style="font-size:.82rem;font-weight:600;margin-bottom:6px;display:block;">Steps</label>
                <div id="howto-steps-${i}">
                    ${h.steps.map((step, si) => `<div class="step-row">
                        <span style="color:var(--gray-400);font-weight:600;min-width:24px;">${si + 1}.</span>
                        <input type="text" value="${esc(step)}" onchange="Admin.updateHowToStep(${i},${si},this.value)">
                        <button class="btn btn-outline btn-sm" onclick="Admin.removeHowToStep(${i},${si})" style="color:var(--primary);padding:4px 8px;">✕</button>
                    </div>`).join('')}
                </div>
                <button class="btn btn-outline btn-sm" onclick="Admin.addHowToStep(${i})" style="margin-top:6px;">+ Step</button>
            </div>`
        ).join('');
    }
    function addHowTo() { howtoItems.push({ name: '', description: '', steps: [''] }); renderHowTos(howtoItems); }
    function removeHowTo(i) { howtoItems.splice(i, 1); renderHowTos(howtoItems); }
    function updateHowTo(i, f, v) { if (howtoItems[i]) howtoItems[i][f] = v; }
    function addHowToStep(i) { if (howtoItems[i]) { howtoItems[i].steps.push(''); renderHowTos(howtoItems); } }
    function removeHowToStep(i, si) { if (howtoItems[i]) { howtoItems[i].steps.splice(si, 1); renderHowTos(howtoItems); } }
    function updateHowToStep(i, si, v) { if (howtoItems[i] && howtoItems[i].steps) howtoItems[i].steps[si] = v; }
    function collectHowTos() { return howtoItems.filter(h => h.name && h.steps.some(Boolean)).map(h => ({ ...h, steps: h.steps.filter(Boolean) })); }

    /* Topic Clusters */
    function renderClusters(items) {
        clusterItems = items || [];
        const el = qs('#cluster-entries');
        if (!clusterItems.length) { el.innerHTML = '<p style="color:var(--gray-400);font-size:.82rem;">No topic clusters defined.</p>'; return; }
        el.innerHTML = clusterItems.map((c, i) =>
            `<div class="cluster-entry">
                <button class="cluster-remove" onclick="Admin.removeCluster(${i})" title="Remove">✕</button>
                <div class="form-group" style="margin-bottom:8px;">
                    <label>Pillar Topic</label>
                    <input type="text" value="${esc(c.pillar || '')}" placeholder="Consumer Protection in India" onchange="Admin.updateCluster(${i},'pillar',this.value)">
                </div>
                <div class="form-group" style="margin-bottom:0;">
                    <label>Sub-topics <small>(comma-separated)</small></label>
                    <input type="text" value="${esc((c.subtopics || []).join(', '))}" placeholder="CPA 2019, consumer forum, legal notice, refund rights" onchange="Admin.updateClusterSubs(${i},this.value)">
                </div>
            </div>`
        ).join('');
    }
    function addCluster() { clusterItems.push({ pillar: '', subtopics: [] }); renderClusters(clusterItems); }
    function removeCluster(i) { clusterItems.splice(i, 1); renderClusters(clusterItems); }
    function updateCluster(i, f, v) { if (clusterItems[i]) clusterItems[i][f] = v; }
    function updateClusterSubs(i, v) { if (clusterItems[i]) clusterItems[i].subtopics = v.split(',').map(s => s.trim()).filter(Boolean); }
    function collectClusters() { return clusterItems.filter(c => c.pillar); }

    /* Speakable */
    function renderSpeakable(items) {
        speakableItems = items || [];
        const el = qs('#speakable-entries');
        if (!speakableItems.length) { el.innerHTML = ''; return; }
        el.innerHTML = speakableItems.map((s, i) =>
            `<div class="sameas-row">
                <input type="text" value="${esc(s)}" placeholder=".hero-title" onchange="Admin.updateSpeakable(${i},this.value)">
                <button class="btn btn-outline btn-sm" onclick="Admin.removeSpeakable(${i})" style="color:var(--primary);">✕</button>
            </div>`
        ).join('');
    }
    function addSpeakable() { speakableItems.push(''); renderSpeakable(speakableItems); }
    function removeSpeakable(i) { speakableItems.splice(i, 1); renderSpeakable(speakableItems); }
    function updateSpeakable(i, v) { speakableItems[i] = v; }
    function collectSpeakable() { return speakableItems.filter(Boolean); }

    /* Citation Sources */
    function renderSources(items) {
        sourceItems = items || [];
        const el = qs('#source-entries');
        if (!sourceItems.length) { el.innerHTML = '<p style="color:var(--gray-400);font-size:.82rem;">No citation sources added.</p>'; return; }
        el.innerHTML = sourceItems.map((s, i) =>
            `<div class="source-row">
                <input type="text" value="${esc(s.name || '')}" placeholder="Source name" onchange="Admin.updateSource(${i},'name',this.value)">
                <input type="url" value="${esc(s.url || '')}" placeholder="https://..." onchange="Admin.updateSource(${i},'url',this.value)">
                <button class="btn btn-outline btn-sm" onclick="Admin.removeSource(${i})" style="color:var(--primary);">✕</button>
            </div>`
        ).join('');
    }
    function addSource() { sourceItems.push({ name: '', url: '' }); renderSources(sourceItems); }
    function removeSource(i) { sourceItems.splice(i, 1); renderSources(sourceItems); }
    function updateSource(i, f, v) { if (sourceItems[i]) sourceItems[i][f] = v; }
    function collectSources() { return sourceItems.filter(s => s.name || s.url); }

    /* ── Activity ────────────────────────────────────────── */
    async function loadActivity() {
        try {
            const res = await apiFetch('/api/admin/activity?limit=100');
            const items = await res.json();
            renderActivity(items);
        } catch (err) {
            qs('#activity-list').innerHTML = '<div class="empty-state">Failed to load.</div>';
        }
    }

    function renderActivity(items) {
        const el = qs('#activity-list');
        if (!items || !items.length) { el.innerHTML = '<div class="empty-state">No activity recorded yet.</div>'; return; }
        el.innerHTML = items.map(a => {
            const icon = a.entity_type === 'notice' ? '📋' : a.entity_type === 'blog' ? '📝' : a.entity_type === 'seo' ? '🔍' : a.entity_type === 'page' ? '📄' : a.entity_type === 'lawyer' ? '👨‍⚖️' : a.entity_type === 'auth' ? '🔐' : '📌';
            return `<div class="activity-item">
                <div class="activity-dot"></div>
                <div style="flex:1">
                    <div>${icon} <strong>${esc(a.action)}</strong> ${esc(a.details)}</div>
                    ${a.entity_id ? `<div style="font-size:.78rem;color:var(--gray-400)">ID: ${esc(a.entity_id)}</div>` : ''}
                    <div class="activity-time">${formatDate(a.timestamp)}</div>
                </div>
            </div>`;
        }).join('');
    }

    /* ── Lawyer ──────────────────────────────────────────── */
    async function loadLawyer() {
        try {
            const res = await apiFetch('/api/admin/lawyer');
            const d = await res.json();
            if (d && d.name) {
                qs('#l-name').value = d.name || '';
                qs('#l-email').value = d.email || '';
                qs('#l-enrollment').value = d.enrollment_no || '';
                qs('#l-bar').value = d.bar_council || '';
                qs('#l-phone').value = d.phone || '';
            }
        } catch (err) {}
    }

    async function saveLawyer() {
        const body = {
            name: qs('#l-name').value.trim(),
            email: qs('#l-email').value.trim(),
            enrollment_no: qs('#l-enrollment').value.trim(),
            bar_council: qs('#l-bar').value.trim() || null,
            phone: qs('#l-phone').value.trim() || null,
        };
        if (!body.name || !body.email || !body.enrollment_no) { showToast('Fill in name, email, and enrollment number', 'error'); return; }
        try {
            const res = await apiFetch('/api/admin/lawyer', { method: 'PUT', body });
            if (res.ok) showToast('Lawyer details saved', 'success');
            else showToast('Failed to save', 'error');
        } catch (err) { showToast('Failed to save lawyer details', 'error'); }
    }

    /* ── Settings ────────────────────────────────────────── */
    function loadSettings() {
        const el = qs('#settings-api-base');
        if (el) el.value = localStorage.getItem('legaltech_api_base') || '';
    }

    async function changePassword() {
        const current = qs('#pw-current').value;
        const newPw = qs('#pw-new').value;
        const confirm = qs('#pw-confirm').value;
        if (!current || !newPw) { showToast('Fill in all password fields', 'error'); return; }
        if (newPw !== confirm) { showToast('New passwords do not match', 'error'); return; }
        if (newPw.length < 6) { showToast('Password must be at least 6 characters', 'error'); return; }
        try {
            const res = await apiFetch('/api/admin/password', {
                method: 'PUT',
                body: { current_password: current, new_password: newPw },
            });
            if (res.ok) {
                showToast('Password changed successfully', 'success');
                qs('#pw-current').value = '';
                qs('#pw-new').value = '';
                qs('#pw-confirm').value = '';
            } else {
                const err = await res.json().catch(() => ({}));
                showToast(err.detail || 'Failed to change password', 'error');
            }
        } catch (err) { showToast('Failed to change password', 'error'); }
    }

    function saveApiBase() {
        const v = (qs('#settings-api-base')?.value || '').trim();
        if (!v) { clearApiBase(); return; }
        try {
            const u = new URL(v);
            if (!['http:', 'https:'].includes(u.protocol)) throw new Error();
        } catch (_) {
            showToast('Please enter a valid URL', 'error');
            return;
        }
        localStorage.setItem('legaltech_api_base', v.replace(/\/$/, ''));
        showToast('API base URL saved', 'success');
    }

    function clearApiBase() {
        localStorage.removeItem('legaltech_api_base');
        qs('#settings-api-base').value = '';
        showToast('API base reset to default', 'info');
    }

    /* ── Users Tab (Database) ─────────────────────────── */
    async function loadDatabase() {
        try {
            const [statsRes, usersRes] = await Promise.all([
                apiFetch('/api/admin/db/stats'),
                apiFetch('/api/admin/db/users'),
            ]);
            const stats = await statsRes.json();
            const users = await usersRes.json();
            renderDbStats(stats);
            renderDbUsers(users);
        } catch (err) { showToast('Failed to load users', 'error'); }
    }

    function renderDbStats(s) {
        const bar = qs('#db-stats-bar');
        bar.innerHTML = [
            ['👤 Users', s.total_users],
            ['📋 Notices', s.total_notices],
            ['📊 Analyses', s.total_analyses],
            ['📄 PDFs', s.total_pdfs],
            ['📎 Documents', s.total_documents],
        ].map(([label, val]) => `<div class="stat-card"><h3>${val}</h3><p>${label}</p></div>`).join('');
    }

    function renderDbUsers(users) {
        const tbody = qs('#db-users-tbody');
        if (!users.length) { tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--gray-400)">No users yet</td></tr>'; return; }
        tbody.innerHTML = users.map(u => `<tr>
            <td>${u.id}</td>
            <td>${u.full_name || '-'}</td>
            <td>${u.email || '-'}</td>
            <td>${u.phone || '-'}</td>
            <td>${new Date(u.created_at).toLocaleDateString()}</td>
        </tr>`).join('');
    }

    async function downloadDbPdf(noticeId) {
        if (!noticeId && currentNoticeId) {
            noticeId = qs('#modal-btn-db-pdf')?.dataset?.noticeId || currentNoticeId;
        }
        if (!noticeId) return;
        try {
            const res = await apiFetch(`/api/admin/db/pdfs/${noticeId}`);
            if (!res.ok) { showToast('PDF not found', 'error'); return; }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `notice_${noticeId}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        } catch (err) { showToast('Failed to download PDF', 'error'); }
    }

    /* ── Versions Tab ─────────────────────────────────── */
    let currentVerKey = null;

    async function loadVersions() {
        const bucket = qs('#ver-bucket').value;
        qs('#ver-file-list').style.display = '';
        qs('#ver-versions-view').style.display = 'none';
        qs('#ver-preview').style.display = 'none';
        qs('#ver-back-btn').style.display = 'none';
        currentVerKey = null;
        try {
            const res = await apiFetch(`/api/admin/versions?bucket=${encodeURIComponent(bucket)}`);
            const files = await res.json();
            renderVerFiles(files);
        } catch (err) { showToast('Failed to load versions', 'error'); }
    }

    function renderVerFiles(files) {
        const tbody = qs('#ver-files-tbody');
        if (!files.length) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--gray-400)">No versioned files found. Changes made after enabling versioning will appear here.</td></tr>';
            return;
        }
        tbody.innerHTML = files.map(f => {
            const size = f.latest_size > 1024 ? `${(f.latest_size / 1024).toFixed(1)} KB` : `${f.latest_size} B`;
            const date = new Date(f.latest_modified).toLocaleString();
            return `<tr>
                <td style="font-family:monospace;font-size:.8rem;">${esc(f.key)}</td>
                <td>${date}</td>
                <td>${size}</td>
                <td><span class="badge">${f.version_count}</span></td>
                <td><button class="btn btn-outline btn-sm" onclick="Admin.viewFileVersions('${escAttr(f.key)}')">View Versions</button></td>
            </tr>`;
        }).join('');
    }

    function escAttr(s) { return s.replace(/'/g, "\\'").replace(/"/g, '&quot;'); }

    async function viewFileVersions(key) {
        const bucket = qs('#ver-bucket').value;
        currentVerKey = key;
        qs('#ver-file-list').style.display = 'none';
        qs('#ver-versions-view').style.display = '';
        qs('#ver-preview').style.display = 'none';
        qs('#ver-back-btn').style.display = '';
        qs('#ver-file-title').textContent = `Versions of: ${key}`;
        try {
            const res = await apiFetch(`/api/admin/versions/file?key=${encodeURIComponent(key)}&bucket=${encodeURIComponent(bucket)}`);
            const versions = await res.json();
            renderFileVersions(versions, key, bucket);
        } catch (err) { showToast('Failed to load file versions', 'error'); }
    }

    function renderFileVersions(versions, key, bucket) {
        const tbody = qs('#ver-versions-tbody');
        if (!versions.length) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--gray-400)">No versions found</td></tr>';
            return;
        }
        tbody.innerHTML = versions.map(v => {
            const size = v.size > 1024 ? `${(v.size / 1024).toFixed(1)} KB` : `${v.size} B`;
            const date = new Date(v.last_modified).toLocaleString();
            const status = v.is_latest ? '<span class="badge" style="background:#22c55e;color:#fff;">Current</span>' : '<span class="badge" style="background:var(--gray-200);">Old</span>';
            const revertBtn = v.is_latest ? '' : `<button class="btn btn-outline btn-sm" style="color:#dc2626;border-color:#dc2626;" onclick="Admin.revertVersion('${escAttr(key)}','${escAttr(v.version_id)}')">Revert</button>`;
            return `<tr>
                <td style="font-family:monospace;font-size:.75rem;">${v.version_id.substring(0, 16)}…</td>
                <td>${date}</td>
                <td>${size}</td>
                <td>${status}</td>
                <td style="display:flex;gap:6px;">
                    <button class="btn btn-outline btn-sm" onclick="Admin.previewVersion('${escAttr(key)}','${escAttr(v.version_id)}')">Preview</button>
                    ${revertBtn}
                </td>
            </tr>`;
        }).join('');
    }

    async function previewVersion(key, versionId) {
        const bucket = qs('#ver-bucket').value;
        try {
            const res = await apiFetch(`/api/admin/versions/content?key=${encodeURIComponent(key)}&version_id=${encodeURIComponent(versionId)}&bucket=${encodeURIComponent(bucket)}`);
            const data = await res.json();
            qs('#ver-preview-title').textContent = `(${key} — ${versionId.substring(0, 12)}…)`;
            qs('#ver-preview-content').textContent = data.content;
            qs('#ver-preview').style.display = '';
        } catch (err) { showToast('Failed to load version content', 'error'); }
    }

    async function revertVersion(key, versionId) {
        if (!confirm(`Revert "${key}" to version ${versionId.substring(0, 12)}…? This creates a new version with the old content.`)) return;
        const bucket = qs('#ver-bucket').value;
        try {
            const res = await apiFetch('/api/admin/versions/revert', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({key, version_id: versionId, bucket}),
            });
            if (!res.ok) throw new Error('Revert failed');
            showToast('File reverted successfully', 'success');
            viewFileVersions(key);
        } catch (err) { showToast('Failed to revert version', 'error'); }
    }

    function versionsBack() {
        loadVersions();
    }

    function closePreview() {
        qs('#ver-preview').style.display = 'none';
    }

    /* ── Email / Notifications ────────────────────────── */
    let emailSettings = {};

    async function loadEmail() {
        try {
            const [settingsRes, logRes] = await Promise.all([
                apiFetch('/api/admin/email/settings'),
                apiFetch('/api/admin/email/log?limit=50'),
            ]);
            emailSettings = await settingsRes.json();
            const log = await logRes.json();
            renderEmailSettings(emailSettings);
            renderEmailTemplates(emailSettings.templates || {});
            renderEmailLog(log);
        } catch (err) { showToast('Failed to load email settings', 'error'); }
    }

    function renderEmailSettings(s) {
        qs('#em-smtp-host').value = s.smtp_host || '';
        qs('#em-smtp-port').value = s.smtp_port || 587;
        qs('#em-smtp-user').value = s.smtp_user || '';
        qs('#em-smtp-pass').value = s.smtp_password || '';
        qs('#em-from-name').value = s.from_name || '';
        qs('#em-from-email').value = s.from_email || '';
        qs('#em-admin-alert').value = s.admin_alert_email || '';
        qs('#em-use-tls').checked = s.use_tls !== false;
        qs('#em-auto-notice').checked = s.auto_send_notice_ready !== false;
        qs('#em-auto-admin').checked = s.auto_send_admin_alert !== false;
        qs('#em-followup-days').value = s.follow_up_days || 15;
    }

    function renderEmailTemplates(templates) {
        const area = qs('#email-templates-area');
        const names = { notice_ready: '📬 Notice Ready', payment_receipt: '🧾 Payment Receipt', follow_up: '🔔 Follow-up Reminder', admin_alert: '🚨 Admin Alert' };
        area.innerHTML = Object.entries(names).map(([key, label]) => {
            const t = templates[key] || {};
            return `<div class="email-template-card">
                <h4>${label}</h4>
                <div class="form-group"><label>Subject</label><input type="text" id="tpl-${key}-subject" value="${esc(t.subject || '')}"></div>
                <div class="form-group"><label>Body</label><textarea rows="4" id="tpl-${key}-body" style="font-family:monospace;font-size:.82rem;">${esc(t.body || '')}</textarea></div>
            </div>`;
        }).join('');
    }

    function renderEmailLog(log) {
        const area = qs('#email-log-area');
        if (!log || !log.length) { area.innerHTML = '<div class="empty-state">No emails sent yet</div>'; return; }
        area.innerHTML = '<div class="email-log-row" style="font-weight:600;color:var(--gray-400);font-size:.75rem;"><div>Template</div><div>To</div><div>Subject</div><div>Status</div><div>Time</div></div>' +
            log.map(e => `<div class="email-log-row">
                <div>${esc(e.template || '')}</div>
                <div>${esc(e.to || '')}</div>
                <div>${esc((e.subject || '').substring(0, 40))}</div>
                <div><span class="email-status-${e.status === 'sent' ? 'sent' : 'failed'}">${e.status}</span></div>
                <div>${formatDate(e.timestamp)}</div>
            </div>`).join('');
    }

    async function saveEmailSettings() {
        const templates = {};
        for (const key of ['notice_ready', 'payment_receipt', 'follow_up', 'admin_alert']) {
            const subEl = qs(`#tpl-${key}-subject`);
            const bodyEl = qs(`#tpl-${key}-body`);
            if (subEl && bodyEl) {
                templates[key] = { subject: subEl.value, body: bodyEl.value };
            }
        }
        const payload = {
            smtp_host: qs('#em-smtp-host').value,
            smtp_port: parseInt(qs('#em-smtp-port').value) || 587,
            smtp_user: qs('#em-smtp-user').value,
            smtp_password: qs('#em-smtp-pass').value,
            from_name: qs('#em-from-name').value,
            from_email: qs('#em-from-email').value,
            admin_alert_email: qs('#em-admin-alert').value,
            use_tls: qs('#em-use-tls').checked,
            auto_send_notice_ready: qs('#em-auto-notice').checked,
            auto_send_admin_alert: qs('#em-auto-admin').checked,
            follow_up_days: parseInt(qs('#em-followup-days').value) || 15,
            templates,
        };
        try {
            const res = await apiFetch('/api/admin/email/settings', { method: 'PUT', body: JSON.stringify(payload) });
            if (res.ok) { showToast('Email settings saved', 'success'); }
            else { showToast('Failed to save', 'error'); }
        } catch (err) { showToast('Error saving email settings', 'error'); }
    }

    async function sendTestEmail() {
        const to = qs('#em-test-to').value.trim();
        const template = qs('#em-test-template').value;
        if (!to) { showToast('Enter a recipient email', 'error'); return; }
        try {
            const res = await apiFetch('/api/admin/email/test', { method: 'POST', body: JSON.stringify({ to_email: to, template }) });
            const data = await res.json();
            if (res.ok) { showToast(data.message || 'Test email sent!', 'success'); loadEmail(); }
            else { showToast(data.detail || 'Failed to send test email', 'error'); }
        } catch (err) { showToast('Failed to send test email', 'error'); }
    }

    /* ── Analytics ──────────────────────────────────────── */
    let analyticsChartDaily = null, analyticsChartRevenue = null, analyticsChartTiers = null;

    async function loadAnalytics() {
        try {
            const res = await apiFetch('/api/admin/analytics');
            const data = await res.json();
            renderAnalyticsKPIs(data);
            renderFunnel(data.funnel);
            renderAnalyticsCharts(data);
            renderCategories(data.categories);
            renderTrafficSources(data.traffic_sources);
            renderTopReferrers(data.top_referrers);
        } catch (err) { showToast('Failed to load analytics', 'error'); }
    }

    function renderAnalyticsKPIs(d) {
        qs('#ak-views').textContent = (d.funnel?.page_view || 0).toLocaleString();
        qs('#ak-started').textContent = (d.funnel?.notice_started || 0).toLocaleString();
        qs('#ak-generated').textContent = (d.funnel?.notice_generated || 0).toLocaleString();
        qs('#ak-revenue').textContent = '₹' + (d.revenue_total || 0).toLocaleString();
    }

    function renderFunnel(f) {
        const area = qs('#funnel-area');
        if (!f) { area.innerHTML = '<div class="empty-state">No data yet</div>'; return; }
        const steps = [
            ['Page Views', f.page_view || 0, 'lv0'],
            ['Notices Started', f.notice_started || 0, 'lv1'],
            ['Notices Generated', f.notice_generated || 0, 'lv2'],
            ['PDFs Downloaded', f.pdf_downloaded || 0, 'lv3'],
            ['Payments', f.payment || 0, 'lv4'],
        ];
        const max = Math.max(...steps.map(s => s[1]), 1);
        area.innerHTML = steps.map(([label, count, cls]) => {
            const pct = Math.max((count / max) * 100, 4);
            return `<div class="funnel-bar">
                <div class="funnel-label">${label}</div>
                <div class="funnel-track"><div class="funnel-fill ${cls}" style="width:${pct}%">${count}</div></div>
            </div>`;
        }).join('');
    }

    function renderAnalyticsCharts(data) {
        if (typeof Chart === 'undefined') return;
        const daily = data.daily_trend || {};
        const dates = Object.keys(daily);
        const generated = dates.map(d => (daily[d]?.notice_generated || 0));
        const views = dates.map(d => (daily[d]?.page_view || 0));

        if (analyticsChartDaily) analyticsChartDaily.destroy();
        analyticsChartDaily = new Chart(qs('#analytics-chart-daily'), {
            type: 'bar',
            data: {
                labels: dates.length ? dates : ['No data'],
                datasets: [
                    { label: 'Page Views', data: views.length ? views : [0], backgroundColor: 'rgba(37,99,235,.3)', borderColor: '#2563EB', borderWidth: 1 },
                    { label: 'Notices', data: generated.length ? generated : [0], backgroundColor: 'rgba(220,38,38,.3)', borderColor: '#DC2626', borderWidth: 1 },
                ],
            },
            options: { responsive: true, plugins: { legend: { position: 'bottom' } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } },
        });

        // Revenue chart
        const revDaily = data.revenue_daily || {};
        const revDates = Object.keys(revDaily);
        const revVals = Object.values(revDaily);
        if (analyticsChartRevenue) analyticsChartRevenue.destroy();
        analyticsChartRevenue = new Chart(qs('#analytics-chart-revenue'), {
            type: 'line',
            data: {
                labels: revDates.length ? revDates : ['No data'],
                datasets: [{ label: 'Revenue (₹)', data: revVals.length ? revVals : [0], borderColor: '#059669', backgroundColor: 'rgba(5,150,105,.1)', fill: true, tension: 0.3 }],
            },
            options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
        });

        // Tier doughnut
        const tiers = data.tier_counts || {};
        if (analyticsChartTiers) analyticsChartTiers.destroy();
        analyticsChartTiers = new Chart(qs('#analytics-chart-tiers'), {
            type: 'doughnut',
            data: {
                labels: Object.keys(tiers).length ? Object.keys(tiers).map(t => t === 'lawyer' ? '₹599 Lawyer' : '₹199 Self') : ['No data'],
                datasets: [{ data: Object.values(tiers).length ? Object.values(tiers) : [1], backgroundColor: ['#DC2626', '#F59E0B', '#2563EB'] }],
            },
            options: { responsive: true, plugins: { legend: { position: 'bottom' } } },
        });
    }

    function renderCategories(cats) {
        const ul = qs('#analytics-categories');
        const entries = Object.entries(cats || {});
        if (!entries.length) { ul.innerHTML = '<li class="empty-state">No categories recorded yet</li>'; return; }
        ul.innerHTML = entries.slice(0, 15).map(([cat, count]) =>
            `<li><span>${esc(cat)}</span><strong>${count}</strong></li>`
        ).join('');
    }

    function renderTrafficSources(sources) {
        const el = qs('#analytics-sources');
        const entries = Object.entries(sources || {});
        if (!entries.length) { el.innerHTML = '<div class="empty-state">No traffic data yet</div>'; return; }
        const total = entries.reduce((s, [, c]) => s + c, 0);
        const colors = { reddit: '#FF4500', google: '#4285F4', direct: '#6B7280', bing: '#008373', twitter: '#1DA1F2', facebook: '#1877F2', linkedin: '#0A66C2', instagram: '#E4405F', youtube: '#FF0000' };
        el.innerHTML = entries.slice(0, 12).map(([src, count]) => {
            const pct = Math.round((count / total) * 100);
            const color = colors[src] || '#8B5CF6';
            return `<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                <span style="width:90px;font-size:.82rem;font-weight:600;text-transform:capitalize;color:${color}">${esc(src)}</span>
                <div style="flex:1;background:#f1f5f9;border-radius:6px;height:22px;overflow:hidden">
                    <div style="width:${Math.max(pct, 3)}%;height:100%;background:${color};border-radius:6px;transition:width .3s"></div>
                </div>
                <span style="font-size:.82rem;font-weight:600;min-width:55px;text-align:right">${count} (${pct}%)</span>
            </div>`;
        }).join('');
    }

    function renderTopReferrers(refs) {
        const ul = qs('#analytics-referrers');
        const entries = Object.entries(refs || {});
        if (!entries.length) { ul.innerHTML = '<li class="empty-state">No referrer data yet</li>'; return; }
        ul.innerHTML = entries.slice(0, 15).map(([ref, count]) =>
            `<li><span style="font-size:.82rem">${esc(ref)}</span><strong>${count}</strong></li>`
        ).join('');
    }

    /* ── Search Insights (Bing Webmaster) ───────────────── */
    let insightsChartTraffic = null, insightsChartCrawl = null;

    async function loadInsights() {
        try {
            const res = await apiFetch('/api/admin/insights');
            const data = await res.json();
            if (!data.configured) {
                qs('#tab-insights').innerHTML = '<div class="empty-state" style="padding:40px;text-align:center;">' +
                    '<h3>Bing Webmaster API Not Configured</h3>' +
                    '<p style="margin-top:8px;color:var(--muted);">Set the <code>BING_WEBMASTER_API_KEY</code> environment variable to enable search insights.</p></div>';
                return;
            }
            renderInsightsKPIs(data);
            renderInsightsCharts(data);
            renderKeywordsTable(data.top_keywords || []);
            renderCrawlInfo(data.crawl || {});
            renderQuota(data.submission_quota || {});
        } catch (err) { showToast('Failed to load insights', 'error'); }
    }

    function renderInsightsKPIs(d) {
        const t = d.totals || {};
        qs('#ik-impressions').textContent = (t.impressions || 0).toLocaleString();
        qs('#ik-clicks').textContent = (t.clicks || 0).toLocaleString();
        qs('#ik-ctr').textContent = (t.ctr || 0) + '%';
        qs('#ik-crawled').textContent = (d.crawl?.total_pages_crawled || 0).toLocaleString();
    }

    function renderInsightsCharts(data) {
        if (typeof Chart === 'undefined') return;
        const daily = data.daily_traffic || {};
        const dates = Object.keys(daily).sort();
        const impressions = dates.map(d => daily[d]?.impressions || 0);
        const clicks = dates.map(d => daily[d]?.clicks || 0);

        if (insightsChartTraffic) insightsChartTraffic.destroy();
        insightsChartTraffic = new Chart(qs('#insights-chart-traffic'), {
            type: 'bar',
            data: {
                labels: dates.length ? dates : ['No data'],
                datasets: [
                    { label: 'Impressions', data: impressions.length ? impressions : [0], backgroundColor: 'rgba(37,99,235,.3)', borderColor: '#2563EB', borderWidth: 1 },
                    { label: 'Clicks', data: clicks.length ? clicks : [0], backgroundColor: 'rgba(5,150,105,.3)', borderColor: '#059669', borderWidth: 1 },
                ],
            },
            options: { responsive: true, plugins: { legend: { position: 'bottom' } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } },
        });

        // Crawl chart from raw crawl data
        const crawl = data.crawl || {};
        if (insightsChartCrawl) insightsChartCrawl.destroy();
        // Use daily_traffic dates as proxy; actual crawl is in crawl.latest
        insightsChartCrawl = new Chart(qs('#insights-chart-crawl'), {
            type: 'bar',
            data: {
                labels: ['Pages Crawled', 'Crawl Errors'],
                datasets: [{
                    label: 'Crawl Stats',
                    data: [crawl.total_pages_crawled || 0, crawl.total_errors || 0],
                    backgroundColor: ['rgba(37,99,235,.4)', 'rgba(220,38,38,.4)'],
                    borderColor: ['#2563EB', '#DC2626'],
                    borderWidth: 1,
                }],
            },
            options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
        });
    }

    function renderKeywordsTable(keywords) {
        const tbody = qs('#insights-keywords-body');
        if (!keywords.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No keyword data yet — Bing needs a few days to collect data after site verification.</td></tr>';
            return;
        }
        tbody.innerHTML = keywords.map(kw =>
            `<tr><td><strong>${esc(kw.query)}</strong></td><td>${kw.impressions.toLocaleString()}</td><td>${kw.clicks.toLocaleString()}</td><td>${kw.ctr}%</td><td>${kw.avg_position}</td></tr>`
        ).join('');
    }

    function renderCrawlInfo(crawl) {
        const el = qs('#insights-crawl-info');
        if (!crawl.total_pages_crawled && !crawl.total_errors) {
            el.innerHTML = '<span class="empty-state">No crawl data yet — Bing will start reporting after it crawls your site.</span>';
            return;
        }
        const latest = crawl.latest || {};
        el.innerHTML = `
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;">
                <div><strong>${(crawl.total_pages_crawled || 0).toLocaleString()}</strong><br><span style="color:var(--muted);font-size:.8rem;">Total Pages Crawled</span></div>
                <div><strong style="color:${crawl.total_errors ? 'var(--red)' : 'inherit'};">${(crawl.total_errors || 0).toLocaleString()}</strong><br><span style="color:var(--muted);font-size:.8rem;">Crawl Errors</span></div>
                <div><strong>${(latest.in_index || 0).toLocaleString()}</strong><br><span style="color:var(--muted);font-size:.8rem;">Pages in Index</span></div>
                <div><strong>${(latest.in_links || 0).toLocaleString()}</strong><br><span style="color:var(--muted);font-size:.8rem;">Inbound Links</span></div>
            </div>`;
    }

    function renderQuota(quota) {
        qs('#insights-quota').textContent = `Daily quota: ${quota.daily_quota ?? '—'} · Monthly quota: ${quota.monthly_quota ?? '—'}`;
    }

    async function submitBingUrl() {
        const input = qs('#insights-submit-url');
        const url = input.value.trim();
        if (!url) { showToast('Enter a URL', 'error'); return; }
        try {
            const res = await apiFetch('/api/admin/insights/submit-url', { method: 'POST', body: { url } });
            const data = await res.json();
            if (data.ok) { showToast('URL submitted to Bing!', 'success'); input.value = ''; }
            else showToast(data.error || 'Submission failed', 'error');
        } catch (err) { showToast('Failed to submit URL', 'error'); }
    }

    async function submitAllPages() {
        const urls = [
            'https://lawly.store/',
            'https://lawly.store/blog',
            'https://lawly.store/sitemap.xml',
        ];
        try {
            const res = await apiFetch('/api/admin/insights/submit-batch', { method: 'POST', body: { urls } });
            const data = await res.json();
            if (data.ok) showToast(`${data.count} URLs submitted to Bing!`, 'success');
            else showToast(data.error || 'Batch submission failed', 'error');
        } catch (err) { showToast('Failed to submit urls', 'error'); }
    }

    /* ── Support Tickets ────────────────────────────────── */
    let ticketsCache = [];
    let currentTicketId = null;

    async function loadSupport() {
        try {
            const [ticketsRes, statsRes] = await Promise.all([
                apiFetch('/api/admin/tickets'),
                apiFetch('/api/admin/tickets/stats'),
            ]);
            ticketsCache = await ticketsRes.json();
            const stats = await statsRes.json();
            renderTicketStats(stats);
            renderTicketsList(ticketsCache);
        } catch (err) { showToast('Failed to load tickets', 'error'); }
    }

    function renderTicketStats(s) {
        qs('#ts-total').textContent = s.total || 0;
        qs('#ts-open').textContent = s.open || 0;
        qs('#ts-progress').textContent = s.in_progress || 0;
        qs('#ts-resolved').textContent = s.resolved || 0;
        qs('#ts-closed').textContent = s.closed || 0;
    }

    function ticketBadge(status) {
        const cls = { open: 'badge-open', in_progress: 'badge-in-progress', resolved: 'badge-resolved', closed: 'badge-closed' };
        const labels = { open: 'Open', in_progress: 'In Progress', resolved: 'Resolved', closed: 'Closed' };
        return `<span class="${cls[status] || 'badge-open'}">${labels[status] || status}</span>`;
    }

    function renderTicketsList(tickets) {
        const area = qs('#tickets-list-area');
        if (!tickets || !tickets.length) { area.innerHTML = '<div class="empty-state">No support tickets yet</div>'; return; }
        area.innerHTML = `<table class="data-table"><thead><tr>
            <th>ID</th><th>Subject</th><th>From</th><th>Category</th><th>Status</th><th>Priority</th><th>Date</th>
        </tr></thead><tbody>` +
            tickets.map(t => `<tr style="cursor:pointer" onclick="Admin.openTicket('${t.id}')">
                <td style="font-family:monospace;font-size:.78rem;">${t.id}</td>
                <td>${esc(t.subject)}</td>
                <td>${esc(t.name)}<br><small style="color:var(--gray-400)">${esc(t.email)}</small></td>
                <td>${esc(t.category)}</td>
                <td>${ticketBadge(t.status)}</td>
                <td>${esc(t.priority || 'normal')}</td>
                <td>${formatDate(t.created_at)}</td>
            </tr>`).join('') +
            '</tbody></table>';
    }

    function filterTickets() {
        const f = qs('#ticket-filter').value;
        const filtered = f === 'all' ? ticketsCache : ticketsCache.filter(t => t.status === f);
        renderTicketsList(filtered);
    }

    async function openTicket(ticketId) {
        try {
            const res = await apiFetch(`/api/admin/tickets/${ticketId}`);
            const t = await res.json();
            currentTicketId = ticketId;
            qs('#ticket-modal-title').textContent = `🎫 Ticket #${t.id}`;
            qs('#ticket-detail-grid').innerHTML = `
                <div class="td-card"><h4>From</h4><p>${esc(t.name)}<br>${esc(t.email)}</p></div>
                <div class="td-card"><h4>Category</h4><p>${esc(t.category)}</p></div>
                <div class="td-card"><h4>Notice ID</h4><p>${t.notice_id ? esc(t.notice_id) : '—'}</p></div>
            `;
            qs('#ticket-message').textContent = t.message || '';
            qs('#ticket-status').value = t.status || 'open';
            qs('#ticket-priority').value = t.priority || 'normal';
            qs('#ticket-admin-notes').value = t.admin_notes || '';
            renderTicketReplies(t.replies || []);
            qs('#ticket-reply-text').value = '';
            qs('#ticket-modal').classList.remove('hidden');
        } catch (err) { showToast('Failed to load ticket', 'error'); }
    }

    function renderTicketReplies(replies) {
        const el = qs('#ticket-replies');
        if (!replies.length) { el.innerHTML = '<div class="empty-state" style="font-size:.82rem;">No replies yet</div>'; return; }
        el.innerHTML = replies.map(r =>
            `<div class="reply-bubble ${r.from === 'admin' ? 'admin' : 'customer'}">
                <div>${esc(r.message)}</div>
                <div class="reply-meta">${r.from === 'admin' ? '👨‍💼 Admin' : '👤 Customer'} · ${formatDate(r.timestamp)}</div>
            </div>`
        ).join('');
    }

    async function updateTicket() {
        if (!currentTicketId) return;
        const payload = {
            status: qs('#ticket-status').value,
            priority: qs('#ticket-priority').value,
            admin_notes: qs('#ticket-admin-notes').value,
        };
        try {
            const res = await apiFetch(`/api/admin/tickets/${currentTicketId}`, { method: 'PUT', body: JSON.stringify(payload) });
            if (res.ok) { showToast('Ticket updated', 'success'); loadSupport(); }
            else { showToast('Failed to update', 'error'); }
        } catch (err) { showToast('Error updating ticket', 'error'); }
    }

    async function sendTicketReply() {
        if (!currentTicketId) return;
        const msg = qs('#ticket-reply-text').value.trim();
        if (!msg) { showToast('Type a reply first', 'error'); return; }
        try {
            const res = await apiFetch(`/api/admin/tickets/${currentTicketId}/reply`, {
                method: 'POST', body: JSON.stringify({ message: msg, from_who: 'admin' }),
            });
            if (res.ok) {
                const t = await res.json();
                renderTicketReplies(t.replies || []);
                qs('#ticket-reply-text').value = '';
                showToast('Reply sent', 'success');
            } else { showToast('Failed to send reply', 'error'); }
        } catch (err) { showToast('Error sending reply', 'error'); }
    }

    function closeTicketModal() {
        qs('#ticket-modal').classList.add('hidden');
        currentTicketId = null;
    }

    /* ── Modal helpers (Escape key + backdrop click) ────── */
    function closeAllModals() {
        qs('#notice-modal')?.classList.add('hidden');
        qs('#blog-modal')?.classList.add('hidden');
        qs('#page-modal')?.classList.add('hidden');
        qs('#ticket-modal')?.classList.add('hidden');
        currentNoticeId = null;
        editingSlug = null;
        editingPage = null;
        currentTicketId = null;
    }

    /* ── AI Tool Functions ───────────────────────────────── */

    // ── Blog AI ──
    async function aiBlogFromTopic() {
        const topic = prompt('Blog topic (e.g. "How to file a consumer complaint under CPA 2019"):');
        if (!topic) return;
        const keywords = prompt('Target keywords (optional, comma-separated):', '') || '';
        const btn = event.currentTarget;
        const r = await aiGenerate('blog_post', { topic, keywords }, btn);
        if (!r) return;
        // Open blog editor and fill in
        openBlogEditor();
        qs('#b-title').value = r.title || '';
        qs('#b-slug').value = r.slug || '';
        if (r.content && quill) quill.root.innerHTML = r.content;
        qs('#b-meta-desc').value = r.meta_description || '';
        qs('#b-meta-kw').value = r.meta_keywords || '';
    }

    async function aiBlogImprove(btn) {
        if (!quill) return;
        const content = quill.root.innerHTML;
        const title = qs('#b-title').value;
        if (!content || content === '<p><br></p>') { showToast('Write some content first', 'error'); return; }
        const instruction = prompt('Improvement instruction:', 'Improve readability, SEO, and add more detail') || 'Improve readability, SEO, and add more detail';
        const r = await aiGenerate('blog_improve', { content, title, instruction }, btn);
        if (!r) return;
        if (r.content) quill.root.innerHTML = r.content;
        if (r.meta_description) qs('#b-meta-desc').value = r.meta_description;
        if (r.meta_keywords) qs('#b-meta-kw').value = r.meta_keywords;
        if (r.suggestions && r.suggestions.length) {
            showToast('Suggestions: ' + r.suggestions.join('; '), 'info');
        }
    }

    async function aiBlogMeta(btn) {
        const title = qs('#b-title').value;
        const content = quill ? quill.getText().substring(0, 500) : '';
        if (!title) { showToast('Enter a blog title first', 'error'); return; }
        const r = await aiGenerate('seo_meta', { title, content }, btn);
        if (!r) return;
        if (r.meta_description) qs('#b-meta-desc').value = r.meta_description;
    }

    async function aiBlogKeywords(btn) {
        const title = qs('#b-title').value;
        const content = quill ? quill.getText().substring(0, 500) : '';
        if (!title) { showToast('Enter a blog title first', 'error'); return; }
        const r = await aiGenerate('seo_meta', { title, content }, btn);
        if (!r) return;
        if (r.meta_keywords) qs('#b-meta-kw').value = r.meta_keywords;
    }

    // ── SEO AI ──
    async function aiSeoMeta(btn) {
        const title = qs('#seo-title').value;
        const desc = qs('#seo-desc').value;
        const r = await aiGenerate('seo_meta', { title: title || 'Lawly', content: desc, url: 'https://lawly.store' }, btn);
        if (!r) return;
        if (r.site_title) qs('#seo-title').value = r.site_title;
        if (r.meta_description) qs('#seo-desc').value = r.meta_description;
        if (r.meta_keywords) qs('#seo-keywords').value = r.meta_keywords;
        if (r.og_title) qs('#seo-og-title').value = r.og_title;
        if (r.og_description) qs('#seo-og-desc').value = r.og_description;
        updateSEOPreview();
    }

    async function aiSeoFaq(btn) {
        const topic = prompt('FAQ topic (or leave blank for general):', '') || '';
        // Gather existing FAQ data
        const existingFaqs = [];
        document.querySelectorAll('#faq-entries .faq-entry').forEach(el => {
            const q = el.querySelector('input')?.value;
            if (q) existingFaqs.push(q);
        });
        const r = await aiGenerate('seo_faq', { topic, existing_faqs: existingFaqs }, btn);
        if (!r || !r.faqs) return;
        for (const faq of r.faqs) {
            addFaqItem();
            const idx = faqItems.length - 1;
            faqItems[idx].question = faq.question || '';
            faqItems[idx].answer = faq.answer || '';
        }
        renderFaqEntries(faqItems);
        showToast(`Added ${r.faqs.length} AI-generated FAQs`, 'success');
    }

    async function aiKeywordIdeas(btn) {
        const seed = prompt('Seed keyword:', qs('#seo-keywords').value || 'consumer legal notice India') || 'consumer legal notice India';
        const r = await aiGenerate('keyword_ideas', { seed_keyword: seed }, btn);
        if (!r || !r.keywords) return;
        const html = r.keywords.map(k =>
            `<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--gray-200);font-size:.82rem;">
                <span><strong>${esc(k.keyword)}</strong></span>
                <span style="color:var(--gray-500);">${esc(k.intent)} · ${esc(k.difficulty)}</span>
            </div>`
        ).join('');
        qs('#keyword-analysis').innerHTML = `<h4>✨ AI Keyword Ideas</h4>${html}`;
    }

    // ── AEO AI ──
    async function aiLlmsTxt(btn) {
        const r = await aiGenerate('aeo_llms_txt', {}, btn);
        if (!r) return;
        if (r.llms_txt) qs('#aeo-llms-txt').value = r.llms_txt;
    }

    async function aiAeoSnippets(btn) {
        const topic = prompt('Focus area for snippets (or leave blank):', '') || '';
        const existing = [];
        document.querySelectorAll('#snippet-entries .snippet-entry').forEach(el => {
            const q = el.querySelector('input')?.value;
            if (q) existing.push({ query: q });
        });
        const r = await aiGenerate('aeo_snippets', { topic, existing_snippets: existing }, btn);
        if (!r || !r.snippets) return;
        for (const s of r.snippets) {
            addSnippet();
            const idx = snippetItems.length - 1;
            snippetItems[idx].query = s.query || '';
            snippetItems[idx].answer = s.answer || '';
        }
        renderSnippets(snippetItems);
        showToast(`Added ${r.snippets.length} AI snippets`, 'success');
    }

    async function aiTopicClusters(btn) {
        const existing = [];
        document.querySelectorAll('#cluster-entries .cluster-entry').forEach(el => {
            const name = el.querySelector('input')?.value;
            if (name) existing.push({ name });
        });
        const r = await aiGenerate('aeo_topic_clusters', { existing_clusters: existing }, btn);
        if (!r || !r.clusters) return;
        for (const c of r.clusters) {
            addCluster();
            const idx = clusterItems.length - 1;
            clusterItems[idx].pillar = c.pillar || c.name || '';
            clusterItems[idx].subtopics = c.subtopics || [];
        }
        renderClusters(clusterItems);
        showToast(`Added ${r.clusters.length} topic clusters`, 'success');
    }

    // ── Email AI ──
    async function aiEmailTemplate(btn) {
        const templateType = prompt('Template type (notice_ready, payment_receipt, follow_up, admin_alert):', 'notice_ready') || 'notice_ready';
        const instruction = prompt('Custom instruction (optional):', '') || '';
        const r = await aiGenerate('email_template', { type: templateType, instruction }, btn);
        if (!r) return;
        const subEl = qs(`#tpl-${templateType}-subject`);
        const bodyEl = qs(`#tpl-${templateType}-body`);
        if (subEl && r.subject) subEl.value = r.subject;
        if (bodyEl && r.body) bodyEl.value = r.body;
        showToast(`AI template generated for ${templateType}`, 'success');
    }

    // ── Support AI ──
    async function aiTicketReply(btn) {
        if (!currentTicketId) return;
        const ticket = {
            subject: qs('#ticket-modal-title')?.textContent || '',
            message: qs('#ticket-message')?.textContent || '',
            status: qs('#ticket-status')?.value || 'open',
            category: '',
            replies: [],
        };
        // Gather existing replies
        document.querySelectorAll('#ticket-replies .reply-bubble').forEach(el => {
            ticket.replies.push(el.textContent || '');
        });
        const r = await aiGenerate('ticket_reply', { ticket }, btn);
        if (!r) return;
        qs('#ticket-reply-text').value = r.reply || '';
        if (r.suggested_status) qs('#ticket-status').value = r.suggested_status;
    }

    // ── Notice AI ──
    async function aiNoticeReview(btn) {
        const noticeText = qs('#modal-n-notice')?.textContent || '';
        if (!noticeText || noticeText.length < 50) { showToast('No notice content to review', 'error'); return; }
        const r = await aiGenerate('notice_review', { notice_text: noticeText }, btn);
        if (!r) return;
        const reviewDiv = qs('#ai-notice-review');
        const contentDiv = qs('#ai-review-content');
        reviewDiv.classList.remove('hidden');
        contentDiv.innerHTML = `
            <div style="display:flex;gap:16px;align-items:center;margin-bottom:8px;">
                <div style="font-size:1.5rem;font-weight:700;color:${r.score >= 70 ? 'var(--green)' : r.score >= 50 ? 'var(--orange)' : 'var(--primary)'};">${r.score || '—'}/100</div>
                <div style="font-size:1.1rem;font-weight:600;">Grade: ${esc(r.grade || '—')}</div>
            </div>
            ${r.strengths?.length ? `<div style="margin-bottom:6px;"><strong style="color:var(--green);">Strengths:</strong><ul style="margin:4px 0 0 16px;">${r.strengths.map(s => `<li>${esc(s)}</li>`).join('')}</ul></div>` : ''}
            ${r.weaknesses?.length ? `<div style="margin-bottom:6px;"><strong style="color:var(--primary);">Weaknesses:</strong><ul style="margin:4px 0 0 16px;">${r.weaknesses.map(s => `<li>${esc(s)}</li>`).join('')}</ul></div>` : ''}
            ${r.suggestions?.length ? `<div style="margin-bottom:6px;"><strong style="color:var(--blue);">Suggestions:</strong><ul style="margin:4px 0 0 16px;">${r.suggestions.map(s => `<li>${esc(s)}</li>`).join('')}</ul></div>` : ''}
            ${r.reviewer_notes ? `<div style="margin-top:8px;padding:8px;background:#fff;border-radius:6px;"><em>${esc(r.reviewer_notes)}</em></div>` : ''}
        `;
    }

    // ── Pages AI ──
    async function aiPageMeta(btn) {
        const path = qs('#pg-path').value;
        const title = qs('#pg-title').value;
        if (!path && !title) { showToast('Enter a path or title first', 'error'); return; }
        const r = await aiGenerate('page_meta', { path, title }, btn);
        if (!r) return;
        if (r.title) qs('#pg-title').value = r.title;
        if (r.meta_description) qs('#pg-desc').value = r.meta_description;
        if (r.meta_keywords) qs('#pg-keywords').value = r.meta_keywords;
        if (r.og_title) qs('#pg-og-title').value = r.og_title;
        if (r.og_description) qs('#pg-og-desc').value = r.og_description;
    }

    /* ── Init ────────────────────────────────────────────── */
    document.addEventListener('DOMContentLoaded', () => {
        // Tab click handlers
        document.querySelectorAll('.admin-tab').forEach(btn => {
            btn.addEventListener('click', () => switchTab(btn.dataset.tab));
        });

        // Login form
        qs('#login-form').addEventListener('submit', login);

        // Escape key closes modals
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') closeAllModals();
        });

        // Backdrop click closes modals
        document.querySelectorAll('.modal-overlay').forEach(overlay => {
            overlay.addEventListener('click', e => {
                if (e.target === overlay) closeAllModals();
            });
        });

        // Auto-login if token exists
        if (token) { showAdmin(); }
    });

    /* ── Public API ──────────────────────────────────────── */
    return {
        login, logout, switchTab,
        openNotice, closeNoticeModal, approveNotice, rejectNotice, downloadPDF, exportCSV, filterNotices,
        openBlogEditor, editBlog, closeBlogModal, saveBlog, deleteBlog,
        openPageEditor, editPage, closePageModal, savePage, deletePage,
        saveSEO, updateSEOPreview, runSEOAudit,
        addFaqItem, removeFaqItem, updateFaqItem,
        addHreflangItem, removeHreflangItem, updateHreflangItem,
        addRedirect, deleteRedirect, pingSitemap,
        saveAEO, runAEOAudit,
        addSameAs, removeSameAs, updateSameAs,
        addSnippet, removeSnippet, updateSnippet,
        addHowTo, removeHowTo, updateHowTo, addHowToStep, removeHowToStep, updateHowToStep,
        addCluster, removeCluster, updateCluster, updateClusterSubs,
        addSpeakable, removeSpeakable, updateSpeakable,
        addSource, removeSource, updateSource,
        saveLawyer,
        changePassword, saveApiBase, clearApiBase,
        downloadDbPdf,
        saveEmailSettings, sendTestEmail,
        filterTickets, openTicket, updateTicket, sendTicketReply, closeTicketModal,
        submitBingUrl, submitAllPages,
        loadVersions, viewFileVersions, previewVersion, revertVersion, versionsBack, closePreview,
        aiBlogFromTopic, aiBlogImprove, aiBlogMeta, aiBlogKeywords,
        aiSeoMeta, aiSeoFaq, aiKeywordIdeas,
        aiLlmsTxt, aiAeoSnippets, aiTopicClusters,
        aiEmailTemplate, aiTicketReply,
        aiNoticeReview, aiPageMeta,
    };
})();
