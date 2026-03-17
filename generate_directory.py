import glob

files = glob.glob("static/*.html")
entity_links = ""
glossary_links = ""
for f in sorted(files):
    filename = f.split("/")[-1]
    clean_url = filename.replace(".html", "")
    if filename.startswith("legal-notice-against-"):
        title = filename.replace("-", " ").replace(".html", "").title()
        entity_links += f'<li><a href="{clean_url}">{title}</a></li>\n'
    elif filename.startswith("what-is-"):
        title = filename.replace("-", " ").replace(".html", "").title()
        glossary_links += f'<li><a href="{clean_url}">{title}</a></li>\n'

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Legal Notice Directory | Lawly India</title>
    <meta name="description" content="Directory of programmatic legal notice formats against Indian companies and legal glossary.">
    <link rel="canonical" href="https://lawly.store/directory">
    <link rel="alternate" hreflang="en-IN" href="https://lawly.store/directory">
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      "itemListElement": [
        {{
          "@type": "ListItem",
          "position": 1,
          "name": "Lawly India",
          "item": "https://lawly.store"
        }},
        {{
          "@type": "ListItem",
          "position": 2,
          "name": "Legal Resource Directory",
          "item": "https://lawly.store/directory"
        }}
      ]
    }}
    </script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="style.css">
    <link rel="stylesheet" href="use-case.css">
    <style>
        .directory-section ul {{ list-style-type: none; padding: 0; }}
        .directory-section li {{ margin-bottom: 0.5rem; }}
        .directory-section a {{ color: #2563eb; text-decoration: none; font-weight: 500; }}
        .directory-section a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body class="uc-page">
    <div class="uc-container">
        <header class="uc-header">
            <a href="/" class="uc-back">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
                Home
            </a>
            <div class="uc-branding">Lawly</div>
        </header>
        <main class="uc-content">
            <div class="uc-hero">
                <h1>Legal Resource Directory</h1>
                <p class="uc-subtitle">Find legal notice templates against major companies and legal definitions.</p>
            </div>
            <section class="uc-section directory-section">
                <h2>Entity Notices (Programmatic SEO)</h2>
                <ul>
                    {entity_links}
                </ul>
            </section>
            <section class="uc-section directory-section">
                <h2>Legal Glossary</h2>
                <ul>
                    {glossary_links}
                </ul>
            </section>
        </main>
    </div>
    <footer class="uc-footer">
        <div class="uc-footer-inner">
            <a href="/" class="uc-footer-brand">Lawly</a>
            <p>Lawly | Drafting reliable legal notices across India.</p>
            <nav class="uc-footer-links">
                <a href="/">Home</a>
                <a href="/directory">Directory</a>
            </nav>
            <p class="uc-footer-copy">&copy; 2026 Lawly. All rights reserved.</p>
        </div>
    </footer>
</body>
</html>
"""
with open("static/directory", "w") as f:
    f.write(html)
print("Generated directory.html")
