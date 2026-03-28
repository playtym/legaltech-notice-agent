import argparse
import os
import json

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-F63GR76DSR"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', 'G-F63GR76DSR');
    </script>
    <title>{title} | Lawly</title>
    <meta name="description" content="{description}">
    <link rel="canonical" href="https://lawly.store/{slug}">
    <meta property="og:title" content="{title} | Lawly">
    <meta property="og:description" content="{description}">
    <meta property="og:image" content="https://lawly.store/img/lawly-og.png">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:image" content="https://lawly.store/img/lawly-og.png">
    <meta property="og:url" content="https://lawly.store/{slug}">
    <meta property="og:type" content="website">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/styles.css">
    {schema_markup}
</head>
<body class="bg-gray-50 text-gray-900 font-sans antialiased">
    <nav class="bg-white border-b border-gray-100 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16">
                <div class="flex">
                    <div class="flex-shrink-0 flex items-center">
                        <a href="/" class="text-2xl font-bold text-indigo-600 tracking-tight">Lawly</a>
                    </div>
                </div>
                <div class="flex items-center space-x-4">
                    <a href="/app" class="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm transition-colors duration-200">
                        Draft Legal Notice
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <article class="prose prose-indigo max-w-none">
            <h1 class="text-4xl font-extrabold tracking-tight text-gray-900 mb-6">{h1}</h1>
            <div class="text-lg text-gray-600 mb-8">
                {content}
            </div>
            
            {faq_html}
            
            <div class="bg-indigo-50 border border-indigo-100 rounded-xl p-8 mt-12 text-center">
                <h2 class="text-2xl font-bold text-gray-900 mb-4">Ready to take legal action?</h2>
                <p class="text-gray-600 mb-6">Send a legally sound pre-litigation notice in minutes without a lawyer.</p>
                <a href="/app" class="inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm transition-colors duration-200">
                    Draft a Legal Notice Now
                </a>
            </div>
        </article>
    </main>

    <footer class="bg-white border-t border-gray-100 mt-16">
        <div class="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
            <p class="text-center text-sm text-gray-500">&copy; 2026 Lawly. All rights reserved.</p>
        </div>
    </footer>
</body>
</html>
"""

def generate_page(slug, title, description, h1, content, faqs=None):
    schema_markup = ""
    faq_html = ""
    
    if faqs and len(faqs) > 0:
        schema_obj = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": []
        }
        
        faq_html = '<div class="mt-12"> <h2 class="text-2xl font-bold text-gray-900 mb-6">Frequently Asked Questions</h2> <div class="space-y-6"> '
        
        for q, a in faqs:
            schema_obj["mainEntity"].append({
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": a
                }
            })
            faq_html += f'<div class="bg-white p-6 rounded-lg shadow-sm border border-gray-100"> <h3 class="text-lg font-semibold text-gray-900 mb-2">{q}</h3> <p class="text-gray-600">{a}</p> </div>'
        
        faq_html += '</div></div>'
        schema_markup = f'<script type="application/ld+json">\n{json.dumps(schema_obj, indent=2)}\n</script>'
        
    filename = f"static/{slug}.html"
    html_content = TEMPLATE.format(
        slug=slug,
        title=title,
        description=description,
        h1=h1,
        content=content,
        schema_markup=schema_markup,
        faq_html=faq_html
    )
    
    with open(filename, 'w') as f:
        f.write(html_content)
        
    print(f"✅ Created page: {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a new landing page for Lawly")
    parser.add_argument("--slug", required=True, help="URL slug")
    parser.add_argument("--title", required=True, help="SEO Title tag")
    parser.add_argument("--desc", required=True, help="SEO Description")
    parser.add_argument("--h1", required=True, help="Main H1 heading")
    parser.add_argument("--content", required=True, help="Main body content")
    
    args = parser.parse_args()
    generate_page(args.slug, args.title, args.desc, args.h1, args.content)
