import re

with open("src/legaltech/services/database.py", "r") as f:
    code = f.read()

# 1. Update schema
schema_insert = """
CREATE TABLE IF NOT EXISTS system_jobs (
    id          TEXT PRIMARY KEY,
    status      TEXT NOT NULL,
    result_json TEXT,
    error_text  TEXT,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON system_jobs(created_at);
"""

if "system_jobs" not in code:
    code = code.replace('_SCHEMA = """\n', '_SCHEMA = """\n' + schema_insert + '\n')

# 2. Add job functions
job_funcs = """

# ── Jobs ─────────────────────────────────────────────────────────────

async def create_job(job_id: str) -> None:
    db = await get_db()
    await db.execute(
        "INSERT INTO system_jobs (id, status, created_at) VALUES (?, ?, ?)",
        (job_id, "processing", _now())
    )
    await _commit_and_sync(db)

async def update_job_status(job_id: str, status: str, result: dict[str, Any] | None = None, error: str | None = None) -> None:
    db = await get_db()
    res_str = json.dumps(result) if result is not None else None
    await db.execute(
        "UPDATE system_jobs SET status=?, result_json=?, error_text=? WHERE id=?",
        (status, res_str, error, job_id)
    )
    await _commit_and_sync(db)

async def get_job(job_id: str) -> dict[str, Any] | None:
    db = await get_db()
    row = await (await db.execute("SELECT * FROM system_jobs WHERE id=?", (job_id,))).fetchone()
    if not row:
        return None
    res = dict(row)
    if res.get("result_json"):
        try:
            res["result"] = json.loads(res["result_json"])
        except ValueError:
            res["result"] = None
    else:
        res["result"] = None
    res["error"] = res.get("error_text")
    return res

async def cleanup_old_jobs(cutoff_seconds: int = 3600) -> None:
    db = await get_db()
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=cutoff_seconds)).isoformat()
    await db.execute("DELETE FROM system_jobs WHERE created_at < ?", (cutoff,))
    await _commit_and_sync(db)
"""

if "async def create_job" not in code:
    code += job_funcs

with open("src/legaltech/services/database.py", "w") as f:
    f.write(code)

print("done")
