"""Synthetic-only security/regression checks, no real data or network fixtures."""
from pathlib import Path
import copy
import ast
import errno
import importlib.util
import json
import sqlite3
import unittest
from contextlib import closing
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('phase8b_synthetic', ROOT / 'scripts/synthetic_state_v1.py')
s = importlib.util.module_from_spec(spec); spec.loader.exec_module(s)


class SyntheticState(unittest.TestCase):
    def setUp(self):
        self.workspace = s.workspace(); self.root = self.workspace.__enter__()
        self.host = s.HostedSimulator(self.root)
        self.epoch = self.host.claim('W', 0, ttl=10000)
        self.client = s.PullClient(self.root, keep=2)
        self.transport = s.ReadOnlyTransport(self.host)

    def tearDown(self):
        self.workspace.__exit__(None, None, None)
        self.assertFalse(self.root.exists())

    def commit(self, event, finals=False):
        generation = self.transport.head()['generation']
        now = event * 100 + (60 if finals else 20)
        return self.host.commit('W', self.epoch, generation, now, s.synthetic_batch(event, finals))

    def seed(self):
        self.commit(1); self.client.pull(self.transport)
        return self.client.pointer.read_bytes()

    def clean(self, pointer):
        self.assertEqual(self.client.pointer.read_bytes(), pointer)
        self.assertFalse((self.client.root / '.pull.lock').exists())
        self.assertEqual(list(self.client.root.glob('.pull-*')), [])
        self.assertEqual(list(self.client.root.glob('.restore-*')), [])

    def test_windows_offline_execution_and_multiple_session_catchup(self):
        self.seed(); old = self.client.pointer.read_bytes()
        for event in range(2, 7):
            self.commit(event); self.commit(event, True)
        self.assertEqual(self.client.pointer.read_bytes(), old)
        self.assertEqual(self.host.website_view()['forecasts'], 12)
        self.assertEqual(self.host.website_view()['settlements'], 10)
        before = self.transport.bytes_read; self.client.pull(self.transport)
        transferred = self.transport.bytes_read - before
        self.assertGreater(transferred, 0)
        self.assertEqual(self.client.current(), self.transport.head())
        before = self.transport.bytes_read; self.client.pull(self.transport)
        self.assertEqual(before, self.transport.bytes_read)

    def test_restart_reattaches_only_owned_synthetic_persistence(self):
        self.seed()
        for event in (2, 3): self.commit(event)
        restarted_host = s.HostedSimulator(self.root)
        restarted_client = s.PullClient(self.root, keep=2)
        restarted_transport = s.ReadOnlyTransport(restarted_host)
        self.assertEqual(restarted_client.current()['generation'], 1)
        self.assertEqual(restarted_transport.head()['generation'], 3)
        restarted_client.pull(restarted_transport)
        restarted_client.restore(self.root / 'restart.synthetic.sqlite')
        self.assertEqual(restarted_client.current(), restarted_transport.head())

    def test_restored_rows_and_cold_integrity_match_host(self):
        self.commit(1); self.commit(1, True); self.client.pull(self.transport)
        target = self.root / 'cold.synthetic.sqlite'; self.client.restore(target)
        with closing(sqlite3.connect(target)) as a, closing(sqlite3.connect(self.host.path)) as b:
            self.assertEqual(a.execute('PRAGMA integrity_check').fetchall(), [('ok',)])
            self.assertEqual(a.execute('SELECT * FROM facts ORDER BY seq').fetchall(), b.execute('SELECT * FROM facts ORDER BY seq').fetchall())
            self.assertEqual(a.execute('SELECT * FROM checkpoints ORDER BY generation').fetchall(), b.execute('SELECT * FROM checkpoints ORDER BY generation').fetchall())
            self.assertEqual(a.execute('SELECT generation,watermark,digest FROM control').fetchone(), b.execute('SELECT generation,watermark,digest FROM control').fetchone())
            self.assertEqual(a.execute('SELECT owner,expires FROM control').fetchone(), (None, 0))

    def test_duplicate_events_and_settlement_idempotency(self):
        self.commit(1); self.commit(1, True)
        head = self.transport.head()
        self.host.commit('W', self.epoch, head['generation'], 170, s.synthetic_batch(1))
        self.host.commit('W', self.epoch, head['generation'], 170, s.synthetic_batch(1, True))
        self.assertEqual(self.transport.head(), head)
        self.assertEqual(self.host.website_view()['settlements'], 2)

    def test_independent_models_and_immutable_versions(self):
        self.commit(1)
        changed = copy.deepcopy(s.synthetic_batch(1))
        changed[-1]['body']['home_score'] = 99
        changed[-1]['sha256'] = s.sha(s.encode(changed[-1]['body']))
        with self.assertRaises(ValueError):
            self.host.commit('W', self.epoch, 1, 120, changed)
        self.assertEqual(self.host.website_view()['forecasts'], 2)

    def test_stale_writer_expired_lease_and_reviewed_takeover(self):
        with self.assertRaises(ValueError): self.host.claim('other', 1)
        with self.assertRaises(ValueError): self.host.claim('other', 10001)
        epoch = self.host.claim('other', 10001, reviewed_takeover=True)
        with self.assertRaises(ValueError): self.host.commit('W', self.epoch, 0, 120, s.synthetic_batch(1))
        self.assertGreater(epoch, self.epoch)

    def test_stale_generation_rejected(self):
        self.commit(1)
        with self.assertRaises(ValueError): self.host.commit('W', self.epoch, 0, 220, s.synthetic_batch(2))

    def test_failure_before_remote_commit_does_not_publish_or_create_facts(self):
        with self.assertRaises(OSError): self.host.commit('W', self.epoch, 0, 120, s.synthetic_batch(1), fail_after_object=True)
        self.assertEqual(self.transport.head(), {'generation': 0, 'digest': None})
        self.assertEqual(self.host.website_view()['forecasts'], 0)
        orphan = next(self.host.objects.iterdir()).stem
        with self.assertRaises(ValueError): list(self.transport.stream(orphan))
        self.commit(1); self.client.pull(self.transport)

    def test_hash_tampering_does_not_advance(self):
        pointer = self.seed(); self.commit(2)
        object_path = self.host.objects / (self.transport.head()['digest'] + '.json')
        object_path.write_bytes(object_path.read_bytes() + b'x')
        with self.assertRaises(ValueError): self.client.pull(self.transport)
        self.clean(pointer)

    def test_interrupted_transfer_and_retry(self):
        pointer = self.seed(); self.commit(2)
        original = self.transport.stream
        def interrupted(digest):
            yield next(iter(original(digest)))
            raise OSError('synthetic interrupted transfer')
        with mock.patch.object(self.transport, 'stream', side_effect=interrupted):
            with self.assertRaises(OSError): self.client.pull(self.transport)
        self.clean(pointer)
        self.client.pull(self.transport); self.assertEqual(self.client.current(), self.transport.head())

    def test_missing_checkpoint_and_object(self):
        pointer = self.seed(); self.commit(2)
        with mock.patch.object(self.transport, 'checkpoint', side_effect=FileNotFoundError('synthetic gap')):
            with self.assertRaises(FileNotFoundError): self.client.pull(self.transport)
        self.clean(pointer)
        path = self.host.objects / (self.transport.head()['digest'] + '.json'); data = path.read_bytes(); path.unlink()
        with self.assertRaises(FileNotFoundError): self.client.pull(self.transport)
        self.clean(pointer); path.write_bytes(data); self.client.pull(self.transport)

    def test_stale_rollback_and_equivocation(self):
        self.seed(); old = self.transport.head(); self.commit(2); self.client.pull(self.transport)
        pointer = self.client.pointer.read_bytes()
        for bad in [old, {'generation': 2, 'digest': '0' * 64}]:
            with mock.patch.object(self.transport, 'head', return_value=bad):
                with self.assertRaises(ValueError): self.client.pull(self.transport)
            self.clean(pointer)

    def test_disk_full_retains_old_checkpoint_then_recovers(self):
        pointer = self.seed(); self.commit(2)
        def disk(stage):
            if stage == 'write': raise OSError(errno.ENOSPC, 'synthetic disk full')
        with self.assertRaises(OSError): self.client.pull(self.transport, fault=disk)
        self.clean(pointer); self.client.pull(self.transport)

    def test_restore_and_checkpoint_failure_recover_without_repeat_download(self):
        pointer = self.seed(); self.commit(2)
        for stage in ['restore', 'checkpoint']:
            def failure(current):
                if current == stage: raise OSError('synthetic ' + stage)
            with self.assertRaises(OSError): self.client.pull(self.transport, fault=failure)
            self.clean(pointer)
        before = self.transport.bytes_read; self.client.pull(self.transport)
        self.assertEqual(before, self.transport.bytes_read)

    def test_atomic_no_overwrite_restore_and_object_publication(self):
        self.seed(); target = self.root / 'sentinel'; target.write_bytes(b'SYNTHETIC KEEP')
        with self.assertRaises(FileExistsError): self.client.restore(target)
        self.assertEqual(target.read_bytes(), b'SYNTHETIC KEEP')
        with self.assertRaises(FileExistsError): s.no_clobber(target, b'REPLACE')
        self.assertEqual(target.read_bytes(), b'SYNTHETIC KEEP')

    def test_retention_preserves_full_parent_chain(self):
        for event in range(1, 8): self.commit(event)
        self.client.pull(self.transport)
        self.assertEqual(len(list(self.client.versions.iterdir())), 3)  # baseline + latest2
        self.assertEqual(len(list(self.client.objects.iterdir())), 7)
        self.client.restore(self.root / 'retained.synthetic.sqlite')

    def test_corrupt_local_checkpoint_or_cache_is_not_silently_reset(self):
        self.seed(); pointer = self.client.pointer.read_bytes()
        self.client.pointer.write_bytes(b'broken')
        with self.assertRaises(ValueError): self.client.pull(self.transport)
        self.assertEqual(self.client.pointer.read_bytes(), b'broken')
        self.client.pointer.write_bytes(pointer)
        cached = next(self.client.objects.iterdir()); cached.write_bytes(b'bad')
        with self.assertRaises(ValueError): self.client.pull(self.transport)
        self.clean(pointer)

    def test_no_backdating_future_inputs_or_foreign_events(self):
        with self.assertRaises(ValueError): self.host.commit('W', self.epoch, 0, 121, s.synthetic_batch(1))
        with self.assertRaises(ValueError): self.host.commit('W', self.epoch, 0, 1, s.synthetic_batch(1))
        item = s.fact('event', event_id='REAL-FORBIDDEN', home='SYNTHETIC-A', away='SYNTHETIC-B', kickoff=200)
        with self.assertRaises(ValueError): self.host.commit('W', self.epoch, 0, 120, [item])
        self.assertEqual(self.host.website_view()['forecasts'], 0)

    def test_cancelled_or_unverified_final_cannot_settle(self):
        self.commit(1)
        bad = s.synthetic_batch(1, True)
        for item in bad:
            if item['kind'] == 'observation':
                item['body']['verified'] = False
                item['id'] = s.identity(item['kind'], item['body']); item['sha256'] = s.sha(s.encode(item['body']))
        with self.assertRaises(ValueError): self.host.commit('W', self.epoch, 1, 160, bad)
        self.assertEqual(self.host.website_view()['settlements'], 0)

    def test_read_only_client_leaves_host_bytes_unchanged(self):
        self.commit(1); before = s.sha(self.host.path.read_bytes())
        objects = {p.name: s.sha(p.read_bytes()) for p in self.host.objects.iterdir()}
        self.client.pull(self.transport); self.client.restore(self.root / 'read-only.synthetic.sqlite')
        self.assertEqual(s.sha(self.host.path.read_bytes()), before)
        self.assertEqual({p.name: s.sha(p.read_bytes()) for p in self.host.objects.iterdir()}, objects)
        self.assertFalse(any(hasattr(self.transport, name) for name in ['put', 'delete', 'commit', 'upload']))

    def test_duplicate_client_lock_and_cleanup(self):
        self.commit(1); lock = self.client.root / '.pull.lock'; lock.write_bytes(b'other-synthetic-client')
        with self.assertRaises(FileExistsError): self.client.pull(self.transport)
        self.assertEqual(lock.read_bytes(), b'other-synthetic-client'); lock.unlink()
        self.client.pull(self.transport)

    def test_invalid_restoration_with_matching_transport_hash_keeps_checkpoint(self):
        pointer = self.seed(); self.commit(2)
        original_head = self.transport.head()
        payload = (self.host.objects / (original_head['digest'] + '.json')).read_bytes()
        bad = s.decode(payload)
        row = next(row for row in bad['changes'] if row['kind'] == 'forecast')
        row['body']['home_probability'] = 2
        row['sha256'] = s.sha(s.encode(row['body']))
        forged_payload = s.encode(bad); forged_digest = s.sha(forged_payload)
        checkpoint = self.transport.checkpoint; stream = self.transport.stream
        with mock.patch.object(self.transport, 'head', return_value={'generation': 2, 'digest': forged_digest}), mock.patch.object(self.transport, 'checkpoint', side_effect=lambda generation: forged_digest if generation == 2 else checkpoint(generation)), mock.patch.object(self.transport, 'stream', side_effect=lambda digest: iter([forged_payload]) if digest == forged_digest else stream(digest)):
            with self.assertRaises(ValueError): self.client.pull(self.transport)
        self.clean(pointer)
        self.client.restore(self.root / 'old-good.sqlite')
        self.client.pull(self.transport)

    def test_feature_cutoff_and_model_identity_are_enforced(self):
        items = s.synthetic_batch(1)
        features = next(item for item in items if item['kind'] == 'features')
        forecast = next(item for item in items if item['kind'] == 'forecast')
        features['body']['available_at'] = 130
        features['id'] = s.identity('features', features['body'])
        features['sha256'] = s.sha(s.encode(features['body']))
        forecast['body']['feature_id'] = features['id']
        forecast['sha256'] = s.sha(s.encode(forecast['body']))
        with self.assertRaises(ValueError): self.host.commit('W', self.epoch, 0, 120, items)
        self.assertEqual(self.host.website_view()['forecasts'], 0)

    def test_clock_rollback_and_database_mutation_are_rejected(self):
        self.commit(1); self.commit(2)
        with self.assertRaises(ValueError): self.host.commit('W', self.epoch, 2, 120, s.synthetic_batch(1))
        with closing(sqlite3.connect(self.host.path)) as db:
            with self.assertRaises(sqlite3.IntegrityError): db.execute("UPDATE facts SET body='changed'")
            with self.assertRaises(sqlite3.IntegrityError): db.execute('DELETE FROM checkpoints')

    def test_generation_and_transfer_budgets_fail_closed(self):
        pointer = self.seed(); self.commit(2)
        with mock.patch.object(self.transport, 'head', return_value={'generation': s.MAX_GENERATIONS + 1, 'digest': '0' * 64}):
            with self.assertRaises(ValueError): self.client.pull(self.transport)
        self.clean(pointer)
        with mock.patch.object(self.transport, 'stream', return_value=iter([b'x' * s.MAX_BYTES, b'x'])):
            with self.assertRaises(ValueError): self.client.pull(self.transport)
        self.clean(pointer)

    def test_event_identity_conflict_is_atomic(self):
        self.commit(1); before = self.transport.head()
        items = s.synthetic_batch(1); items[0]['body']['home'] = 'SYNTHETIC-CHANGED'
        items[0]['sha256'] = s.sha(s.encode(items[0]['body']))
        with self.assertRaises(ValueError): self.host.commit('W', self.epoch, 1, 120, items)
        self.assertEqual(before, self.transport.head())

    def test_corrected_final_requires_append_only_review(self):
        self.commit(1); self.commit(1, True)
        final = s.fact('observation', event_id='SYNTHETIC-EVENT-1', source='SYNTHETIC_FREE_SOURCE', received_at=170, state='FINAL', home_score=20, away_score=24, verified=True)
        forecast = next(item for item in s.synthetic_batch(1) if item['kind'] == 'forecast')
        corrected = s.fact('settlement', forecast_id=forecast['id'], observation_id=final['id'], policy='SIMULATED_FINAL_V1')
        with self.assertRaises(ValueError): self.host.commit('W', self.epoch, 2, 170, [final, corrected])
        review = s.fact('review', forecast_id=forecast['id'], observation_id=final['id'], reason='CORRECTED_FINAL_REQUIRES_REVIEW')
        self.host.commit('W', self.epoch, 2, 170, [final, review])
        self.assertEqual(self.host.website_view()['settlements'], 2)

    def test_simulator_has_no_network_or_process_imports(self):
        tree = ast.parse((ROOT / 'scripts/synthetic_state_v1.py').read_text())
        imports = {node.module.split('.')[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imports |= {name.name.split('.')[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for name in node.names}
        self.assertEqual(imports, {'contextlib', 'pathlib', 'hashlib', 'json', 'os', 'sqlite3', 'stat', 'tempfile', 'time'})
        calls = {ast.unparse(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)}
        self.assertFalse(calls & {'os.system', 'os.popen', 'eval', 'exec', '__import__'})

    def test_restore_rejects_unsafe_identity_or_external_destination(self):
        self.seed()
        with self.assertRaises(ValueError): self.client.restore(self.root.parent / 'forbidden-not-created.sqlite')
        with self.assertRaises(ValueError): self.client.restore(self.root / 'unsafe.sqlite', {'generation': 1, 'digest': '../forbidden'})
        self.assertFalse((self.root / 'unsafe.sqlite').exists())

    def test_reject_non_disposable_roots(self):
        with self.assertRaises((ValueError, FileNotFoundError)): s.HostedSimulator(ROOT)


if __name__ == '__main__': unittest.main()
