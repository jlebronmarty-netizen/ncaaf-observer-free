"""Offline simulation of copying a synthetic backup to a separate directory.

This is NOT an off-host test and has no external provider/network access.
"""
import hashlib
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def restore_verified(remote_file, destination, expected_hash):
    if not remote_file.is_file():
        raise FileNotFoundError("synthetic remote object missing")
    if sha256(remote_file) != expected_hash:
        raise ValueError("synthetic remote object hash mismatch")
    if destination.exists():
        raise FileExistsError("refuse overwrite")
    shutil.copyfile(remote_file, destination)
    if sha256(destination) != expected_hash:
        destination.unlink()
        raise ValueError("restored hash mismatch")
    con = sqlite3.connect(f"file:{destination.as_posix()}?mode=ro", uri=True)
    try:
        if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity failed")
        if con.execute("SELECT value FROM sample").fetchone()[0] != "synthetic":
            raise ValueError("synthetic content mismatch")
    finally:
        con.close()

class SeparatedRecovery(unittest.TestCase):
    def test_recovery_and_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="ncaaf-offline-copy-") as tmp:
            base = Path(tmp)
            source = base / "source"
            remote = base / "simulated_remote_not_external"
            restore = base / "restored"
            for directory in (source,remote,restore):
                directory.mkdir()
            original = source / "fixture.sqlite"
            db = sqlite3.connect(original)
            db.execute("CREATE TABLE sample(value TEXT NOT NULL)")
            db.execute("INSERT INTO sample VALUES ('synthetic')")
            db.commit()
            db.close()
            expected = sha256(original)
            remote_object = remote / "object.bin"
            shutil.copyfile(original, remote_object)
            restored = restore / "fixture.sqlite"
            restore_verified(remote_object, restored, expected)
            self.assertEqual(sha256(restored), expected)
            with self.assertRaises(FileExistsError):
                restore_verified(remote_object, restored, expected)
            remote_object.write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                restore_verified(remote_object, restore / "tampered.sqlite", expected)
            remote_object.unlink()
            with self.assertRaises(FileNotFoundError):
                restore_verified(remote_object, restore / "missing.sqlite", expected)
            self.assertEqual(sha256(restored), expected)

if __name__ == "__main__":
    unittest.main()
