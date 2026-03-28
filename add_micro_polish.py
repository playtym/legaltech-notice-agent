import re

with open('static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

extra_css = """
/* Selection & Placeholders */
::selection {
    background: #111827 !important;
    color: #ffffff !important;
}
::-moz-selection {
    background: #111827 !important;
    color: #ffffff !important;
}

.step input::placeholder, .step textarea::placeholder {
    color: #9ca3af !important;
    transition: opacity 0.3s ease;
}
.step input:focus::placeholder, .step textarea:focus::placeholder {
    opacity: 0.5 !important;
}

/* Crisp Section Dividers */
.step hr.section-divider {
    border: none !important;
    border-top: 1px solid #f3f4f6 !important;
    margin: 32px 0 !important;
}

/* Subtle Label Letter Spacing */
.step .field-label, .step .section-label, .step label {
    letter-spacing: -0.01em !important;
}

/* Form Group Polish */
.step .form-group {
    margin-bottom: 28px !important;
}

/* Enhancing Analysis Checkmarks / Findings */
.step .analysis-box .finding {
    transition: transform 0.2s ease, background-color 0.2s ease;
    border-radius: 8px;
}
.step .analysis-box .finding:hover {
    background-color: rgba(255,255,255,0.02) !important;
    transform: translateX(4px);
    border-left-color: #60a5fa !important;
}
"""

if '/* Selection & Placeholders */' not in html:
    # insert before </style>
    html = html.replace('</style>', extra_css + '\n</style>', 1)
    with open('static/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Added micro-polish details to index.html CSS")
else:
    print("Micro-polish already added")
