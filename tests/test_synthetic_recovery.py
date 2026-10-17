"""Synthetic-only backup/recovery demonstration. No NCAAF state, external I/O or encryption keys."""
import hashlib
import io
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

class SyntheticRecovery(unittest.TestCase):
    def test_tamper_detection_and_cold_sqlite_restore(self):
        with tempfile.TemporaryDirectory(prefix="ncaaf-synthetic-") as directory:
            root = Path(directory)
            src = root / "synthetic.db"
            db = sqlite3.connect(src)
            db.execute("CREATE TABLE examples (id INTEGER PRIMARY KEY, label TEXT NOT NULL)")
            db.execute("INSERT INTO examples VALUES (1, 'synthetic-only')")
            db.commit()
            db.close()
            payload = src.read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
                z.writestr("synthetic.db", payload)
            archive = buf.getvalue()
            with zipfile.ZipFile(io.BytesIO(archive)) as z:
                self.assertEqual(z.namelist(), ["synthetic.db"])
                restored = z.read("synthetic.db")
            self.assertEqual(hashlib.sha256(restored).hexdigest(), digest)
            self.assertNotEqual(hashlib.sha256(restored + b"x").hexdigest(), digest)
            dest = root / "restored.db"
            dest.write_bytes(restored)
            cold = sqlite3.connect(f"file:{dest.as_posix()}?mode=ro", uri=True)
            self.assertEqual(cold.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(cold.execute("SELECT label FROM examples").fetchone()[0], "synthetic-only")
            cold.close()

if __name__ == "__main__":
    unittest.main()
