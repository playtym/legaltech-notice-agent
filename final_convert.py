import re

with open("src/legaltech/services/database.py", "r", encoding="utf-8") as f:
    text = f.read()

# Docstring / general replace
text = text.replace("import aiosqlite", "import asyncpg\nfrom contextlib import asynccontextmanager")
text = text.replace("import sqlite3", "")
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
text = re.sub(r'async def _commit_and_sync\(.*?\).*?_db = None', pool_logic, text, flags=re.DOTALL)
text = re.sub(r'def _now\(\) -> str:\n\s+return datetime\.now\(timezone\.utc\)\.strftime\("%Y-%m-%dT%H:%M:%SZ"\)', 'def _now() -> str:\n    return datetime.now(timezone.utc).isoformat()', text)
text = re.sub(r'async def get_db.*?\n    return _db\n', '', text, flags=re.DOTALL)
text = re.sub(r'async def _init_tables.*?\n\n\n?', '', text, flags=re.DOTALL)

# Let's fix DB execution replacements with a more careful parser
def fix_db_calls(code):
    import ast
    # Instead of full AST, we can just find and replace using regex line by line
    # Actually wait, AST is perfectly reliable.
    return code

# We won't use AST, regex is good enough if done in a targeted way inside string literals:
def fix_q_marks(q):
    parts = q.split("?")
    if len(parts) == 1:
        return q
    out = parts[0]
    for i in range(1, len(parts)):
        out += f"${i}" + parts[i]
    return out

# 1. db.execute returning tuple replacing
def repl_fetchone(m):
    q = fix_q_marks(m.group(1))
    args = m.group(2)
    new_call = f"await db.fetchrow({q}"
    if args: new_call += f", {args}"
    new_call += ")"
    return new_call

text = re.sub(r'await \(await db\.execute\((.*?)(?:,\s*(.*?))?\)\)\.fetchone\(\)', repl_fetchone, text)

# 2. handle newlines in fetchall: await (await db.execute(...)).fetchall() where it can span lines
def repl_fetchall(m):
    q = fix_q_marks(m.group(1))
    args = m.group(2)
    new_call = f"await db.fetch({q}"
    if args: new_call += f", {args}"
    new_call += ")"
    return new_call

text = re.sub(r'await \(await db\.execute\((.*?)(?:,\s*(.*?))?\)\)\.fetchall\(\)', repl_fetchall, text, flags=re.DOTALL)

# 3. simple execute
def repl_execute(m):
    q = fix_q_marks(m.group(1))
    args = m.group(2)
    if "PRAGMA" in q: return ""
    new_call = f"await db.execute({q}"
    if args: new_call += f", {args}"
    new_call += ")"
    return new_call

text = re.sub(r'await db\.execute\((.*?)(?:,\s*(.*?))?\)(?!\.fetch)', repl_execute, text)

# 4. Remove db.commit() and _upload_db_to_s3 calls
text = re.sub(r'await db\.commit\(\)\n', '\n', text)
text = re.sub(r'await _commit_and_sync\(db\)\n', '\n', text)

# There are some tuples dynamically passed with variables, e.g. `await db.execute(..., (a, b))` -> `await db.execute(..., a, b)`
# asyncpg expects arguments like fetchrow(query, a, b) instead of fetchrow(query, (a,b)) for parameter binding.
def unwrap_tuple_args(m):
    prefix = m.group(1)
    args = m.group(2)
    # args might be like `(a, b)`
    if args.startswith("(") and args.endswith(")"):
        # strip outer parens, but watch out for `(a, )` which becomes `a, `
        args_inner = args[1:-1]
        if args_inner.endswith(","):
            args_inner = args_inner[:-1]
        if args_inner.strip():
            return f"{prefix}, {args_inner})"
    return m.group(0)

text = re.sub(r'(await db\.(?:fetch|fetchrow|execute)\([^,]*)((?:,\s*\(.*?\)))\)', unwrap_tuple_args, text, flags=re.DOTALL)

with open("src/legaltech/services/database.py", "w", encoding="utf-8") as f:
    f.write(text)
