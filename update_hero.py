import re

with open('static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

hero_match = re.search(r'<div class="hero".*?</section>', text, re.DOTALL)
if hero_match:
    flat_hero = """<div class="hero" style="text-align: center;">
        <h1 style="font-size: 32px; font-weight: 600; margin-bottom: 8px; text-transform: uppercase; letter-spacing: -0.02em; color: var(--fg);">Legal Notice Matrix</h1>
        <p class="card-sub" style="font-size: 15px; margin-bottom: 32px; color: var(--gray-600); max-width: 480px; margin-left: auto; margin-right: auto;">An autonomous intelligence pipeline for extracting factual data, evaluating against consumer protection statutes, and synthesizing court-ready legal notices.</p>
        <button class="btn btn-primary" onclick="App.goTo(2)" style="font-size: 13px; padding: 14px 28px; width: auto; margin: 0 auto; display: inline-flex;">INITIALIZE_WORKFLOW() &rarr;</button>
        <div style="margin-top: 48px; border-top: 1px solid var(--border); padding-top: 24px; font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: var(--gray-400); text-align: center;">
            <p>SYSTEM OK &middot; JURISDICTION: IN &middot; PROTOCOL: CPA-2019</p>
        </div>
    </div>
</section>"""
    text = text[:hero_match.start()] + flat_hero + text[hero_match.end():]
    
    with open('static/index.html', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Hero updated")
else:
    print("Hero not found")
