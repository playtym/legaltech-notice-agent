with open('static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

style_override = """
    <style>
        @media (min-width: 900px) {
            .tier-grid { grid-template-columns: repeat(3, 1fr) !important; gap: 16px !important; }
        }
        @media (max-width: 899px) {
            .tier-grid { grid-template-columns: 1fr !important; }
        }
    </style>
</head>
"""

html = html.replace('</head>', style_override)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
