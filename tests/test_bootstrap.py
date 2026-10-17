from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]

class SafeBootstrap(unittest.TestCase):
    def test_no_live_workflows(self):
        self.assertFalse((ROOT / ".github" / "workflows").exists())

    def test_templates_disabled(self):
        self.assertTrue((ROOT / "templates" / "manual-only.yml.disabled").is_file())
        self.assertEqual(list(ROOT.glob("**/*.yml")), [])
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
