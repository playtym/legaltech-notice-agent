import re

with open("src/legaltech/services/database.py", "r", encoding="utf-8") as f:
    text = f.read()

# Replace aiosqlite with asyncpg
text = text.replace("import aiosqlite\n", "import asyncpg\n")
text = text.replace("import sqlite3\n", "")
text = text.replace("_db: aiosqlite.Connection | None = None", "_db: asyncpg.Pool | None = None")

# Remove S3 stuff
text = re.sub(r'# ── S3 persistence ─+.*?(_SCHEMA = )', r'\1', text, flags=re.DOTALL)

# Handle db.execute(...).fetchone/fetchall/etc
# Instead of Regex we will replace the `get_db()` and `close_db()`
init_stuff = """async def init_db():
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

from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db():
    if _db is None:
        await init_db()
    async with _db.acquire() as conn:
        yield conn
"""

text = re.sub(r'async def _commit_and_sync.*?return _db', init_stuff, text, flags=re.DOTALL)

# Replace execute(...)
def replace_query(match):
    prefix = match.group(1)
    func_name = match.group(2)
    query_string = match.group(3)
    args = match.group(4)
    suffix = match.group(5)

    if args:
        # replace ? with $1, $2 inside query_string
        qparts = query_string.split("?")
        if len(qparts) > 1:
            query_string = qparts[0]
            for i in range(1, len(qparts)):
                query_string += f"${i}" + qparts[i]
    
    if suffix == ".fetchone()":
        call_method = "fetchrow"
    elif suffix == ".fetchall()":
        call_method = "fetch"
    else: # e.g. .execute() or .commit()
        call_method = "execute"
        if "PRAGMA" in query_string:
            return "" # remove PRAGMA calls

    # Now reconstruct the line
    if args:
        return f"{prefix}await db.{call_method}({query_string}, {args})"
    else:
        return f"{prefix}await db.{call_method}({query_string})"

# We match: `await (await db.execute( QUERY , ARGS )).fetchone()`
# Note: we need to handle variations.
text = re.sub(r'(^|\s|\[|\=|\()await \(await db\.(execute)\((.*?)(?:,\s*(.*?))?\)\)(\.fetchone\(\)|\.fetchall\(\))',
              replace_query, text)

# We match: `await db.execute( QUERY , ARGS )` without fetchone/fetchall
text = re.sub(r'(^|\s|\[|\=|\()await db\.(execute)\((.*?)(?:,\s*(.*?))?\)(?!\.fetch)',
              replace_query, text)

# There are counts that look like: `(await db.fetchrow("SELECT COUNT(...)"))[0]`
text = text.replace("db.commit()", "pass") # asyncpg is autocommit by default or within transactions

with open("src/legaltech/services/database.py.new", "w", encoding="utf-8") as f:
    f.write(text)

print("done")
