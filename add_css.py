import sys
with open('static/style.css', 'r') as f:
    text = f.read()
if '.file-thumb' in text:
    text = text[:text.find('.file-thumb')].strip() + '\n'
new_css = """
.file-thumb { width:40px; height:40px; object-fit:cover; border-radius:var(--r-sm); display:flex; align-items:center; justify-content:center; background:var(--blue-bg); color:var(--blue); font-size:20px; flex-shrink:0; }
.file-info { flex:1; overflow:hidden; text-align:left; }
.file-name { font-weight:500; white-space:nowrap; text-overflow:ellipsis; overflow:hidden; }
.file-size { color:var(--text-3); font-size:11px; }
.file-status { font-size:12px; font-weight:600; }
.file-status.done { color:var(--green); }
.file-status.error { color:var(--red); }
.file-status.uploading { color:var(--orange); }
.upload-file-item button { background:none; border:none; font-size:16px; color:var(--text-3); cursor:pointer; padding:4px; border-radius:4px; }
.upload-file-item button:hover { color:var(--red); background:#fee2e2; }
.stage.done::before { content:'\\2713'; display:flex; align-items:center; justify-content:center; color:white; font-size:11px; font-weight:bold; }
"""
with open('static/style.css', 'w') as f:
    f.write(text + '\n' + new_css)
print('Done!')
