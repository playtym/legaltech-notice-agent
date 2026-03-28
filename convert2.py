import re

with open('src/legaltech/services/database.py') as f:
    code = f.read()

# Replace aiosqlite with asyncpg
code = code.replace('import aiosqlite', 'import asyncpg')
code = code.replace('_db: aiosqlite.Connection | None = None', '_db: asyncpg.Pool | None = None')

# Remove S3 stuff
code = re.sub(r'# ── S3 persistence ─+[\s\S]*?(_SCHEMA = )', r'\1', code)
code = re.sub(r'import boto3\n?', '', code)
code = re.sub(r's3_client = .*?\n', '', code)
code = re.sub(r'S3_BUCKET = .*?\n', '', code)

# We need to change connection string logic in init_db
init_db_replacement = """
async def init_db():
    \"\"\"
    Initialize PostgreSQL connection pool.
    \"\"\"
    global _db
    if _db is not None:
        return
        
    import os
    db_url = os.getenv("DATABASE_URL", "postgresql://localhost/legaltech")
    _db = await asyncpg.create_pool(db_url)
    
    # Initialize schema
    async with _db.acquire() as conn:
        await conn.execute(_SCHEMA)
"""
code = re.sub(r'async def init_db\(\):[\s\S]*?(?=async def get_db\(\):)', init_db_replacement, code)

code = re.sub(r'_db.close\(\)', r'_db.close()', code) # aiosqlite is close(), asyncpg pool is close()

# We need a get_db that yields connections from the pool probably, or just replace use of get_db
# Actually the code uses: async with get_db() as db:
# For asyncpg, it would be: async with _db.acquire() as db:
# Let's fix get_db to return an acquire context manager
get_db_replacement = """
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db():
    \"\"\"
    Get a DB connection from the pool.
    \"\"\"
    global _db
    if _db is None:
        await init_db()
    async with _db.acquire() as conn:
        yield conn
"""
code = re.sub(r'@asynccontextmanager.*?async def get_db\(\):[\s\S]*?(?=async def )', get_db_replacement, code, count=1, flags=re.DOTALL)

# Replace execute(...).fetchone()
def repl_fetchone(m):
    full = m.group(0)
    q = m.group(1)
    args = m.group(2)
    # convert ? to $1, $2
    qparts = q.split('?')
    if len(qparts) > 1:
        nq = qparts[0]
        for i in range(1, len(qparts)):
            nq += f'${i}' + qparts[i]
    else:
        nq = q
    if args: return f'await db.fetchrow({nq}, {args})'
    return f'await db.fetchrow({nq})'

code = re.sub(r'await \(await db\.execute\((.*?)(?:,\s*(.*?))?\)\)\.fetchone\(\)', repl_fetchone, code)

# Replace execute(...).fetchall()
def repl_fetchall(m):
    q = m.group(1)
    args = m.group(2)
    qparts = q.split('?')
    if len(qparts) > 1:
        nq = qparts[0]
        for i in range(1, len(qparts)):
            nq += f'${i}' + qparts[i]
    else:
        nq = q
    if args: return f'await db.fetch({nq}, {args})'
    return f'await db.fetch({nq})'

code = re.sub(r'await \(await db\.execute\((.*?)(?:,\s*(.*?))?\)\)\.fetchall\(\)', repl_fetchall, code)

# Replace execute without fetch
def repl_execute(m):
    q = m.group(1)
    args = m.group(2)
    if q.startswith('PRAGMA'): return '' # strip pragmas
    
    qparts = q.split('?')
    if len(qparts) > 1:
        nq = qparts[0]
        for i in range(1, len(qparts)):
            nq += f'${i}' + qparts[i]
    else:
        nq = q
    if args: return f'await db.execute({nq}, {args})'
    return f'await db.execute({nq})'

code = re.sub(r'await db\.execute\((.*?)(?:,\s*(.*?))?\)', repl_execute, code)

# Also fix the sqlite3 row_factory related imports
code = re.sub(r'import sqlite3\n?', '', code)

with open('src/legaltech/services/database.py.new', 'w') as f:
    f.write(code)
