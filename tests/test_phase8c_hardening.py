"""Phase8C adversarial tests. Every canary/database is disposable and synthetic."""
from pathlib import Path
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
import copy
import errno
import importlib.util
import json
import os
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('phase8c_sim', ROOT / 'scripts/synthetic_state_v1.py')
s = importlib.util.module_from_spec(spec); spec.loader.exec_module(s)


class Hardening(unittest.TestCase):
    def setUp(self):
        self.context = s.workspace(); self.root = self.context.__enter__()
        self.host = s.HostedSimulator(self.root); self.epoch = self.host.claim('W', 0, ttl=2000000)
        self.client = s.PullClient(self.root); self.transport = s.ReadOnlyTransport(self.host)

    def tearDown(self):
        self.context.__exit__(None, None, None)
        self.assertFalse(self.root.exists())

    def commit(self, event, finals=False):
        return self.host.commit('W', self.epoch, self.transport.head()['generation'], event * 100 + (60 if finals else 20), s.synthetic_batch(event, finals))

    def seed(self):
        self.commit(1); self.client.pull(self.transport)
        return self.client.pointer.read_bytes()

    def test_no_arbitrary_writes_outside_synthetic_workspace(self):
        with tempfile.TemporaryDirectory(prefix='phase8c-canary-') as name:
            destination = Path(name) / 'forbidden.synthetic'
            with self.assertRaises(ValueError): s.no_clobber(destination, b'SYNTHETIC ONLY')
            self.assertFalse(destination.exists())

    def test_hardlinked_workspace_marker_rejected(self):
        marker = self.root / '.synthetic-only'; data = marker.read_bytes()
        with tempfile.TemporaryDirectory(prefix='phase8c-canary-') as name:
            canary = Path(name) / 'marker'; canary.write_bytes(data)
            marker.unlink(); os.link(canary, marker)
            with self.assertRaises(ValueError): s.HostedSimulator(self.root)
            self.assertEqual(canary.read_bytes(), data)

    def test_malicious_watermark_does_not_allocate_unbounded_range(self):
        payload = s.encode({'format': s.FORMAT, 'synthetic': True, 'generation': 1, 'parent': None, 'from_seq': 0, 'watermark': 10**30, 'fence': 1, 'committed_at': 1, 'changes': [{'seq': 1}]})
        with self.assertRaises(ValueError): s.snapshot(payload, s.sha(payload), 1, None, 0)

    def test_deep_or_compressed_input_rejected_as_bounded_json(self):
        for payload in [b'[' * 2000 + b'0' + b']' * 2000, b'PK\x03\x04synthetic', b'\x1f\x8bsynthetic']:
            with self.subTest(prefix=payload[:4]):
                with self.assertRaises(ValueError): s.decode(payload)

    def test_reopened_database_requires_synthetic_identity_before_write(self):
        # A fake unrelated database, not an authentic ledger or record.
        self.host.path.unlink()
        with closing(sqlite3.connect(self.host.path)) as db:
            db.execute('CREATE TABLE unrelated_canary(value TEXT)'); db.commit()
        before = self.host.path.read_bytes()
        with self.assertRaises(ValueError): s.HostedSimulator(self.root)
        self.assertEqual(self.host.path.read_bytes(), before)

    def test_junction_cache_directory_rejected_without_external_write(self):
        with tempfile.TemporaryDirectory(prefix='phase8c-canary-') as name:
            outside = Path(name)
            self.client.objects.rmdir()
            if os.name == 'nt':
                result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(self.client.objects), str(outside)], capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
            else: self.client.objects.symlink_to(outside, target_is_directory=True)
            self.commit(1)
            with self.assertRaises(ValueError): self.client.pull(self.transport)
            self.assertEqual(list(outside.iterdir()), [])

    def test_hardlinked_cache_file_rejected_without_reading_canary(self):
        self.seed(); cached = next(self.client.objects.iterdir()); data = cached.read_bytes()
        with tempfile.TemporaryDirectory(prefix='phase8c-canary-') as name:
            canary = Path(name) / 'payload'; canary.write_bytes(data)
            cached.unlink(); os.link(canary, cached)
            with self.assertRaises(ValueError): self.client.pull(self.transport)
            self.assertEqual(canary.read_bytes(), data)

    def test_malicious_head_rejected_before_pointer_publication(self):
        old = self.seed(); self.commit(2)
        bad = {**self.transport.head(), 'unexpected': 'SYNTHETIC'}
        with mock.patch.object(self.transport, 'head', return_value=bad):
            with self.assertRaises(ValueError): self.client.pull(self.transport)
        self.assertEqual(self.client.pointer.read_bytes(), old)

    def test_parent_hash_and_out_of_order_generation_rejected(self):
        old = self.seed(); self.commit(2)
        path = self.host.objects / (self.transport.head()['digest'] + '.json')
        original = path.read_bytes()
        for key, value in [('parent', '../outside'), ('generation', 1), ('from_seq', -1), ('fence', False)]:
            with self.subTest(key=key):
                data = s.decode(original); data[key] = value; payload = s.encode(data); digest = s.sha(payload)
                checkpoint = self.transport.checkpoint; stream = self.transport.stream
                with mock.patch.object(self.transport, 'head', return_value={'generation': 2, 'digest': digest}), mock.patch.object(self.transport, 'checkpoint', side_effect=lambda generation: digest if generation == 2 else checkpoint(generation)), mock.patch.object(self.transport, 'stream', side_effect=lambda identity: iter([payload]) if identity == digest else stream(identity)):
                    with self.assertRaises(ValueError): self.client.pull(self.transport)
                self.assertEqual(self.client.pointer.read_bytes(), old)

    def test_corrupt_committed_parent_blocks_writer(self):
        self.seed(); head = self.transport.head()
        path = self.host.objects / (head['digest'] + '.json')
        data = s.decode(path.read_bytes()); data['committed_at'] = 0; path.write_bytes(s.encode(data))
        with self.assertRaises(ValueError): self.host.commit('W', self.epoch, 1, 220, s.synthetic_batch(2))
        self.assertEqual(self.transport.head(), head)

    def test_unexpected_version_file_never_deleted_or_published(self):
        old = self.seed(); canary = self.client.versions / 'UNREVIEWED.txt'; canary.write_bytes(b'SYNTHETIC KEEP')
        self.commit(2)
        with self.assertRaises(ValueError): self.client.pull(self.transport)
        self.assertEqual(canary.read_bytes(), b'SYNTHETIC KEEP')
        self.assertEqual(self.client.pointer.read_bytes(), old)

    def test_permission_denial_and_partial_write_keep_previous_backup(self):
        old = self.seed(); self.commit(2)
        with mock.patch.object(os, 'link', side_effect=PermissionError('synthetic denied')):
            with self.assertRaises(PermissionError): self.client.pull(self.transport)
        self.assertEqual(self.client.pointer.read_bytes(), old)
        original_open = Path.open
        class PartialWriter:
            def __init__(self, file): self.file = file
            def __enter__(self): return self
            def __exit__(self, *args): return self.file.__exit__(*args)
            def write(self, data):
                self.file.write(data[:5]); self.file.flush()
                raise OSError(errno.ENOSPC, 'injected partial write')
        def opener(path, *args, **kwargs):
            file = original_open(path, *args, **kwargs)
            return PartialWriter(file) if path.name == 'partial' else file
        with mock.patch.object(Path, 'open', opener):
            with self.assertRaises(OSError): self.client.pull(self.transport)
        self.assertEqual(self.client.pointer.read_bytes(), old)
        self.assertEqual(list(self.client.root.glob('.pull-*')), [])
        self.assertFalse((self.client.root / '.pull.lock').exists())
        self.client.pull(self.transport)

    def test_unexpected_restart_and_reviewed_stale_lock_recovery(self):
        old = self.seed(); self.commit(2)
        def fail(stage):
            if stage == 'checkpoint': raise OSError('simulated restart boundary')
        with self.assertRaises(OSError): self.client.pull(self.transport, fault=fail)
        lock = self.client.root / '.pull.lock'; lock.write_bytes(b'SYNTHETIC DEAD OWNER')
        restarted = s.PullClient(self.root)
        with self.assertRaises(FileExistsError): restarted.pull(self.transport)
        self.assertEqual(restarted.pointer.read_bytes(), old)
        self.assertEqual(lock.read_bytes(), b'SYNTHETIC DEAD OWNER')
        lock.unlink()  # explicit reviewed synthetic cleanup, not automatic takeover
        before = self.transport.bytes_read; restarted.pull(self.transport)
        self.assertEqual(self.transport.bytes_read, before)
        restarted.restore(self.root / 'restarted-cold.sqlite')

    def test_retained_version_cold_restore_and_synthetic_database_separation(self):
        self.seed(); old = self.client.current(); self.commit(2); self.client.pull(self.transport)
        restored = self.root / 'retained-cold.sqlite'; self.client.restore(restored, old)
        with closing(sqlite3.connect(restored)) as db:
            names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertIn('synthetic_identity', names)
            self.assertNotIn('forecasts', names); self.assertNotIn('metadata', names)
            self.assertEqual(db.execute('PRAGMA application_id').fetchone(), (s.APPLICATION_ID,))
            self.assertEqual(db.execute('SELECT format FROM synthetic_identity').fetchall(), [(s.FORMAT,)])
        bad = s.synthetic_batch(3); bad[0]['body']['synthetic'] = False
        bad[0]['sha256'] = s.sha(s.encode(bad[0]['body']))
        with self.assertRaises(ValueError): self.host.commit('W', self.epoch, 2, 320, bad)

    def test_unsafe_windows_paths_and_bounded_file_reads(self):
        for name in ['NUL', 'CON.txt', 'payload:stream', 'trailing.', '../phase8c-escape']:
            with self.subTest(name=name):
                with self.assertRaises(ValueError): s.no_clobber(self.root / name, b'SYNTHETIC')
        path = self.root / 'oversized'; path.write_bytes(b'x' * (s.MAX_BYTES + 1))
        calls = []; original = os.open
        def opened(name, *args, **kwargs):
            calls.append(str(name)); return original(name, *args, **kwargs)
        with mock.patch.object(os, 'open', side_effect=opened):
            with self.assertRaises(ValueError): s.read(path)
        self.assertNotIn(str(path), calls)

    def test_aggregate_session_and_fact_budgets_preserve_authority(self):
        with mock.patch.object(s, 'MAX_CHANGES', 1):
            with self.assertRaises(ValueError): self.commit(1)
        self.assertEqual(self.host.website_view()['forecasts'], 0)
        old = self.seed()
        with mock.patch.object(s, 'MAX_SESSION_BYTES', 1):
            with self.assertRaises(ValueError): self.client.pull(self.transport)
            with self.assertRaises(ValueError): self.client.restore(self.root / 'too-large.sqlite')
        self.assertEqual(self.client.pointer.read_bytes(), old)
        self.assertFalse((self.root / 'too-large.sqlite').exists())

    def test_frozen_phase8b_model_forecast_contracts_unchanged(self):
        self.assertEqual(s.sha(s.encode(s.synthetic_batch(1))), '89569e7295490faf48207be46afffb1f7e60072aa0e053fa8680fa7cd23fe0bb')
        self.assertEqual(s.sha(s.encode(s.synthetic_batch(1, True))), 'b210a85b87b4293d3fbb63a5c8f5798a0cfcf4c0ab4063df959d5b4496c93078')

    def test_host_can_advance_during_frozen_client_snapshot(self):
        self.seed(); self.commit(2); head = self.transport.head(); original = self.transport.stream
        advanced = []
        def advancing(digest):
            if not advanced:
                self.commit(3); advanced.append(True)
            yield from original(digest)
        with mock.patch.object(self.transport, 'stream', side_effect=advancing):
            self.client.pull(self.transport)
        self.assertEqual(self.client.current(), head)
        self.assertEqual(self.transport.head()['generation'], 3)
        self.client.pull(self.transport)
        self.assertEqual(self.client.current(), self.transport.head())

    def test_corrupt_sqlite_fails_without_rewriting_it(self):
        self.seed(); self.host.path.write_bytes(b'SYNTHETIC CORRUPT SQLITE')
        before = self.host.path.read_bytes()
        with self.assertRaises((ValueError, sqlite3.DatabaseError)):
            self.host.website_view()
        self.assertEqual(self.host.path.read_bytes(), before)

    def test_valid_sqlite_but_corrupt_fact_body_hash_blocks_settlement(self):
        self.seed(); head = self.transport.head()
        with closing(sqlite3.connect(self.host.path)) as db:
            row = db.execute("SELECT seq,body FROM facts WHERE kind='forecast' ORDER BY seq LIMIT 1").fetchone()
            body = s.decode(row[1]); body['home_score'] = 99
            db.execute('DROP TRIGGER facts_no_UPDATE')  # controlled disk-corruption surrogate
            db.execute('UPDATE facts SET body=? WHERE seq=?', (s.encode(body), row[0])); db.commit()
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchall(), [('ok',)])
        with self.assertRaises(ValueError): self.host.commit('W', self.epoch, 1, 160, s.synthetic_batch(1, True))
        self.assertEqual(self.transport.head(), head)

    def test_two_writers_same_expected_generation_one_wins(self):
        self.commit(1); barrier = threading.Barrier(2)
        def run():
            barrier.wait()
            try: return self.host.commit('W', self.epoch, 1, 220, s.synthetic_batch(2))
            except ValueError: return 'CONFLICT'
        with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(lambda _: run(), range(2)))
        self.assertEqual(sorted(map(str, results)), ['2', 'CONFLICT'])
        self.assertEqual(self.host.website_view()['forecasts'], 4)

    def test_two_simultaneous_lease_claims_one_owner(self):
        # Fresh owned synthetic host; reset fixture only through fresh workspace.
        with s.workspace() as root:
            host = s.HostedSimulator(root); barrier = threading.Barrier(2)
            def run(owner):
                barrier.wait()
                try: return host.claim(owner, 0)
                except ValueError: return 'CONFLICT'
            with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(run, ['one', 'two']))
            self.assertEqual(sorted(map(str, results)), ['1', 'CONFLICT'])

    def test_concurrent_settlement_retry_is_idempotent(self):
        self.commit(1); barrier = threading.Barrier(2)
        def run():
            barrier.wait()
            try: return self.host.commit('W', self.epoch, 1, 160, s.synthetic_batch(1, True))
            except ValueError: return 'CONFLICT'
        with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(lambda _: run(), range(2)))
        self.assertEqual(sorted(map(str, results)), ['2', 'CONFLICT'])
        self.host.commit('W', self.epoch, 2, 170, s.synthetic_batch(1, True))
        self.assertEqual(self.host.website_view()['settlements'], 2)

    def test_two_simultaneous_backup_clients_one_lock_owner(self):
        self.commit(1); entered = threading.Event(); release = threading.Event()
        def pause(stage):
            if stage == 'write': entered.set(); self.assertTrue(release.wait(10))
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(self.client.pull, self.transport, pause)
            self.assertTrue(entered.wait(10))
            other = s.PullClient(self.root)
            try:
                with self.assertRaises(FileExistsError): other.pull(s.ReadOnlyTransport(self.host))
            finally: release.set()
            self.assertEqual(first.result()['generation'], 1)
        self.assertFalse((self.client.root / '.pull.lock').exists())

    def test_offline_1_3_7_14_days_incremental_immutable_backup(self):
        for days in (1, 3, 7, 14):
            with self.subTest(days=days), s.workspace() as root:
                host = s.HostedSimulator(root); epoch = host.claim('W', 0, ttl=2000000)
                client = s.PullClient(root); transport = s.ReadOnlyTransport(host)
                host.commit('W', epoch, 0, 120, s.synthetic_batch(1)); client.pull(transport)
                validated = {p.name: p.read_bytes() for p in client.objects.iterdir()}
                pointer = client.pointer.read_bytes()
                # A controlled 86400-second gap per day, not a real wait or real game.
                for day in range(1, days + 1):
                    event = day * 864
                    host.commit('W', epoch, transport.head()['generation'], day * 86400 + 20, s.synthetic_batch(event))
                    host.commit('W', epoch, transport.head()['generation'], day * 86400 + 60, s.synthetic_batch(event, True))
                self.assertEqual(client.pointer.read_bytes(), pointer)
                self.assertEqual(host.website_view()['forecasts'], 2 * (days + 1))
                expected = sum((host.objects / (transport.checkpoint(g) + '.json')).stat().st_size for g in range(2, 2 * days + 2))
                before = transport.bytes_read; client.pull(transport)
                self.assertEqual(transport.bytes_read - before, expected)
                for name, payload in validated.items(): self.assertEqual((client.objects / name).read_bytes(), payload)
                self.assertEqual(client.current(), transport.head())
                client.restore(root / 'offline-cold.sqlite')


if __name__ == '__main__': unittest.main()
