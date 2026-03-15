import re

with open('static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Remove inline style tags that we want to control via CSS
html = re.sub(r'style="[^"]*"', '', html)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
