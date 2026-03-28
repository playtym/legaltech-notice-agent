import re

with open('static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# I want to append some high-quality polished CSS into the existing <style> block for APP UI REDESIGN
extra_css = """
/* ---- EXTRA POLISH & ANIMATIONS ---- */

/* Step Transitions */
.step {
    opacity: 0 !important;
    transform: translateY(8px) scale(0.99) !important;
    transition: opacity 0.4s cubic-bezier(0.16, 1, 0.3, 1), transform 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
    pointer-events: none !important;
}
.step.active {
    opacity: 1 !important;
    transform: translateY(0) scale(1) !important;
    pointer-events: auto !important;
}

/* Beautiful Input Focus & Hover */
.step input[type="text"]:hover, .step input[type="url"]:hover, .step input[type="email"]:hover, 
.step input[type="tel"]:hover, .step input[type="date"]:hover, .step select:hover, 
.step textarea:not(.composer textarea):hover {
    border-color: #d1d5db !important;
}

.step input[type="text"]:focus, .step input[type="url"]:focus, .step input[type="email"]:focus, 
.step input[type="tel"]:focus, .step input[type="date"]:focus, .step select:focus, 
.step textarea:not(.composer textarea):focus {
    background-color: #ffffff !important;
    border-color: #000000 !important;
    box-shadow: 0 0 0 4px rgba(0,0,0,0.05) !important;
    transform: translateY(-1px) !important;
}

/* Primary Button Polish */
.step button.btn-primary, .step .btn-primary {
    position: relative !important;
    overflow: hidden !important;
    letter-spacing: -0.01em !important;
}
.step button.btn-primary::after {
    content: '' !important;
    position: absolute !important;
    top: 50% !important;
    left: 50% !important;
    width: 300% !important;
    height: 300% !important;
    background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 60%) !important;
    transform: translate(-50%, -50%) scale(0) !important;
    opacity: 0 !important;
    transition: transform 0.5s ease-out, opacity 0.5s ease-out !important;
}
.step button.btn-primary:active::after {
    transform: translate(-50%, -50%) scale(1) !important;
    opacity: 1 !important;
    transition: 0s !important;
}

/* Secondary Button Edge Polish */
.step button.btn-secondary:hover, .step .btn-secondary:hover {
    border-color: #9ca3af !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
}

/* Terminal Pulse Cursor */
@keyframes terminalPulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
}
.step .analysis-box h3::after, .step .review-doc h3::after {
    content: '_';
    display: inline-block;
    margin-left: 6px;
    color: #60a5fa;
    font-weight: 900;
    animation: terminalPulse 1.2s infinite;
}

/* Improved Chips */
.step .quick-chips .chip {
    box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
}
.step .quick-chips .chip:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 3px 6px rgba(0,0,0,0.04) !important;
}

/* Fix Display issues with steps where app sets display none initially */
.step {
    display: none; /* App relies on this */
}
.step.active {
    display: block; /* So it fades in properly while visible */
}

"""

if '/* ---- EXTRA POLISH & ANIMATIONS ---- */' not in html:
    html = html.replace('</style>', extra_css + '\n</style>', 1)
    with open('static/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Added UI Polish CSS to index.html")
else:
    print("UI Polish already added")
