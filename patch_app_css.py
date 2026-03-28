import re

with open("static/index.html", "r", encoding="utf-8") as f:
    text = f.read()

app_override_css = """
<!-- --- APP UI REDESIGN: Matching "Intelligence Layer" Terminal Vibe --- -->
<style>
/* Base Step Background */
.step {
    background-color: #f9fafb !important; /* bg-gray-50 */
}

/* Make the overall App Container look like the terminal window */
.step .card {
    background-color: #ffffff !important;
    border-radius: 24px !important;
    box-shadow: 0 25px 50px -12px rgba(229, 231, 235, 0.5) !important;
    border: 1px solid #e5e7eb !important;
    overflow: hidden !important;
    max-width: 800px !important;
    margin: 40px auto 100px auto !important;
    padding: 0 !important;
}

/* Headers */
.step .card-header {
    background-color: #ffffff !important;
    border-bottom: 1px solid #f3f4f6 !important;
    padding: 32px 40px !important;
}
.step .card-header h2, .step .step-title {
    font-family: ui-sans-serif, system-ui, sans-serif !important;
    font-size: 1.5rem !important;
    font-weight: 600 !important;
    color: #111827 !important;
    letter-spacing: -0.025em;
    margin-bottom: 8px !important;
}
.step .card-header .card-sub, .step .step-desc {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
    color: #9ca3af !important;
    font-size: 0.75rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Form Area */
.step form, .step .split-layout {
    padding: 40px !important;
    background-color: #ffffff !important;
}
.step .form-group {
    margin-bottom: 24px !important;
}
.step .form-group label {
    font-family: ui-sans-serif, system-ui, sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    color: #374151 !important;
    margin-bottom: 12px !important;
    display: block !important;
}

/* Inputs */
.step input[type="text"], .step input[type="url"], .step input[type="email"], .step input[type="tel"], .step input[type="date"], .step select, .step textarea {
    background-color: #f9fafb !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 12px !important;
    padding: 16px !important;
    font-family: ui-sans-serif, system-ui, sans-serif !important;
    font-size: 1rem !important;
    color: #111827 !important;
    width: 100% !important;
    box-shadow: none !important;
    transition: all 0.2s ease !important;
}
.step input:focus, .step textarea:focus, .step select:focus {
    background-color: #ffffff !important;
    border-color: #111827 !important;
    box-shadow: 0 0 0 1px #111827 !important;
    outline: none !important;
}
.step .hint, .step small {
    font-family: ui-monospace, monospace !important;
    font-size: 0.75rem !important;
    color: #9ca3af !important;
    margin-top: 8px !important;
    display: block;
}

/* Chips Map to clean buttons */
.step .quick-chips .chip {
    background: #f9fafb !important;
    border: 1px solid #e5e7eb !important;
    color: #4b5563 !important;
    border-radius: 8px !important;
    padding: 8px 16px !important;
    font-family: ui-sans-serif, system-ui, sans-serif !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}
.step .quick-chips .chip:hover {
    background: #f3f4f6 !important;
    color: #111827 !important;
    border-color: #d1d5db !important;
}
.step .quick-chips .chip.active {
    background: #111827 !important;
    color: #ffffff !important;
    border-color: #111827 !important;
}

/* Progress bar redesign */
.progress-bar {
    background: rgba(255, 255, 255, 0.8) !important;
    backdrop-filter: blur(12px) !important;
    border-bottom: 1px solid #f3f4f6 !important;
}
.progress-steps .p-step span {
    background: #f3f4f6 !important;
    color: #9ca3af !important;
    border: none !important;
    font-weight: 600 !important;
    font-family: ui-monospace, monospace !important;
}
.progress-steps .p-step.active span {
    background: #111827 !important;
    color: #ffffff !important;
}
.progress-steps .p-step small {
    color: #6b7280 !important;
    font-family: ui-sans-serif, system-ui, sans-serif !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-size: 0.65rem !important;
}
.progress-steps .p-step.active small {
    color: #111827 !important;
    font-weight: 700 !important;
}

/* TERMINAL AGENT OUTPUT LOGS IN THE APP (Converting analysis boxes to dark mode terminal) */
.step .analysis-box, .step .review-doc {
    background-color: #111827 !important; /* gray-900 */
    color: #d1d5db !important; /* gray-300 */
    font-family: ui-monospace, SFMono-Regular, monospace !important;
    border-radius: 16px !important;
    padding: 32px !important;
    border: none !important;
    margin-bottom: 24px !important;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.2) !important;
}
.step .analysis-box h3, .step .review-doc h3 {
    color: #60a5fa !important; /* blue-400 */
    text-transform: uppercase !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.1em !important;
    margin-bottom: 24px !important;
    font-weight: 700 !important;
    display: flex;
    align-items: center;
    gap: 8px;
}
.step .analysis-box h3::before, .step .review-doc h3::before {
    content: '';
    display: inline-block;
    width: 8px;
    height: 8px;
    background-color: #60a5fa;
    border-radius: 50%;
    box-shadow: 0 0 0 2px rgba(96, 165, 250, 0.2);
}
.step .analysis-box .finding {
    border-left: 2px solid #374151 !important;
    padding-left: 16px !important;
    background: transparent !important;
    margin-bottom: 16px !important;
}
.step .analysis-box .finding strong {
    color: #ffffff !important;
    font-weight: 600 !important;
}
.step .analysis-box .badge {
    background: #1f2937 !important;
    color: #9ca3af !important;
    border: 1px solid #374151 !important;
}

/* Action Buttons */
.step .actions {
    padding: 32px 40px !important;
    background: #ffffff !important;
    border-top: 1px solid #f3f4f6 !important;
    border-radius: 0 0 24px 24px !important;
    margin: 0 !important;
    display: flex !important;
    gap: 16px !important;
}
.step button.btn-primary, .step .btn-primary {
    background-color: #111827 !important;
    color: #ffffff !important;
    font-family: ui-sans-serif, system-ui, sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    padding: 16px 32px !important;
    border-radius: 12px !important;
    border: none !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
    transition: all 0.2s ease !important;
    cursor: pointer !important;
}
.step button.btn-primary:hover {
    background-color: #000000 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05) !important;
}
.step button.btn-secondary, .step .btn-secondary {
    background-color: #ffffff !important;
    color: #374151 !important;
    font-family: ui-sans-serif, system-ui, sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    padding: 16px 32px !important;
    border-radius: 12px !important;
    border: 1px solid #e5e7eb !important;
    box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
    transition: all 0.2s ease !important;
    cursor: pointer !important;
}
.step button.btn-secondary:hover {
    background-color: #f9fafb !important;
    color: #111827 !important;
}
</style>
"""

if "</head>" in text and "<!-- --- APP UI REDESIGN" not in text:
    text = text.replace("</head>", app_override_css + "\n</head>")
    with open("static/index.html", "w", encoding="utf-8") as f:
        f.write(text)
    print("Injected CSS overrides for the app UI!")
else:
    print("Already modified or head not found.")
