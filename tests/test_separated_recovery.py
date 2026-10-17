"""Offline simulation of copying a synthetic backup to a separate directory.

This is NOT an off-host test and has no external provider/network access.
"""
import hashlib
import os
from contextlib import closing
import shutil
import sqlite3
import tempfile
import unittest
from unittest import mock
from pathlib import Path

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def restore_verified(remote_file, destination, expected_hash):
    if not remote_file.is_file():
        raise FileNotFoundError("synthetic remote object missing")
    if sha256(remote_file) != expected_hash:
        raise ValueError("synthetic remote object hash mismatch")
    # Validate a private same-volume staging copy before publishing any destination.
    # os.link is atomic no-clobber: a stale exists() result cannot permit overwrite.
    with tempfile.TemporaryDirectory(prefix=".restore-", dir=destination.parent) as temporary:
        staged = Path(temporary) / "verified.sqlite"
        shutil.copyfile(remote_file, staged)
        if sha256(staged) != expected_hash:
            raise ValueError("restored hash mismatch")
        with closing(sqlite3.connect(staged.as_uri() + "?mode=ro", uri=True)) as con:
            if con.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise ValueError("SQLite integrity failed")
            if con.execute("SELECT value FROM sample").fetchall() != [("synthetic",)]:
                raise ValueError("synthetic content mismatch")
        # No overwrite fallback on filesystems without hard-link support.
        os.link(staged, destination)

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
        self.assertFalse(base.exists(), "temporary fixture directory must be removed")


    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix="ncaaf-synthetic-regression-")
        self.base = Path(self.workspace.name)

    def tearDown(self):
        self.workspace.cleanup()
        self.assertFalse(self.base.exists(), "temporary regression directory leaked")

    def make_object(self, value="synthetic"):
        source = self.base / "object.bin"
        with closing(sqlite3.connect(source)) as con:
            con.execute("CREATE TABLE sample(value TEXT NOT NULL)")
            con.execute("INSERT INTO sample VALUES (?)", (value,))
            con.commit()
        return source

    def assert_no_output(self, destination):
        self.assertFalse(destination.exists(), "failed restore must not be published")
        self.assertEqual(list(self.base.glob(".restore-*")), [], "staging directory leaked")

    def test_overwrite_guard_does_not_trust_exists_check(self):
        source = self.make_object()
        destination = self.base / "existing.sqlite"
        destination.write_bytes(b"preserve-existing-synthetic-file")
        previous = destination.read_bytes()
        real_exists = Path.exists
        # Model a stale negative existence check before a conflicting publish.
        with mock.patch.object(Path, "exists", lambda path: False if path == destination else real_exists(path)):
            with self.assertRaises(FileExistsError):
                restore_verified(source, destination, sha256(source))
        self.assertEqual(destination.read_bytes(), previous)
        self.assertEqual(list(self.base.glob(".restore-*")), [])

    def test_hash_matching_non_sqlite_is_not_published(self):
        source = self.base / "object.bin"
        source.write_bytes(b"synthetic-not-a-database")
        destination = self.base / "rejected.sqlite"
        with self.assertRaises((sqlite3.DatabaseError, ValueError)):
            restore_verified(source, destination, sha256(source))
        self.assert_no_output(destination)

    def test_sqlite_content_failure_is_not_published(self):
        source = self.make_object("incorrect-synthetic-content")
        destination = self.base / "rejected.sqlite"
        with self.assertRaises(ValueError):
            restore_verified(source, destination, sha256(source))
        self.assert_no_output(destination)

    def test_copy_tampering_is_not_published(self):
        source = self.make_object()
        destination = self.base / "rejected.sqlite"
        copy = shutil.copyfile
        def corrupt_after_copy(src, dst):
            result = copy(src, dst)
            Path(dst).write_bytes(b"tampered-copy")
            return result
        with mock.patch.object(shutil, "copyfile", side_effect=corrupt_after_copy):
            with self.assertRaises(ValueError):
                restore_verified(source, destination, sha256(source))
        self.assert_no_output(destination)

    def test_interrupted_copy_removes_partial_output(self):
        source = self.make_object()
        destination = self.base / "rejected.sqlite"
        def fail_copy(src, dst):
            Path(dst).write_bytes(b"partial-synthetic-copy")
            raise OSError("injected synthetic copy failure")
        with mock.patch.object(shutil, "copyfile", side_effect=fail_copy):
            with self.assertRaises(OSError):
                restore_verified(source, destination, sha256(source))
        self.assert_no_output(destination)

    def test_unsupported_atomic_publish_fails_closed(self):
        source = self.make_object()
        destination = self.base / "rejected.sqlite"
        with mock.patch.object(os, "link", side_effect=OSError("synthetic unsupported filesystem")):
            with self.assertRaises(OSError):
                restore_verified(source, destination, sha256(source))
        self.assert_no_output(destination)

    def test_missing_and_tampered_objects_have_no_output(self):
        source = self.make_object()
        expected = sha256(source)
        destination = self.base / "rejected.sqlite"
        source.write_bytes(b"tampered-source")
        with self.assertRaises(ValueError):
            restore_verified(source, destination, expected)
        self.assert_no_output(destination)
        source.unlink()
        with self.assertRaises(FileNotFoundError):
            restore_verified(source, destination, expected)
        self.assert_no_output(destination)

if __name__ == "__main__":
    unittest.main()
