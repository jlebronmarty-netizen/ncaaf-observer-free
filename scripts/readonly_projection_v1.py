"""Local synthetic read capability. No HTTP, host object, mutation or cache API."""
from contextlib import closing
import sqlite3
import synthetic_state_v1 as s

VERSION = 'NCAAF_SYNTHETIC_PROJECTION_V1'
MAX_FACTS = 10000
MAX_OUTPUT = 65536


class Reader:
    def __init__(self, root):
        host = s.guard(root) / 'simulated-host'
        if s.read(host / '.host-format', 256) != s.encode({'format': s.FORMAT}):
            raise ValueError('Incompatible host')
        self._path = host / 'synthetic.sqlite'
        self._objects = host / 'objects'

    def project(self, request, *, floor, now):
        """Caller supplies trusted persisted floor and clock; no implicit reset on restart."""
        if not isinstance(request, dict) or set(request) != {'version', 'offset', 'limit', 'max_age'} or request['version'] != VERSION:
            raise ValueError('Request contract')
        for k, low, high in [('offset', 0, MAX_FACTS), ('limit', 1, 50), ('max_age', 0, 86400)]:
            if type(request[k]) is not int or not low <= request[k] <= high: raise ValueError('Request budget')
        if type(now) is not int or now < 0: raise ValueError('Clock contract')
        s.checkpoint_identity(floor)
        with closing(s.connect(self._path, readonly=True)) as db:
            db.execute('PRAGMA temp_store=MEMORY')
            db.execute('BEGIN')
            if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]: raise ValueError('SQLite integrity')
            generation, watermark, digest = db.execute('SELECT generation,watermark,digest FROM control').fetchone()
            s.checkpoint_identity({'generation': generation, 'digest': digest})
            if generation < floor['generation'] or not 0 < watermark <= MAX_FACTS: raise ValueError('Rollback/budget')
            checkpoints = db.execute('SELECT generation,digest,parent,watermark FROM checkpoints ORDER BY generation LIMIT ?', (s.MAX_GENERATIONS + 1,)).fetchall()
            if len(checkpoints) != generation: raise ValueError('Uncommitted head')
            if checkpoints[floor['generation'] - 1][1] != floor['digest']: raise ValueError('Conflicting floor')
            parent = None; count = 0; clock = -1; fence = 0; budget = 0
            with closing(sqlite3.connect(':memory:')) as verified:
                verified.execute('PRAGMA temp_store=MEMORY')
                s.schema(verified)
                for expected, (g, sha, previous, mark) in enumerate(checkpoints, 1):
                    if g != expected or not s.valid_digest(sha): raise ValueError('Checkpoint sequence')
                    payload = s.read(self._objects / (sha + '.json')); budget += len(payload)
                    if budget > s.MAX_SESSION_BYTES: raise ValueError('Read budget')
                    data = s.snapshot(payload, sha, expected, parent, count, clock, fence)
                    if previous != parent or mark != data['watermark'] or mark > MAX_FACTS: raise ValueError('Journal mismatch')
                    for row in data['changes']:
                        item = {k: v for k, v in row.items() if k != 'seq'}
                        if not s.insert(verified, item): raise ValueError('Duplicate fact')
                    parent, count, clock, fence = sha, mark, data['committed_at'], data['fence']
                if (parent, count) != (digest, watermark): raise ValueError('Head mismatch')
                if not clock <= now <= clock + request['max_age']: raise ValueError('Stale state/clock rollback')
                rows = db.execute('SELECT seq,kind,id,body,body_sha FROM facts ORDER BY seq LIMIT ?', (MAX_FACTS + 1,)).fetchall()
                expected_rows = verified.execute('SELECT seq,kind,id,body,body_sha FROM facts ORDER BY seq').fetchall()
                if rows != expected_rows: raise ValueError('Authority/object mismatch')
                forecasts = verified.execute("SELECT id,body FROM facts WHERE kind='forecast' ORDER BY seq").fetchall()
                page = []
                for identity, raw in forecasts[request['offset']:request['offset'] + request['limit']]:
                    body = s.decode(raw)
                    settlement = verified.execute("SELECT body FROM facts WHERE kind='settlement' AND id=?", (identity,)).fetchone()
                    reviews = verified.execute("SELECT body FROM facts WHERE kind='review'").fetchall()
                    reviewed = any(s.decode(r[0])['forecast_id'] == identity for r in reviews)
                    final = None
                    if settlement:
                        final_body = s.lookup(verified, 'observation', s.decode(settlement[0])['observation_id'])
                        final = {k: final_body[k] for k in ('home_score', 'away_score')}
                    page.append({'id': identity, 'event_id': body['event_id'], 'model_id': body['model_id'], 'as_of': body['as_of'], 'created_at': body['created_at'], 'home_score': body['home_score'], 'away_score': body['away_score'], 'home_probability': body['home_probability'], 'final': final, 'review_required': reviewed})
                result = {'schema_version': VERSION, 'synthetic': True, 'generation': generation, 'head_digest': digest, 'watermark': watermark, 'committed_at': clock, 'fence': fence, 'offset': request['offset'], 'total': len(forecasts), 'forecasts': page}
                output = s.encode(result)
                if len(output) > MAX_OUTPUT: raise ValueError('Output budget')
                return output
