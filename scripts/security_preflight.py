"""Offline repository guard. No HTTP, credentials, execution, archive or publication APIs.
The disabled workflow intentionally uses JSON, a strict YAML subset, to fail closed
without a third-party parser or YAML implicit-key coercion.
"""
from pathlib import Path
import json
import re
import sys

ALLOWED = {
    ".gitignore", "README.md", "SECURITY_REVIEW.md",
    "templates/manual-only.yml.disabled", "tests/test_bootstrap.py",
    "tests/test_security_preflight.py", "tests/test_synthetic_recovery.py", "tests/test_separated_recovery.py", "tests/synthetic_crypto_check.mjs", "scripts/security_preflight.py",
    "audit/github-observations.json", "audit/BASE_INVENTORY.json",
    "audit/FILE_INVENTORY.json", "audit/OFFLINE_TEST_RESULTS.txt",
    "audit/CHECKPOINT.json", "WORKFLOW_REVIEW.md", "RESTART.md", "PHASE7_SECURITY_PLAN.md", "PHASE7_SEPARATED_RECOVERY.md", "PHASE7_OFFHOST_SYNTHETIC_DESIGN.md",
    ".github/workflows/manual-synthetic.yml",
}
CHECKOUT = "actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10"
FORBIDDEN_PARTS = {"state", "backups", "raw", "forecasts", "datasets", "node_modules"}
FORBIDDEN_SUFFIXES = {".sqlite", ".sqlite3", ".db", ".zip", ".aesgcm", ".pem", ".key", ".csv", ".jsonl", ".parquet", ".gz", ".7z", ".tar", ".p12", ".pfx"}
SECRET_PATTERNS = [
    re.compile(rb"gh[pousr]_" + rb"[A-Za-z0-9]{30,}"),
    re.compile(rb"github_pat_" + rb"[A-Za-z0-9_]{40,}"),
    re.compile(rb"AKIA" + rb"[A-Z0-9]{16}"),
    re.compile(rb"-----BEGIN " + rb"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"(?i)(?:password|api_key|access_token|client_secret)\s*[:=]\s*[\"\']?" + rb"[A-Za-z0-9_/+.-]{16,}"),
]

def workflow_findings(data):
    errors = []
    if not isinstance(data, dict): return ["workflow must be an object"]
    if set(data) != {"name", "on", "permissions", "jobs"}: errors.append("unexpected workflow fields")
    if data.get("on") != {"workflow_dispatch": {}}: errors.append("manual-only trigger required")
    if data.get("permissions") != {"contents": "read"}: errors.append("read-only permission required")
    jobs = data.get("jobs", {})
    if not isinstance(jobs, dict) or set(jobs) != {"preflight"}: return errors + ["one synthetic job required"]
    job = jobs["preflight"]
    if not isinstance(job, dict): return errors + ["job must be object"]
    if set(job) != {"runs-on", "timeout-minutes", "permissions", "steps"}: errors.append("unexpected job fields")
    if job.get("runs-on") != "windows-2022": errors.append("standard Windows runner required")
    timeout = job.get("timeout-minutes")
    if type(timeout) is not int or not 1 <= timeout <= 10: errors.append("bounded timeout required")
    if job.get("permissions") != {"contents": "read"}: errors.append("job read-only permission required")
    steps = job.get("steps")
    expected = [
        {"name": "Read source only", "uses": CHECKOUT, "with": {"persist-credentials": False, "fetch-depth": 1}},
        {"name": "Offline synthetic security tests", "shell": "pwsh", "run": "python -I -m unittest discover -s tests -v"},
    ]
    if steps != expected: errors.append("only pinned checkout and offline tests allowed")
    if "${{" in json.dumps(data): errors.append("expressions and secret references forbidden")
    return errors

def inspect(root):
    root = Path(root)
    errors = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if ".git" in rel.parts or "__pycache__" in rel.parts: continue
        name = rel.as_posix()
        if path.is_symlink(): errors.append(name + ": symlink forbidden"); continue
        if any(part.lower() in FORBIDDEN_PARTS for part in rel.parts): errors.append(name + ": operational directory forbidden")
        if not path.is_file(): continue
        if name not in ALLOWED: errors.append(name + ": unreviewed file")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES or path.name.lower().startswith(".env"): errors.append(name + ": forbidden operational type")
        if path.stat().st_size > 1024 * 1024: errors.append(name + ": oversized preparation file"); continue
        payload = path.read_bytes()
        if payload.startswith((b"PK\x03\x04", b"SQLite format 3\x00", b"\x1f\x8b")): errors.append(name + ": archive/database signature")
        if any(pattern.search(payload) for pattern in SECRET_PATTERNS): errors.append(name + ": possible credential (value redacted)")
    template = root / "templates/manual-only.yml.disabled"
    try: errors.extend(workflow_findings(json.loads(template.read_text(encoding="utf-8"))))
    except (ValueError, OSError): errors.append("disabled workflow missing or not strict JSON/YAML subset")
    # Only the exact reviewed workflow is permitted, byte-equivalent to the disabled template.
    active_dir = root / ".github/workflows"
    approved = active_dir / "manual-synthetic.yml"
    if active_dir.exists():
        if not approved.is_file(): errors.append("reviewed manual-only workflow missing")
        else:
            try:
                enabled_data = json.loads(approved.read_text(encoding="utf-8"))
                template_data = json.loads(template.read_text(encoding="utf-8"))
                if enabled_data != template_data: errors.append("installed workflow differs from reviewed template")
                errors.extend(workflow_findings(enabled_data))
            except (ValueError, OSError): errors.append("installed workflow not strict reviewed JSON")
        if sorted(p.name for p in active_dir.iterdir()) != ["manual-synthetic.yml"]:
            errors.append("additional active workflow forbidden")
    return errors

if __name__ == "__main__":
    findings = inspect(Path(__file__).resolve().parents[1])
    for finding in findings: print(finding)
    print("OFFLINE_SECURITY_" + ("FAIL" if findings else "PASS"))
    sys.exit(bool(findings))
