import re

with open('static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Make sure head links the new fonts
if 'Space Grotesk' not in text:
    text = re.sub(
        r'</title>',
        '</title>\n    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">\n',
        text
    )

text = text.replace('class="btn btn-secondary btn-ghost"', 'class="btn btn-outline"')
text = text.replace('class="btn btn-ghost"', 'class="btn btn-outline"')
text = text.replace('class="btn btn-primary btn-lg"', 'class="btn btn-primary"')
text = text.replace('class="btn btn-lg btn-block"', 'class="btn btn-block btn-primary"')
text = text.replace('class="btn-row"', 'class="nav-buttons"')
text = text.replace('class="spinner"', 'class="custom-loader"')
text = text.replace('class="card loading-card"', 'class="loading-view"')
text = text.replace('class="gen-progress-wrap"', 'class="loading-text"')

# Replace progress bar classes
text = text.replace('class="progress-bar hidden"', 'class="progress-bar hidden" id="progress-bar"')

# Clean up emojis from headers
text = re.sub(r'<h2>(.*?)</h2>', 
              lambda m: '<h2>' + m.group(1).replace('🎯', '').replace('📝', '').replace('📊', '').replace('📄', '').replace('📋', '').replace('⚖️', '').strip() + '</h2>', 
              text)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
