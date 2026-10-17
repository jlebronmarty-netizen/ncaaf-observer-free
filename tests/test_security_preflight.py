from pathlib import Path
import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("security_preflight", ROOT / "scripts/security_preflight.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

class SecurityPreflight(unittest.TestCase):
    def setUp(self):
        self.template = json.loads((ROOT / "templates/manual-only.yml.disabled").read_text())

    def test_repository(self):
        self.assertEqual(guard.inspect(ROOT), [])

    def test_workflow_contract(self):
        self.assertEqual(guard.workflow_findings(self.template), [])

    def test_forbidden_triggers(self):
        for trigger in ["schedule", "push", "pull_request", "pull_request_target", "workflow_run"]:
            with self.subTest(trigger=trigger):
                data = copy.deepcopy(self.template)
                data["on"][trigger] = {}
                self.assertTrue(guard.workflow_findings(data))

    def test_privileges_runtime_timeout_and_expressions(self):
        mutations = [
            lambda d: d.update(permissions={"contents": "write"}),
            lambda d: d.update(env={"KEY": "${{ secrets." + "ANY }}"}),
            lambda d: d["jobs"]["preflight"].update({"runs-on": "self-hosted"}),
            lambda d: d["jobs"]["preflight"].update({"timeout-minutes": 999}),
            lambda d: d["jobs"]["preflight"].update({"timeout-minutes": True}),
            lambda d: d["jobs"]["preflight"].update(permissions={"actions": "write"}),
        ]
        for mutate in mutations:
            data = copy.deepcopy(self.template); mutate(data)
            self.assertTrue(guard.workflow_findings(data))

    def test_no_transfer_publication_or_extra_commands(self):
        for action in ["actions/upload-artifact@v4", "softprops/action-gh-release@v2", "actions/deploy-pages@v4"]:
            data = copy.deepcopy(self.template)
            data["jobs"]["preflight"]["steps"].append({"uses": action})
            self.assertTrue(guard.workflow_findings(data))
        for command in ["curl provider.invalid", "git push", "gh release create test", "Invoke-WebRequest provider.invalid"]:
            data = copy.deepcopy(self.template)
            data["jobs"]["preflight"]["steps"][1]["run"] = command
            self.assertTrue(guard.workflow_findings(data))

    def test_checkout_credentials_and_pin(self):
        for field, value in [("persist-credentials", True), ("fetch-depth", 0)]:
            data = copy.deepcopy(self.template)
            data["jobs"]["preflight"]["steps"][0]["with"][field] = value
            self.assertTrue(guard.workflow_findings(data))
        data = copy.deepcopy(self.template)
        data["jobs"]["preflight"]["steps"][0]["uses"] = "actions/checkout@main"
        self.assertTrue(guard.workflow_findings(data))

    def fixture(self, name, content):
        with tempfile.TemporaryDirectory(prefix="ncaaf-synthetic-security-") as directory:
            root = Path(directory)
            (root / "templates").mkdir()
            (root / "templates/manual-only.yml.disabled").write_text(json.dumps(self.template))
            target = root / name; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            return guard.inspect(root)

    def test_operational_file_rejection(self):
        for name in ["state/item.txt", "forecasts/sample.json", "data.SQLITE", ".env.local", "capture.jsonl", ".github/workflows/test.yml"]:
            with self.subTest(name=name): self.assertTrue(self.fixture(name, b"synthetic"))

    def test_disguised_archives_and_database(self):
        for payload in [b"PK" + bytes([3,4]), b"SQLite format 3" + bytes([0]), bytes([31,139])]:
            self.assertTrue(self.fixture("README.md", payload))

    def test_synthetic_credential_detection_and_redaction(self):
        for payload in [b"ghp_" + b"A" * 36, b"-----BEGIN " + b"PRIVATE KEY-----", b"api_key=" + b"A" * 32]:
            errors = self.fixture("README.md", payload)
            self.assertTrue(any("credential" in error for error in errors))
            self.assertNotIn(payload.decode(), " ".join(errors))

    def test_ignore_patterns(self):
        patterns = ["x.sqlite", "x.SQLITE", "x.sqlite3", "x.DB", "x.zip", "x.AESGCM", ".env.local", "nested/raw/file.txt", "nested/forecasts/item.json", "x.pem", "x.key", "x.jsonl", "x.parquet", "backups/test.txt"]
        result = subprocess.run(["git", "check-ignore", "--no-index", "--stdin", "-z"], cwd=ROOT, input=("\0".join(patterns)+"\0").encode(), capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(set(result.stdout.decode().strip("\0").split("\0")), set(patterns))

if __name__ == "__main__": unittest.main()
