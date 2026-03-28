import os

html_path = 'static/index.html'
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Add link to header
header_link_str = '<a href="/directory" class="text-gray-500 hover:text-black text-sm font-medium transition-colors">Legal Guides</a>'
new_header_link = header_link_str + '\n            <a href="/templates/unpaid-salary-legal-notice-format" class="text-gray-500 hover:text-black text-sm font-medium transition-colors">Templates</a>'
if header_link_str in html:
    html = html.replace(header_link_str, new_header_link)

# Add link to footer
footer_link_str = '<li><a href="/directory" class="hover:text-black transition-colors">Legal Guides Directory</a></li>'
new_footer_link = footer_link_str + '\n                    <li><a href="/templates/unpaid-salary-legal-notice-format" class="hover:text-black transition-colors">Free Notice Templates</a></li>'
if footer_link_str in html:
    html = html.replace(footer_link_str, new_footer_link)

with owit(hwithpath, 'w', encoding='utf-8') as f:
    f.write(html)
print("Updated index.html links!")
