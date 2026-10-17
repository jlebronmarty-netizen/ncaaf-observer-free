import unittest
import sys
from pathlib import Path
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import hashlib
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import synthetic_state_v1 as s
import readonly_projection_v1 as a


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = s.workspace(); self.root = self.temp.__enter__(); self.addCleanup(self.temp.__exit__, None, None, None)
        self.host = s.HostedSimulator(self.root); self.epoch = self.host.claim('W', 0, ttl=10000)
        self.host.commit('W', self.epoch, 0, 120, s.synthetic_batch(1))
        self.transport = s.ReadOnlyTransport(self.host); self.floor = self.transport.head(); self.reader = a.Reader(self.root)
        self.request = {'version': a.VERSION, 'offset': 0, 'limit': 50, 'max_age': 1000}

    def read(self, reader=None, **kw):
        return (reader or self.reader).project(self.request, floor=kw.get('floor', self.floor), now=kw.get('now', 120))

    def test_deterministic_projection_immutable_ids(self):
        raw = self.read(); data = s.decode(raw)
        self.assertEqual(raw, self.read()); self.assertEqual(data['generation'], 1)
        self.assertTrue(data['synthetic']); self.assertEqual(len(data['forecasts']), 2)
        self.assertEqual(data['forecasts'][0]['id'], next(x['id'] for x in s.synthetic_batch(1) if x['kind'] == 'forecast'))
        self.assertLessEqual(len(raw), a.MAX_OUTPUT)

    def test_concurrent_reads_restart_and_no_host_writes(self):
        def hashes(): return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.host.root.rglob('*') if p.is_file()}
        before = hashes()
        with ThreadPoolExecutor(max_workers=4) as pool: results = list(pool.map(lambda _: self.read(a.Reader(self.root)), range(8)))
        self.assertTrue(all(x == results[0] for x in results)); self.assertEqual(before, hashes())
        self.assertFalse(hasattr(self.reader, 'host')); self.assertFalse(hasattr(self.reader, 'commit'))
        with closing(s.connect(self.reader._path, readonly=True)) as db:
            with self.assertRaises(sqlite3.OperationalError): db.execute('DELETE FROM control')

    def test_malformed_request_bounds(self):
        for value in [None, {}, {**self.request, 'write': True}, {**self.request, 'version': 'NBA'}, {**self.request, 'limit': True}, {**self.request, 'limit': 51}, {**self.request, 'offset': -1}, {**self.request, 'max_age': 86401}]:
            with self.subTest(value=value), self.assertRaises(ValueError): self.reader.project(value, floor=self.floor, now=120)
        with self.assertRaises(ValueError): self.read(now=True)

    def test_stale_clock_and_floor(self):
        for now in [119, 1121]:
            with self.assertRaises(ValueError): self.read(now=now)
        for floor in [{'generation': 2, 'digest': 'a'*64}, {'generation': 1, 'digest': 'a'*64}, {}]:
            with self.assertRaises(ValueError): self.read(floor=floor)

    def test_corrupt_missing_partial_objects(self):
        path = self.host.objects / (self.floor['digest'] + '.json'); original = path.read_bytes()
        for data in [original[:20], b'corrupt']:
            path.write_bytes(data)
            with self.assertRaises(ValueError): self.read()
        path.unlink()
        with self.assertRaises(FileNotFoundError): self.read()

    def test_orphan_and_partial_publication_invisible(self):
        before = self.read()
        with self.assertRaises(OSError): self.host.commit('W', self.epoch, 1, 220, s.synthetic_batch(2), fail_after_object=True)
        self.assertEqual(self.read(), before)
        self.assertEqual(len(list(self.host.objects.iterdir())), 2)

    def test_uncommitted_head_and_corrupt_facts_rejected(self):
        with closing(s.connect(self.host.path)) as db:
            db.execute('UPDATE control SET generation=2'); db.commit()
        with self.assertRaises(ValueError): self.read()

    def test_authority_body_corruption_rejected(self):
        with closing(s.connect(self.host.path)) as db:
            db.execute('DROP TRIGGER facts_no_UPDATE'); db.execute("UPDATE facts SET body_sha='bad'"); db.commit()
        with self.assertRaises(ValueError): self.read()

    def test_settlement_and_restart_floor_rollback(self):
        self.host.commit('W', self.epoch, 1, 160, s.synthetic_batch(1, True)); latest = self.transport.head()
        result = s.decode(self.read(now=160)); self.assertEqual(result['forecasts'][0]['final'], {'home_score':24,'away_score':20})
        with closing(s.connect(self.host.path)) as db:
            db.execute('UPDATE control SET generation=1,watermark=(SELECT watermark FROM checkpoints WHERE generation=1),digest=?', (self.floor['digest'],)); db.commit()
        with self.assertRaises(ValueError): self.read(a.Reader(self.root), floor=latest, now=160)

    def test_incompatible_namespace_and_resource_budgets(self):
        with mock.patch.object(a, 'MAX_FACTS', 1):
            with self.assertRaises(ValueError): self.read()
        with mock.patch.object(s, 'MAX_SESSION_BYTES', 1):
            with self.assertRaises(ValueError): self.read()
        with mock.patch.object(a, 'MAX_OUTPUT', 1):
            with self.assertRaises(ValueError): self.read()
        with closing(s.connect(self.host.path)) as db: db.execute('PRAGMA application_id=1')
        with self.assertRaises(ValueError): self.read()

    def test_read_during_commit_sees_only_committed_state(self):
        old = self.read(); original = s.no_clobber; observed = []
        def intercepted(path, data):
            original(path, data)
            observed.append(self.read())
        with mock.patch.object(s, 'no_clobber', side_effect=intercepted): self.host.commit('W', self.epoch, 1, 220, s.synthetic_batch(2))
        self.assertEqual(observed, [old]); self.assertEqual(s.decode(self.read(now=220))['generation'], 2)


if __name__ == '__main__': unittest.main()
