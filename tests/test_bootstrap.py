from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]

class SafeBootstrap(unittest.TestCase):
    def test_exactly_one_reviewed_manual_workflow(self):
        import json
        approved = ROOT / ".github" / "workflows" / "manual-synthetic.yml"
        template = ROOT / "templates" / "manual-only.yml.disabled"
        self.assertTrue(approved.is_file())
        self.assertEqual(json.loads(approved.read_text()), json.loads(template.read_text()))
        self.assertEqual([p.name for p in approved.parent.iterdir()], ["manual-synthetic.yml"])

    def test_templates_disabled(self):
        self.assertTrue((ROOT / "templates" / "manual-only.yml.disabled").is_file())
        self.assertEqual([p.as_posix().removeprefix(ROOT.as_posix()+"/") for p in ROOT.glob("**/*.yml")], [".github/workflows/manual-synthetic.yml"])
        self.assertEqual(list(ROOT.glob("**/*.yaml")), [])

    def test_no_state_or_secrets(self):
        forbidden = {".zip", ".aesgcm", ".db", ".sqlite", ".sqlite3", ".pem", ".key"}
        self.assertFalse([p for p in ROOT.rglob("*") if p.is_file() and p.suffix in forbidden])

    def test_review_gates(self):
        doc = (ROOT / "SECURITY_REVIEW.md").read_text()
        self.assertIn("NOT APPROVED", doc)
        self.assertIn("NOT CONFIGURED", doc)

if __name__ == "__main__":
    unittest.main()
