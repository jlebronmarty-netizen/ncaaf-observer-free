"""Offline-only Phase8B simulator. No network, credential, real-data or cloud adapters.
Only fresh disposable roots created by workspace() are accepted. Not a production service.
"""
from contextlib import contextmanager, closing
from pathlib import Path
import hashlib
import json
import os
import sqlite3
import tempfile
import time

FORMAT = 'NCAAF_PHASE8B_SYNTHETIC_V1'
MAX_BYTES = 1024 * 1024
MAX_GENERATIONS = 10000
KINDS = {'model', 'event', 'observation', 'forecast', 'settlement', 'review', 'features'}
FIELDS = {
    'model': {'synthetic', 'model', 'version', 'artifact_sha256', 'frozen_at'},
    'event': {'synthetic', 'event_id', 'home', 'away', 'kickoff'},
    'observation': {'synthetic', 'event_id', 'source', 'received_at', 'state'},
    'features': {'synthetic', 'event_id', 'model_id', 'available_at', 'input_observation_ids', 'values'},
    'forecast': {'synthetic', 'event_id', 'model_id', 'observation_id', 'feature_id', 'as_of', 'created_at', 'home_score', 'away_score', 'home_probability'},
    'settlement': {'synthetic', 'forecast_id', 'observation_id', 'policy'},
    'review': {'synthetic', 'forecast_id', 'observation_id', 'reason'},
}
MODELS = ('NCAAF_PPG_V1', 'NCAAF_RIDGE_FEATURES_V1')


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def decode(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    value = json.loads(data, object_pairs_hook=unique)
    if encode(value) != data:
        raise ValueError('Noncanonical snapshot')
    return value


@contextmanager
def workspace():
    with tempfile.TemporaryDirectory(prefix='ncaaf-phase8b-synthetic-') as name:
        root = Path(name).resolve()
        (root / '.synthetic-only').write_bytes(encode({'format': FORMAT}))
        yield root


def guard(root):
    root = Path(root)
    if root.is_symlink() or root.resolve().parent != Path(tempfile.gettempdir()).resolve():
        raise ValueError('Disposable synthetic workspace required')
    if not root.name.startswith('ncaaf-phase8b-synthetic-') or (root / '.synthetic-only').read_bytes() != encode({'format': FORMAT}):
        raise ValueError('Synthetic marker required')
    return root.resolve()


def connect(path):
    db = sqlite3.connect(path)
    db.execute('PRAGMA synchronous=FULL')
    return db


def schema(db):
    db.executescript('''
    CREATE TABLE facts(seq INTEGER PRIMARY KEY,kind TEXT NOT NULL,id TEXT NOT NULL,
        body BLOB NOT NULL,body_sha TEXT NOT NULL,UNIQUE(kind,id));
    CREATE TABLE checkpoints(generation INTEGER PRIMARY KEY,digest TEXT UNIQUE NOT NULL,
        parent TEXT,watermark INTEGER NOT NULL);
    CREATE TABLE control(id INTEGER PRIMARY KEY CHECK(id=1),epoch INTEGER NOT NULL,
        owner TEXT,expires INTEGER NOT NULL,generation INTEGER NOT NULL,watermark INTEGER NOT NULL,digest TEXT);
    INSERT INTO control VALUES(1,0,NULL,0,0,0,NULL);
    ''')
    for table in ('facts', 'checkpoints'):
        for action in ('UPDATE', 'DELETE'):
            db.execute(f"CREATE TRIGGER {table}_no_{action} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'Immutable synthetic evidence'); END")
    db.commit()


def identity(kind, body):
    if kind == 'model': return body['model'] + '@' + body['version']
    if kind == 'event': return body['event_id']
    if kind == 'forecast': return sha((body['model_id'] + '\0' + body['event_id']).encode())
    if kind == 'settlement': return body['forecast_id']
    return sha(encode(body))


def fact(kind, **fields):
    body = {'synthetic': True, **fields}
    return {'kind': kind, 'id': identity(kind, body), 'body': body, 'sha256': sha(encode(body))}


def lookup(db, kind, key):
    row = db.execute('SELECT body FROM facts WHERE kind=? AND id=?', (kind, key)).fetchone()
    if row is None: raise ValueError('Missing dependency')
    return decode(row[0])


def validate(db, item):
    if set(item) != {'kind', 'id', 'body', 'sha256'} or item['kind'] not in KINDS:
        raise ValueError('Unknown fact contract')
    kind, body = item['kind'], item['body']
    fields = FIELDS[kind]
    if kind == 'observation' and body.get('state') == 'FINAL': fields = fields | {'home_score', 'away_score', 'verified'}
    if set(body) != fields: raise ValueError('Unexpected fact fields')
    if body.get('synthetic') is not True or item['id'] != identity(kind, body) or item['sha256'] != sha(encode(body)):
        raise ValueError('Identity/hash/synthetic mismatch')
    if 'event_id' in body and not body['event_id'].startswith('SYNTHETIC-'):
        raise ValueError('Synthetic events only')
    if kind == 'model':
        if body['model'] not in MODELS or body['version'] != 'SIMULATED_RULES_V1' or body['artifact_sha256'] != sha(body['model'].encode()) or body['frozen_at'] != 0:
            raise ValueError('Frozen synthetic model mismatch')
    elif kind == 'event':
        if type(body['kickoff']) is not int or body['kickoff'] <= 0 or body['home'] == body['away'] or not all(body[s].startswith('SYNTHETIC-') for s in ('home', 'away')):
            raise ValueError('Invalid synthetic teams')
    elif kind == 'observation':
        lookup(db, 'event', body['event_id'])
        if body['source'] != 'SYNTHETIC_FREE_SOURCE' or type(body['received_at']) is not int:
            raise ValueError('Invalid source evidence')
        if body['state'] not in ('SCHEDULED', 'FINAL', 'CANCELLED', 'POSTPONED'):
            raise ValueError('Invalid lifecycle')
        if body['state'] == 'FINAL' and (not all(type(body[s]) is int and body[s] >= 0 for s in ('home_score', 'away_score')) or body['home_score'] == body['away_score'] or body.get('verified') is not True):
            raise ValueError('Unverified final')
    elif kind == 'features':
        lookup(db, 'model', body['model_id']); lookup(db, 'event', body['event_id'])
        if type(body['available_at']) is not int or not body['input_observation_ids'] or body['values'] != {'fixture_home_mean': 21, 'fixture_away_mean': 17}:
            raise ValueError('Synthetic feature contract')
        for key in body['input_observation_ids']:
            if lookup(db, 'observation', key)['received_at'] > body['available_at']: raise ValueError('Feature future input')
    elif kind == 'forecast':
        model = lookup(db, 'model', body['model_id'])
        if type(body['created_at']) is not int or model['frozen_at'] > body['created_at']: raise ValueError('Model freeze/as-of')
        features = lookup(db, 'features', body['feature_id'])
        if features['event_id'] != body['event_id'] or features['model_id'] != body['model_id'] or features['available_at'] > body['as_of']: raise ValueError('Feature identity/as-of')
        event = lookup(db, 'event', body['event_id'])
        obs = lookup(db, 'observation', body['observation_id'])
        if obs['event_id'] != body['event_id'] or obs['state'] != 'SCHEDULED' or not obs['received_at'] <= body['as_of'] == body['created_at'] < event['kickoff']:
            raise ValueError('Not pregame/as-of')
        if not all(type(body[k]) in (int, float) and body[k] >= 0 for k in ('home_score', 'away_score')) or type(body['home_probability']) not in (int, float) or not 0 <= body['home_probability'] <= 1:
            raise ValueError('Invalid synthetic projection')
    elif kind == 'settlement':
        forecast = lookup(db, 'forecast', body['forecast_id'])
        event = lookup(db, 'event', forecast['event_id'])
        obs = lookup(db, 'observation', body['observation_id'])
        if obs['event_id'] != forecast['event_id'] or obs['state'] != 'FINAL' or obs['received_at'] < event['kickoff'] or body['policy'] != 'SIMULATED_FINAL_V1':
            raise ValueError('Verified matching final required')
    elif kind == 'review':
        forecast = lookup(db, 'forecast', body['forecast_id'])
        observation = lookup(db, 'observation', body['observation_id'])
        if observation['state'] != 'FINAL' or observation['event_id'] != forecast['event_id']: raise ValueError('Correction identity mismatch')
        if body['reason'] != 'CORRECTED_FINAL_REQUIRES_REVIEW': raise ValueError('Invalid review')


def insert(db, item):
    validate(db, item)
    old = db.execute('SELECT body FROM facts WHERE kind=? AND id=?', (item['kind'], item['id'])).fetchone()
    if old:
        if old[0] != encode(item['body']): raise ValueError('Immutable identity conflict; review required')
        return False
    db.execute('INSERT INTO facts(kind,id,body,body_sha) VALUES(?,?,?,?)', (item['kind'], item['id'], encode(item['body']), item['sha256']))
    return True


def no_clobber(path, data):
    """Same-volume authenticated bytes already validated by caller. No overwrite fallback."""
    with tempfile.TemporaryDirectory(prefix='.stage-', dir=path.parent) as tmp:
        staged = Path(tmp) / 'payload'
        with staged.open('xb') as file:
            file.write(data); file.flush(); os.fsync(file.fileno())
        os.link(staged, path)


class HostedSimulator:
    def __init__(self, root):
        self.root = guard(root) / 'simulated-host'
        marker = self.root / '.host-format'
        fresh = not self.root.exists()
        if fresh:
            self.root.mkdir(); marker.write_bytes(encode({'format': FORMAT}))
        elif self.root.is_symlink() or marker.read_bytes() != encode({'format': FORMAT}):
            raise ValueError('Unrecognized synthetic host')
        self.objects = self.root / 'objects'
        self.path = self.root / 'synthetic.sqlite'
        if fresh:
            self.objects.mkdir()
            with closing(connect(self.path)) as db: schema(db)
        elif self.objects.is_symlink() or not self.objects.is_dir() or self.path.is_symlink() or not self.path.is_file():
            raise ValueError('Invalid synthetic persistence')

    def claim(self, owner, now, ttl=100, reviewed_takeover=False):
        with closing(connect(self.path)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            epoch, previous, expires = db.execute('SELECT epoch,owner,expires FROM control').fetchone()
            if previous is not None and (now < expires or not reviewed_takeover):
                raise ValueError('Lease active or explicit takeover review missing')
            db.execute('UPDATE control SET epoch=?,owner=?,expires=?', (epoch + 1, owner, now + ttl))
            return epoch + 1

    def commit(self, owner, epoch, expected_generation, now, items, fail_after_object=False):
        with closing(connect(self.path)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            e, o, expires, generation, watermark, parent = db.execute('SELECT epoch,owner,expires,generation,watermark,digest FROM control').fetchone()
            if (epoch, owner, expected_generation) != (e, o, generation) or now >= expires:
                raise ValueError('Stale writer/expired lease/checkpoint')
            if generation and now < decode((self.objects / (parent + '.json')).read_bytes())['committed_at']:
                raise ValueError('Writer clock rollback')
            changed = 0
            for item in items:
                if item['kind'] == 'forecast' and not db.execute("SELECT 1 FROM facts WHERE kind='forecast' AND id=?", (item['id'],)).fetchone() and item['body']['created_at'] != now:
                    raise ValueError('New forecasts cannot be backdated')
                if item['kind'] == 'features' and item['body']['available_at'] > now: raise ValueError('Future feature bundle')
                if item['kind'] == 'observation' and item['body']['received_at'] > now:
                    raise ValueError('Future observation')
                changed += insert(db, item)
            if not changed: return generation
            rows = [{'seq': seq, **fact(kind, **{k: v for k, v in decode(body).items() if k != 'synthetic'})} for seq, kind, body in db.execute('SELECT seq,kind,body FROM facts WHERE seq>? ORDER BY seq', (watermark,))]
            payload = encode({'format': FORMAT, 'synthetic': True, 'generation': generation + 1, 'parent': parent, 'from_seq': watermark, 'watermark': rows[-1]['seq'], 'fence': epoch, 'committed_at': now, 'changes': rows})
            if len(payload) > MAX_BYTES: raise ValueError('Snapshot budget exceeded')
            digest = sha(payload); path = self.objects / (digest + '.json')
            if path.exists():
                if path.read_bytes() != payload: raise ValueError('Corrupt existing object')
            else: no_clobber(path, payload)
            if fail_after_object: raise OSError('Injected failure before committed pointer')
            db.execute('INSERT INTO checkpoints VALUES(?,?,?,?)', (generation + 1, digest, parent, rows[-1]['seq']))
            db.execute('UPDATE control SET generation=?,watermark=?,digest=?', (generation + 1, rows[-1]['seq'], digest))
            return generation + 1

    def website_view(self):
        """Read-only synthetic website projection: no Windows/client dependency."""
        with closing(sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)) as db:
            generation = db.execute('SELECT generation FROM control').fetchone()[0]
            return {'synthetic': True, 'generation': generation, 'forecasts': db.execute("SELECT count(*) FROM facts WHERE kind='forecast'").fetchone()[0], 'settlements': db.execute("SELECT count(*) FROM facts WHERE kind='settlement'").fetchone()[0]}


class ReadOnlyTransport:
    """In-process authenticated-identity substitute, NOT a network/auth implementation."""
    def __init__(self, host):
        self.host = host
        self.bytes_read = 0

    def head(self):
        with closing(sqlite3.connect(self.host.path.as_uri() + '?mode=ro', uri=True)) as db:
            generation, digest = db.execute('SELECT generation,digest FROM control').fetchone()
            return {'generation': generation, 'digest': digest}

    def checkpoint(self, generation):
        with closing(sqlite3.connect(self.host.path.as_uri() + '?mode=ro', uri=True)) as db:
            row = db.execute('SELECT digest FROM checkpoints WHERE generation=?', (generation,)).fetchone()
            if row is None: raise FileNotFoundError('Missing committed checkpoint')
            return row[0]

    def stream(self, digest):
        # Require a committed identity: orphaned uploads are never downloadable.
        with closing(sqlite3.connect(self.host.path.as_uri() + '?mode=ro', uri=True)) as db:
            if not db.execute('SELECT 1 FROM checkpoints WHERE digest=?', (digest,)).fetchone():
                raise ValueError('Object is not committed')
        payload = (self.host.objects / (digest + '.json')).read_bytes()
        self.bytes_read += len(payload)
        for offset in range(0, len(payload), 1024): yield payload[offset:offset + 1024]


def valid_digest(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def snapshot(payload, digest, generation, parent, watermark, previous_clock=-1, previous_fence=0):
    if len(payload) > MAX_BYTES or sha(payload) != digest: raise ValueError('Snapshot checksum/size')
    data = decode(payload)
    if set(data) != {'format', 'synthetic', 'generation', 'parent', 'from_seq', 'watermark', 'fence', 'committed_at', 'changes'} or data['format'] != FORMAT or data['synthetic'] is not True:
        raise ValueError('Snapshot contract')
    if not all(type(data[key]) is int for key in ('generation', 'from_seq', 'watermark', 'fence', 'committed_at')) or data['fence'] < 1 or data['committed_at'] < 0:
        raise ValueError('Invalid checkpoint clocks/fence')
    if data['committed_at'] < previous_clock or data['fence'] < previous_fence: raise ValueError('Clock/fence rollback')
    if data['generation'] != generation or data['parent'] != parent or data['from_seq'] != watermark:
        raise ValueError('Broken chain/sequence')
    seqs = [row['seq'] for row in data['changes']]
    if not seqs or not all(type(seq) is int for seq in seqs) or seqs != list(range(watermark + 1, data['watermark'] + 1)):
        raise ValueError('Noncontiguous facts')
    return data


class PullClient:
    def __init__(self, root, keep=3):
        if type(keep) is not int or keep < 1: raise ValueError('Positive retention required')
        self.root = guard(root) / 'synthetic-windows-client'
        marker = self.root / '.client-format'
        fresh = not self.root.exists()
        if fresh:
            self.root.mkdir(); marker.write_bytes(encode({'format': FORMAT}))
        elif self.root.is_symlink() or marker.read_bytes() != encode({'format': FORMAT}):
            raise ValueError('Unrecognized synthetic client')
        self.objects = self.root / 'objects'
        self.versions = self.root / 'versions'
        if fresh:
            self.objects.mkdir(); self.versions.mkdir()
        elif any(path.is_symlink() or not path.is_dir() for path in (self.objects, self.versions)):
            raise ValueError('Invalid synthetic cache')
        self.keep = keep
        self.pointer = self.root / 'last_verified.json'

    def current(self):
        if not self.pointer.exists(): return {'generation': 0, 'digest': None}
        data = decode(self.pointer.read_bytes())
        if set(data) != {'generation', 'digest'} or type(data['generation']) is not int or not 1 <= data['generation'] <= MAX_GENERATIONS or not valid_digest(data['digest']):
            raise ValueError('Corrupt local checkpoint')
        return data

    def pull(self, transport, fault=lambda stage: None):
        lock = self.root / '.pull.lock'
        with lock.open('xb'): pass
        try:
            old = self.current(); head = transport.head()
            if type(head['generation']) is not int or not 1 <= head['generation'] <= MAX_GENERATIONS: raise ValueError('No committed generation')
            if head['generation'] < old['generation'] or (head['generation'] == old['generation'] and head['digest'] != old['digest']):
                raise ValueError('Rollback/equivocation')
            # Revalidate cached lineage on every session, not just newly fetched objects.
            parent, watermark = None, 0
            clock, fence = -1, 0
            with tempfile.TemporaryDirectory(prefix='.pull-', dir=self.root) as temporary:
                for generation in range(1, head['generation'] + 1):
                    digest = transport.checkpoint(generation)
                    if not valid_digest(digest):
                        raise ValueError('Invalid object identifier')
                    cached = self.objects / (digest + '.json')
                    if cached.exists(): payload = cached.read_bytes()
                    else:
                        partial = Path(temporary) / 'partial'
                        with partial.open('xb') as target:
                            size = 0
                            for chunk in transport.stream(digest):
                                fault('write'); size += len(chunk)
                                if size > MAX_BYTES: raise ValueError('Transfer size exceeded')
                                target.write(chunk)
                        payload = partial.read_bytes(); partial.unlink()
                    data = snapshot(payload, digest, generation, parent, watermark, clock, fence)
                    if generation == old['generation'] and digest != old['digest']:
                        raise ValueError('Historical checkpoint equivocation')
                    if not cached.exists(): no_clobber(cached, payload)
                    version = self.versions / f'{generation:012d}-{digest}.json'
                    if version.exists():
                        if version.read_bytes() != payload: raise ValueError('Existing backup corrupt')
                    else: no_clobber(version, payload)
                    parent, watermark = digest, data['watermark']
                    clock, fence = data['committed_at'], data['fence']
                if parent != head['digest']: raise ValueError('Head not bound to chain')
                fault('restore')
                self.restore(Path(temporary) / 'cold.sqlite', head)
                fault('checkpoint')
                staged_pointer = Path(temporary) / 'checkpoint'
                with staged_pointer.open('xb') as target:
                    target.write(encode(head)); target.flush(); os.fsync(target.fileno())
                os.replace(staged_pointer, self.pointer)  # sole mutable LOCAL pointer
            # Retain baseline + newest K recovery-point files. CAS parents never pruned.
            versions = sorted(self.versions.glob('*.json'))
            for path in versions[1:-self.keep]: path.unlink()
            return self.current()
        finally:
            lock.unlink()

    def restore(self, destination, checkpoint=None):
        checkpoint = checkpoint or self.current()
        destination = Path(destination)
        if not destination.resolve().is_relative_to(self.root.parent): raise ValueError('Synthetic restore outside workspace')
        if destination.exists(): raise FileExistsError('Restore refuses existing output')
        parent, watermark, generation = None, 0, checkpoint['generation']
        if type(generation) is not int or not 1 <= generation <= MAX_GENERATIONS: raise ValueError('Restore generation budget')
        chain = []
        clock, fence = -1, 0
        digest = checkpoint['digest']
        for expected in range(generation, 0, -1):
            if not valid_digest(digest): raise ValueError('Unsafe restore object identity')
            payload = (self.objects / (digest + '.json')).read_bytes(); data = decode(payload)
            if sha(payload) != digest or data['generation'] != expected: raise ValueError('Restore chain corrupt')
            chain.append((payload, digest)); digest = data['parent']
        with tempfile.TemporaryDirectory(prefix='.restore-', dir=destination.parent) as tmp:
            staged = Path(tmp) / 'state.sqlite'
            with closing(connect(staged)) as db:
                schema(db)
                for expected, (payload, digest) in enumerate(reversed(chain), 1):
                    data = snapshot(payload, digest, expected, parent, watermark, clock, fence)
                    for row in data['changes']:
                        item = {k: v for k, v in row.items() if k != 'seq'}
                        if not insert(db, item): raise ValueError('Duplicate fact sequence')
                    parent, watermark = digest, data['watermark']
                    clock, fence = data['committed_at'], data['fence']
                    db.execute('INSERT INTO checkpoints VALUES(?,?,?,?)', (expected, digest, data['parent'], watermark))
                db.execute('UPDATE control SET epoch=?,owner=NULL,expires=0,generation=?,watermark=?,digest=?', (fence, generation, watermark, parent))
                db.commit()
            with closing(sqlite3.connect(staged.as_uri() + '?mode=ro', uri=True)) as cold:
                if cold.execute('PRAGMA integrity_check').fetchall() != [('ok',)]: raise ValueError('Cold integrity failed')
                rows = cold.execute('SELECT seq,kind,id,body,body_sha FROM facts ORDER BY seq').fetchall()
                if len(rows) != watermark: raise ValueError('Restore count mismatch')
            os.link(staged, destination)
        return sha(encode([[seq, kind, key, decode(body), digest] for seq, kind, key, body, digest in rows]))


def synthetic_batch(number, finals=False):
    event = fact('event', event_id=f'SYNTHETIC-EVENT-{number}', home=f'SYNTHETIC-HOME-{number}', away=f'SYNTHETIC-AWAY-{number}', kickoff=100 * number + 50)
    obs = fact('observation', event_id=event['id'], source='SYNTHETIC_FREE_SOURCE', received_at=100 * number + 10, state='SCHEDULED')
    items = [event, obs]
    for model in MODELS:
        registry = fact('model', model=model, version='SIMULATED_RULES_V1', artifact_sha256=sha(model.encode()), frozen_at=0)
        features = fact('features', event_id=event['id'], model_id=registry['id'], available_at=100 * number + 10, input_observation_ids=[obs['id']], values={'fixture_home_mean': 21, 'fixture_away_mean': 17})
        forecast = fact('forecast', event_id=event['id'], model_id=registry['id'], observation_id=obs['id'], feature_id=features['id'], as_of=100 * number + 20, created_at=100 * number + 20, home_score=21, away_score=17, home_probability=0.6)
        items += [registry, features, forecast]
        if finals:
            final = fact('observation', event_id=event['id'], source='SYNTHETIC_FREE_SOURCE', received_at=100 * number + 60, state='FINAL', home_score=24, away_score=20, verified=True)
            items += [final, fact('settlement', forecast_id=forecast['id'], observation_id=final['id'], policy='SIMULATED_FINAL_V1')]
    if finals: return [item for item in items if item['kind'] == 'settlement' or (item['kind'] == 'observation' and item['body']['state'] == 'FINAL')]
    return items


def demo(generations=20):
    with workspace() as root:
        host = HostedSimulator(root); epoch = host.claim('synthetic-worker', 0, ttl=100 * generations + 100)
        client = PullClient(root); transport = ReadOnlyTransport(host)
        host.commit('synthetic-worker', epoch, 0, 120, synthetic_batch(1))
        host.commit('synthetic-worker', epoch, 1, 160, synthetic_batch(1, True)); client.pull(transport)
        initial = transport.bytes_read
        for number in range(2, generations + 1):
            host.commit('synthetic-worker', epoch, 2 * number - 2, 100 * number + 20, synthetic_batch(number))
            host.commit('synthetic-worker', epoch, 2 * number - 1, 100 * number + 60, synthetic_batch(number, True))
        before = transport.bytes_read; start = time.perf_counter(); client.pull(transport)
        catchup_seconds = time.perf_counter() - start
        start = time.perf_counter(); digest = client.restore(root / 'restored.synthetic.sqlite')
        return {'synthetic': True, 'events': generations, 'generations': 2 * generations, 'website': host.website_view(), 'initial_download_bytes': initial, 'catchup_download_bytes': transport.bytes_read - before, 'retained_object_bytes': sum(p.stat().st_size for p in client.objects.iterdir()), 'retained_version_bytes': sum(p.stat().st_size for p in client.versions.iterdir()), 'cold_sqlite_bytes': (root / 'restored.synthetic.sqlite').stat().st_size, 'catchup_seconds': catchup_seconds, 'restore_seconds': time.perf_counter() - start, 'table_digest': digest}


if __name__ == '__main__':
    print(json.dumps(demo(), indent=2))
