with open('static/style.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Make the fallback logo slightly smaller so it doesn't take up too much vertical space
css = css.replace('width: 160px; height: 160px;', 'width: 100px; height: 100px;')

# Reduce the font size of the text in the logo proportionally
css = css.replace('.sun-text.top, .sun-text.bot { color: var(--red); font-size: 28px; }', 
                  '.sun-text.top, .sun-text.bot { color: var(--red); font-size: 18px; }')
css = css.replace('.sun-text.mid {\n color: var(--orange-dark); font-size: 22px; }', 
                  '.sun-text.mid {\n color: var(--orange-dark); font-size: 14px; }')

# Reduce hero padding from 40px 20px 80px to something tighter
css = css.replace('padding: 40px 20px 80px;', 'padding: 30px 20px 40px;')

# Reduce logo margin
css = css.replace('margin-bottom: 28px;', 'margin-bottom: 16px;')

with open('static/style.css', 'w', encoding='utf-8') as f:
    f.write(css)
