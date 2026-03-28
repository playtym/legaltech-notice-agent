import re

with open("src/legaltech/app.py", "r") as f:
    code = f.read()

# Replace _jobs dict definition
code = re.sub(r'# ── Async job store.*?def _cleanup_old_jobs\(\).*?\n(?:\s+.*?\n)*\s+.*?\n\n', '', code, flags=re.DOTALL)
# For the pattern specifically there:
code = re.sub(r'_jobs: dict\[str, dict\] = \{\}.*?_JOB_TTL = 3600.*?\n\ndef _cleanup_old_jobs\(\):\n(?:    .*?\n)*\n', '', code, flags=re.DOTALL)

# In create_notice_typed and voice, replace _jobs initialization and cleanup
code = code.replace('_cleanup_old_jobs()', 'await db.cleanup_old_jobs()')
code = re.sub(r'_jobs\[job_id\]\s*=\s*\{"status":\s*"processing"[^\}]*\}', 'await db.create_job(job_id)', code)

# Replace pipeline fail blocks
code = re.sub(r'\s*_jobs\[job_id\]\["status"\] = "failed"\n\s*_jobs\[job_id\]\["error"\] = (.*?)\n',
              r'\n        await db.update_job_status(job_id, "failed", error=\1)\n', code)

# Replace pipeline success blocks
code = re.sub(r'\s*_jobs\[job_id\]\["status"\] = "completed"\n\s*_jobs\[job_id\]\["result"\] = result\n',
              r'\n        await db.update_job_status(job_id, "completed", result=result)\n', code)

# Replace polling endpoint
new_poll = """@app.get("/job/{job_id}/status")
async def get_job_status(job_id: str):
    \"\"\"Poll for async job completion.\"\"\"
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")
    return {"status": job["status"], "result": job.get("result"), "error": job.get("error")}
"""
code = re.sub(r'@app\.get\("/job/\{job_id\}/status"\)\nasync def get_job_status.*?return \{"status".*?\n', new_poll, code, flags=re.DOTALL)

# Remove any empty cleanup job calls if there are left over syntax issues
code = re.sub(r'_jobs\[job_id\].*?\n', '', code)  # Any other direct assignments to _jobs

with open("src/legaltech/app.py", "w") as f:
    f.write(code)

print("done")
