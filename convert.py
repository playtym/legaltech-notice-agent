import re

with open("src/legaltech/services/database.py", "r") as f:
    content = f.read()

# 1. Strip S3 junk
s3_junk = re.compile(r"# ── S3 persistence ───────────────────────────────────────────────────.*?(?=_SCHEMA =)", re.DOTALL)
content = s3_junk.sub("", content)

# 2. Change aiosqlite to asyncpg
content = content.replace("import aiosqlite", "import asyncpg")
content = content.replace("_db: aiosqlite.Connection | None = None", "_db: asyncpg.Pool | None = None")

def convert_q_to_dollar(match):
    query = match.group(1)
    args_str = match.group(2)
    # replace ? with $1, $2 inside query
    # It's better to just write a simple replacer for ? inside a string
    parts = query.split("?")
    new_q = parts[0]
    for i in range(1, len(parts)):
        new_q += f"${i}" + parts[i]
    return f"await db.execute({new_q}, {args_str})"

# Actually, asyncpg uses `fetchrow` instead of `.fetchone()`
# and `fetch` instead of `.fetchall()`.

with open("convert.py", "w") as f:
    f.write("import re")
