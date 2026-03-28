import re

with open("src/legaltech/services/database.py", "r", encoding="utf-8") as f:
    text = f.read()

# Docstring / general replace
text = text.replace("import aiosqlite", "import asyncpg\nfrom contextlib import asynccontextmanager")
text = text.replace("import sqlite3\n", "")
text = text.replace("_db: aiosqlite.Connection | None = None", "_db: asyncpg.Pool | None = None")
text = text.replace("pdf_data        BLOB", "pdf_data        BYTEA")

# Remove S3 logic completely
text = re.sub(r'# ── S3 persistence ─.*?_SCHEMA = """', '# ── Schema ───────────────────────────────────────────────────────────\n\n_SCHEMA = """', text, flags=re.DOTALL)

# Replace connection and pool stuff
pool_logic = """async def init_db():
    global _db
    if _db is not None:
        return
    import os
    db_url = os.getenv("DATABASE_URL", "postgresql://localhost/legaltech")
    _db = await asyncpg.create_pool(db_url)
    async with _db.acquire() as conn:
        await conn.execute(_SCHEMA)

async def close_db():
    global _db
    if _db is not None:
        await _db.close()
        _db = None

@asynccontextmanager
async def get_db():
    if _db is None:
        await init_db()
    async with _db.acquire() as conn:
        yield conn
"""
text = re.sub(r'async def _commit_and_sync.*?_db = None', pool_logic, text, flags=re.DOTALL)

text = re.sub(r'async def get_db\(\).*?\n    return _db', '', text, flags=re.DOTALL)
text = re.sub(r'async def _init_tables.*?\n\n\n?', '', text, flags=re.DOTALL)

text = text.replace("await db.commit()", "")
text = text.replace("await _commit_and_sync(db)", "")

# Now let's carefully replace the execute calls. 
# It's better to find `await (await db.execute(...)` as blocks manually

def process_query_execution(text):
    # This loop targets `await (await db.execute( QUERY , ARGS )).fetchone()` or `fetchall()`
    import re
    # We find "await (await db.execute(" and look for matching parens.
    idx = 0
    while True:
        idx = text.find("await (await db.execute(", idx)
        if idx == -1: break
        
        # find matching parenthesis for the outer `await (` 
        # i.e., skip past `db.execute( ... )`
        open_parens = 1
        i = idx + len("await (")
        while i < len(text) and open_parens > 0:
            if text[i] == '(': open_parens += 1
            elif text[i] == ')': open_parens -= 1
            i += 1
            
        # i is now right after `))` 
        # let's see if there's `.fetchone()` or `.fetchall()`
        rest = text[i:]
        method = ""
        fetch_len = 0
        if rest.startswith(".fetchone()"):
            method = "fetchrow"
            fetch_len = len(".fetchone()")
        elif rest.startswith(".fetchall()"):
            method = "fetch"
            fetch_len = len(".fetchall()")
        else:
            idx += 1
            continue
            
        # Extract the contents of execute(...)
        inner_content = text[idx + len("await (await db.execute("): i - 2]
        
        # inner_content contains `QUERY, (ARGS)`
        # Let's fix up `?` in inner_content to `$1`, `$2`
        # We only want to replace `?` inside strings.
        parts = inner_content.split('?')
        fixed_inner = parts[0]
        for p_idx in range(1, len(parts)):
            fixed_inner += f"${p_idx}" + parts[p_idx]
            
        # Also unwrapping the tuple if args exist
        # A simple hack: asyncpg will just take *args instead of (args).
        # We can change `query, (arg1, arg2)` to `query, arg1, arg2` by removing the last surrounding parens 
        # separated by comma.
        arg_split = fixed_inner.rsplit(',', 1)
        if len(arg_split) == 2:
            left, right = arg_split
            right = right.strip()
            if right.startswith('(') and right.endswith(')'):
                right = right[1:-1]
            # remove trailing comma inside right if it was like (email,)
            if right.endswith(','): right = right[:-1]
            fixed_inner = left + ", " + right
            
        new_str = f"await db.{method}({fixed_inner})"
        
        text = text[:idx] + new_str + text[i + fetch_len:]
        
    return text

text = process_query_execution(text)

def process_simple_execute(text):
    idx = 0
    while True:
        idx = text.find("await db.execute(", idx)
        if idx == -1: break
        
        open_parens = 1
        i = idx + len("await db.execute(")
        while i < len(text) and open_parens > 0:
            if text[i] == '(': open_parens += 1
            elif text[i] == ')': open_parens -= 1
            i += 1
            
        inner_content = text[idx + len("await db.execute("): i - 1]
        
        # fix ? 
        parts = inner_content.split('?')
        fixed_inner = parts[0]
        for p_idx in range(1, len(parts)):
            fixed_inner += f"${p_idx}" + parts[p_idx]
            
        arg_split = fixed_inner.rsplit(',', 1)
        if len(arg_split) == 2:
            left, right = arg_split
            right = right.strip()
            if right.startswith('(') and right.endswith(')'):
                right = right[1:-1]
            if right.endswith(','): right = right[:-1]
            fixed_inner = left + ", " + right
            
        if "PRAGMA" in fixed_inner:
            new_str = 'pass'
        else:
            new_str = f"await db.execute({fixed_inner})"
            
        text = text[:idx] + new_str + text[i:]
        
    return text

text = process_simple_execute(text)

with open("src/legaltech/services/database.py", "w", encoding="utf-8") as f:
    f.write(text)
