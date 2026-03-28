import os
import re
from datetime import datetime

STATIC_DIR = "static"
BASE_URL = "https://lawly.store"

def extract_title(html_content):
    match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
    if match:
        title = match.group(1).replace(" | Lawly", "").strip()
        return title
    return "Lawly Legal Notice"

def generate_assets():
    html_files = []
    exclude_list = ["admin.html", "about.html", "privacy.html", "contact.html", "refund.html", "blog.html"]
    
    for root, dirs, files in os.walk(STATIC_DIR):
        for filename in files:
            if filename.endswith(".html") and filename not in exclude_list:
                filepath = os.path.join(root, filename)
                
                # compute the slug relative to the STATIC_DIR
                rel_path = os.path.relpath(filepath, STATIC_DIR)
                slug = rel_path.replace('.html', '')
                # replace backslashes with slashes for windows compa   ust in case
                slug = slug.replace('\\\\', '/')
                
                if slug == 'index':
                    slug = ''
                    
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    title = extract_title(content)
                    
                    mtime = os.path.getmtime(filepath)
                    lastmod = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
                    
                    html_files.append({
                        "filename": filename,
                        "slug": slug,
                        "title": title,
                        "lastmod": lastmod
                    })
    
    html_files.sort(key=lambda x: x['title'])

    # 1. Generate sitemap.xml
    sitemap_content = ['<?xml version="1.0" encoding="UTF-8"?>']
    sitemap_content.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    
    for file_info in html_files:
        url = f"{BASE_URL}/{file_info['slug']}" if file_info['slug'] else BASE_URL
        sitemap_content.append('  <url>')
        sitemap_content.append(f'    <loc>{url}</loc>')
        sitemap_content.append(f'    <lastmod>{file_info["lastmod"]}</lastmod>')
        sitemap_content.append(f'    <changefreq>weekly</changefreq>')
        sitemap_content.append('  </url>')
        
    sitemap_content.append('</urlset>')
    
    with open('sitemap.xml', 'w', encoding='utf-8') as f:
        f.write('\\n'.join(sitemap_content))
    print("✅ Created sitemap.xml")

    # 2. Generate directory.html
    directory_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Complaint Directory & Resources | Lawly</title>
    <meta name="description" content="Browse our complete directory of consumer complaints and legal notice templates.">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/styles.css">
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

    <main class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div class="mb-12 text-center">
            <h1 class="text-4xl font-extrabold tracking-tight text-gray-900 mb-4">Consumer Complaint Directory</h1>
            <p class="text-lg text-gray-600">Find the specific consumer complaint guide or legal notice template you need.</p>
        </div>
        
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
"""
    
    for file_info in html_files:
        if file_info['slug'] == "": 
            continue
        url = f"/{file_info['slug']}"
        directory_html += f"""
            <a href="{url}" class="block p-6 bg-white border border-gray-200 rounded-xl hover:border-indigo-500 hover:shadow-md transition duration-200 flex flex-col justify-between h-full">
                <h3 class="text-base font-semibold text-gray-900 mb-4">{file_info['title']}</h3>
                <span class="text-indigo-600 text-sm font-medium flex items-center mt-auto">
                    Read more
                </span>
            </a>"""

    directory_html += """
        </div>
    </main>
</body>
</html>"""

    with open(os.path.join(STATIC_DIR, 'directory.html'), 'w', encoding='utf-8') as f:
        f.write(directory_html)
    print("✅ Created static/directory.html with subdirectories mapping!")

if __name__ == "__main__":
    generate_assets()
