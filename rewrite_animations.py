import re

with open('static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Remove the previously injected polish block if it exists so we can replace cleanly
html = re.sub(r'/\* ---- EXTRA POLISH & ANIMATIONS ---- \*/.*?</style>', '</style>', html, flags=re.DOTALL)

# Add the much safer keyframe-based transition and the rest of the polish
extra_css = """
/* ---- EXTRA POLISH & ANIMATIONS ---- */

/* Step Transitions via Keyframes (Safe for display:none/block) */
@keyframes stepFadeIn {
    0% {
        opacity: 0;
        transform: translateY(12px) scale(0.995);
    }
    100% {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}
.step.active {
    animation: stepFadeIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards !important;
}

/* App Container (Card) Subtly refined shadow and floating effect */
.step .card {
    transition: box-shadow 0.3s ease, transform 0.3s ease;
}
.step .card:hover {
    box-shadow: 0 30px 60px -12px rgba(229, 231, 235, 0.6) !important;
}

/* Beautiful Input Focus & Hover */
.step input[type="text"], .step input[type="url"], .step input[type="email"], 
.step input[type="tel"], .step input[type="date"], .step select, 
.step textarea:not(.composer textarea) {
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
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
    transform: translateY(-2px) !important;
}

/* Primary Button Polish */
.step button.btn-primary, .step .btn-primary {
    position: relative !important;
    overflow: hidden !important;
    letter-spacing: -0.01em !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
}
.step button.btn-primary:active {
    transform: translateY(1px) !important;
    box-shadow: 0 2px 4px -2px rgba(0, 0, 0, 0.1) !important;
}

/* Secondary Button Edge Polish */
.step button.btn-secondary, .step .btn-secondary {
    transition: all 0.2s ease !important;
}
.step button.btn-secondary:hover, .step .btn-secondary:hover {
    border-color: #9ca3af !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
    transform: translateY(-1px) !important;
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
    vertical-align: bottom;
    animation: terminalPulse 1.2s infinite;
}

/* Improved Chips */
.step .quick-chips .chip {
    box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
    border: 1px solid #e5e7eb !important;
}
.step .quick-chips .chip:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 8px rgba(0,0,0,0.04) !important;
    border-color: #d1d5db !important;
}
.step .quick-chips .chip:active {
    transform: translateY(0) !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
}

/* Loading Spinner Polish */
.loader-lg {
    border: 3px solid rgba(0,0,0,0.05) !important;
    border-top-color: #000000 !important;
    animation: spin 1s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite !important;
}

/* Progress bar transitions */
.progress-steps .p-step span {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.progress-steps .p-step.active span {
    transform: scale(1.1) !important;
    box-shadow: 0 0 0 4px rgba(17, 24, 39, 0.1) !important;
}
"""

html = html.replace('</style>', extra_css + '\n</style>', 1)
with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Rewritten UI Polish CSS applied to index.html successfully.")
