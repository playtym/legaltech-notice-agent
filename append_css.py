# Read original
with open('static/style.css', 'r', encoding='utf-8') as f:
    text = f.read()

# Make sure we don't duplicate
if 'notice-preview' not in text:
    append_css = """
/* Notice Output Preview */
.notice-preview {
    margin-top: 32px;
    border: 1px solid var(--border);
    background: var(--gray-50);
}
.notice-preview summary {
    padding: 16px;
    cursor: pointer;
    font-weight: 500;
    font-size: 14px;
    border-bottom: 1px solid var(--border);
    background: var(--bg);
}
#notice-text {
    padding: 24px;
    font-family: 'Georgia', serif;
    font-size: 14px;
    line-height: 1.8;
    color: var(--fg);
    white-space: pre-wrap;
    background: var(--bg);
    overflow-x: auto;
}

/* Success Card */
.success-card h2 { text-transform: uppercase; letter-spacing: 0.05em; font-size: 20px;}
.success-icon {
    font-size: 40px;
    margin-bottom: 16px;
    text-align: center;
}

/* Info Boxes */
.info-box {
    background: var(--gray-50);
    border: 1px dashed var(--gray-400);
    padding: 24px;
    margin-bottom: 24px;
}
.info-box h3 { margin-bottom: 16px; font-size: 18px; }
.info-box ol { margin-left: 20px; font-size: 14px; line-height: 1.8; color: var(--gray-800); }
.info-box ol li { margin-bottom: 8px; }

/* Upsell box */
.upsell-box {
    margin-top: 24px;
    padding-top: 24px;
    border-top: 1px solid var(--border);
}
.upsell-box p {
    font-size: 13px;
    margin-bottom: 16px;
    color: var(--gray-600);
}

/* Timeline */
.status-timeline { margin: 24px 0; border-left: 2px solid var(--border); padding-left: 16px; }
.status-step { margin-bottom: 16px; font-size: 14px; position: relative; color: var(--gray-500); }
.status-step.done { color: var(--fg); }
.status-step.active { color: var(--fg); font-weight: 600; }
.status-step .dot {
    position: absolute; left: -22px; top: 4px; width: 10px; height: 10px;
    background: var(--bg); border: 2px solid var(--border); border-radius: 50%;
}
.status-step.done .dot { background: var(--fg); border-color: var(--fg); }
.status-step.active .dot { background: var(--bg); border-color: var(--fg); }

/* Actual exact error class names from HTML */
.error-overlay {
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(255,255,255,0.95);
    display: flex; align-items: center; justify-content: center;
    z-index: 1000;
}
.error-box {
    background: var(--bg);
    border: 1px solid var(--error);
    padding: 32px;
    max-width: 400px;
    width: 90%;
}
.error-box h3 { color: var(--error); font-size: 16px; margin-bottom: 16px; text-transform: uppercase; }
.error-box p { font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: var(--gray-800); margin-bottom: 24px; word-break: break-all;}

/* Loading Card */
.loading-card { text-align: center; padding: 60px 20px; }
.loading-card h2 { margin-bottom: 32px; }
.gen-progress-track {
    width: 100%; height: 4px; background: var(--gray-200); margin-bottom: 16px; overflow: hidden;
}
.gen-progress-fill {
    width: 0%; height: 100%; background: var(--fg); transition: width 0.3s ease;
}
.gen-progress-meta {
    display: flex; justify-content: space-between; font-family: 'IBM Plex Mono', monospace; font-size: 11px; text-transform: uppercase; color: var(--gray-500);
}
"""
    with open('static/style.css', 'a', encoding='utf-8') as f:
        f.write(append_css)
