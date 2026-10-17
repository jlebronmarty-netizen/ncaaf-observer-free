"""Offline synthetic durable-store simulator. No provider, credential or network API."""
from contextlib import closing
import hashlib
import hmac
import math
import sqlite3
import time
import synthetic_state_v1 as s
import readonly_projection_v1 as projection

VERSION = 'NCAAF_OFFLINE_BRIDGE_V1'
REQUESTS = 1000
FOOTPRINT = 32 * 1024 * 1024
TRANSFER = 64 * 1024 * 1024
SECONDS = 20 * 60


class Store:
    """SQLite simulates remote persistence; HMAC fixture key is supplied only in memory.

    Roles are simulated labels, not provider IAM. Clock is one trusted monotonic era.
    """
    def __init__(self, root, fixture_key, clock=time.monotonic):
        self.root = s.guard(root)
        if not isinstance(fixture_key, bytes) or len(fixture_key) != 32: raise ValueError('Synthetic fixture key')
        self._key = fixture_key
        self.clock = clock
        self.path = self.root / 'bridge.synthetic.sqlite'
        fresh = not s.exists(self.path)
        with closing(s.connect(self.path, create=fresh)) as db, db:
            if fresh:
                s.schema(db)
                db.executescript("""
                CREATE TABLE bridge_meta(version TEXT NOT NULL,epoch INTEGER,owner TEXT,expires REAL,generation INTEGER,digest TEXT,watermark INTEGER,commit_clock INTEGER,requests INTEGER,transfer INTEGER,tick REAL,runtime REAL);
                CREATE TABLE bridge_objects(digest TEXT PRIMARY KEY,payload BLOB NOT NULL);
                CREATE TABLE bridge_journal(generation INTEGER PRIMARY KEY,receipt BLOB NOT NULL);
                CREATE TRIGGER bridge_objects_immutable BEFORE UPDATE ON bridge_objects BEGIN SELECT RAISE(ABORT,'Immutable'); END;
                CREATE TRIGGER bridge_journal_immutable BEFORE UPDATE ON bridge_journal BEGIN SELECT RAISE(ABORT,'Immutable'); END;
                """)
                db.execute('INSERT INTO bridge_meta VALUES(?,0,NULL,0,0,NULL,0,-1,0,0,?,0)', (VERSION, self.clock()))
            if db.execute('SELECT version FROM bridge_meta').fetchall() != [(VERSION,)]: raise ValueError('Bridge namespace')
            if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]: raise ValueError('Bridge SQLite integrity')

    def _footprint(self, db):
        # Conservative headroom covers commit bookkeeping; inspect active sidecars too.
        pages = db.execute('PRAGMA page_count').fetchone()[0] * db.execute('PRAGMA page_size').fetchone()[0]
        sidecars = sum(s.plain(p, directory=False).st_size for p in self.root.glob(self.path.name + '-*'))
        if pages + sidecars + 65536 > FOOTPRINT: raise ValueError('Footprint budget')

    def _meter(self, db, size=0):
        now = self.clock()
        if type(now) not in (int,float) or not math.isfinite(now): raise ValueError('Budget clock')
        requests, transfer, tick, runtime = db.execute('SELECT requests,transfer,tick,runtime FROM bridge_meta').fetchone()
        if type(requests) is not int or not 0 <= requests <= REQUESTS or type(transfer) is not int or not 0 <= transfer <= TRANSFER or type(tick) not in (int,float) or not math.isfinite(tick) or type(runtime) not in (int,float) or not math.isfinite(runtime) or runtime < 0: raise ValueError('Corrupt budget metadata')
        if type(size) is not int or size < 0 or now < tick: raise ValueError('Budget clock/bytes')
        elapsed = runtime + now - tick
        if requests + 1 > REQUESTS or transfer + size > TRANSFER or elapsed > SECONDS: raise ValueError('Pilot budget exhausted')
        db.execute('UPDATE bridge_meta SET requests=?,transfer=?,tick=?,runtime=?', (requests + 1, transfer + size, now, elapsed))
        self._footprint(db)

    def _call(self, role, allowed, operation):
        # Charge denied/failed attempts too; budget survives clean client restarts.
        with closing(s.connect(self.path)) as db, db:
            db.execute('BEGIN IMMEDIATE'); self._meter(db)
        if role not in allowed: raise PermissionError('Simulated identity denied')
        with closing(s.connect(self.path)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            result = operation(db)
            self._footprint(db)
            return result

    def _signed(self, body):
        return {'body': body, 'tag': hmac.new(self._key, s.encode(body), hashlib.sha256).hexdigest()}

    def verify(self, receipt):
        if not isinstance(receipt, dict) or set(receipt) != {'body', 'tag'}: raise ValueError('Receipt contract')
        body = receipt['body']
        if not isinstance(body, dict) or set(body) != {'version','synthetic','generation','digest','parent','watermark','fence','committed_at'} or body['version'] != VERSION or body['synthetic'] is not True:
            raise ValueError('Receipt namespace')
        if not isinstance(receipt['tag'], str) or not hmac.compare_digest(receipt['tag'], self._signed(body)['tag']): raise ValueError('Receipt authentication')
        s.checkpoint_identity({'generation': body['generation'], 'digest': body['digest']})
        return body

    def claim(self, role, owner, *, ttl=60, reviewed=False):
        def op(db):
            if not isinstance(owner, str) or not 1 <= len(owner) <= 64 or type(ttl) is not int or not 1 <= ttl <= 1200: raise ValueError('Lease request')
            epoch, prior, expires = db.execute('SELECT epoch,owner,expires FROM bridge_meta').fetchone()
            now = self.clock()
            if prior is not None and (now < expires or not reviewed): raise ValueError('Lease active/review missing')
            db.execute('UPDATE bridge_meta SET epoch=?,owner=?,expires=?', (epoch+1,owner,now+ttl)); return epoch+1
        return self._call(role, {'writer'}, op)

    def put(self, role, payload):
        def op(db):
            if not isinstance(payload, bytes) or not 0 < len(payload) <= s.MAX_BYTES: raise ValueError('Object budget')
            s.decode(payload); digest = s.sha(payload)
            db.execute('UPDATE bridge_meta SET transfer=transfer+?', (len(payload),))
            if db.execute('SELECT transfer FROM bridge_meta').fetchone()[0] > TRANSFER: raise ValueError('Transfer budget')
            old = db.execute('SELECT payload FROM bridge_objects WHERE digest=?', (digest,)).fetchone()
            if old and old[0] != payload: raise ValueError('Object conflict')
            if not old: db.execute('INSERT INTO bridge_objects VALUES(?,?)', (digest,payload))
            self._footprint(db)
            return digest
        return self._call(role, {'writer'}, op)

    def publish(self, role, owner, epoch, expected, digest, fault=False):
        def op(db):
            e,o,expires,g,parent,watermark,clock = db.execute('SELECT epoch,owner,expires,generation,digest,watermark,commit_clock FROM bridge_meta').fetchone()
            if type(g) is not int or not 0 <= g < s.MAX_GENERATIONS or type(watermark) is not int or not 0 <= watermark <= projection.MAX_FACTS or type(clock) is not int or clock < -1: raise ValueError('Corrupt committed metadata')
            if type(epoch) is not int or type(expected) is not int or (epoch,owner)!=(e,o) or self.clock() >= expires: raise ValueError('Stale writer')
            if not s.valid_digest(digest): raise ValueError('Digest')
            # Exact duplicate retry after an acknowledged or uncertain commit.
            if expected == g-1 and digest == parent:
                receipt = s.decode(db.execute('SELECT receipt FROM bridge_journal WHERE generation=?',(g,)).fetchone()[0]); self.verify(receipt); return receipt
            if expected != g or g >= s.MAX_GENERATIONS: raise ValueError('Generation CAS')
            row = db.execute('SELECT payload FROM bridge_objects WHERE digest=?',(digest,)).fetchone()
            if row is None: raise ValueError('Missing object')
            previous_fence = 0
            if g:
                prior = s.decode(db.execute('SELECT receipt FROM bridge_journal WHERE generation=?',(g,)).fetchone()[0]); previous_fence = self.verify(prior)['fence']
            data = s.snapshot(row[0],digest,g+1,parent,watermark,clock,previous_fence)
            # Validate complete fact lineage before any committed publication.
            with closing(sqlite3.connect(':memory:')) as verifier:
                verifier.execute('PRAGMA temp_store=MEMORY'); s.schema(verifier)
                replay_parent=None; replay_mark=0; replay_clock=-1; replay_fence=0; replay_bytes=0
                for number in range(1,g+2):
                    if number==g+1: raw=row[0]; candidate_digest=digest
                    else:
                        old=s.decode(db.execute('SELECT receipt FROM bridge_journal WHERE generation=?',(number,)).fetchone()[0]); oldbody=self.verify(old)
                        raw=db.execute('SELECT payload FROM bridge_objects WHERE digest=?',(oldbody['digest'],)).fetchone()[0]
                        candidate_digest=oldbody['digest']
                    replay_bytes+=len(raw)
                    if replay_bytes>s.MAX_SESSION_BYTES: raise ValueError('Lineage byte budget')
                    candidate=s.snapshot(raw,candidate_digest,number,replay_parent,replay_mark,replay_clock,replay_fence)
                    if number<=g and any(oldbody[k]!=candidate[k] for k in ('generation','parent','watermark','fence','committed_at')): raise ValueError('Parent receipt mismatch')
                    replay_parent,replay_mark,replay_clock,replay_fence=candidate_digest,candidate['watermark'],candidate['committed_at'],candidate['fence']
                    for change in candidate['changes']:
                        item={k:v for k,v in change.items() if k!='seq'}
                        if item['kind']=='forecast' and item['body']['created_at']!=candidate['committed_at']: raise ValueError('Backdated forecast')
                        if item['kind']=='observation' and item['body']['received_at']>candidate['committed_at']: raise ValueError('Future observation')
                        if not s.insert(verifier,item): raise ValueError('Duplicate immutable identity')
                    if verifier.execute('SELECT count(*) FROM facts').fetchone()[0]>projection.MAX_FACTS: raise ValueError('Fact budget')
            # Bridge lease epochs and source fencing are separate unchanged contracts.
            receipt = self._signed({'version':VERSION,'synthetic':True,**{k:data[k] for k in ('generation','parent','watermark','fence','committed_at')},'digest':digest})
            db.execute('INSERT INTO bridge_journal VALUES(?,?)',(g+1,s.encode(receipt)))
            if fault: raise OSError('Injected interrupted publication')
            db.execute('UPDATE bridge_meta SET generation=?,digest=?,watermark=?,commit_clock=?',(g+1,digest,data['watermark'],data['committed_at']))
            return receipt
        return self._call(role, {'writer'}, op)

    def head(self, role):
        def op(db):
            g,digest = db.execute('SELECT generation,digest FROM bridge_meta').fetchone()
            if not g: raise ValueError('No committed generation')
            if db.execute('SELECT count(*),max(generation) FROM bridge_journal').fetchone()!=(g,g): raise ValueError('Uncommitted journal')
            row=db.execute('SELECT receipt FROM bridge_journal WHERE generation=?',(g,)).fetchone()
            if not row: raise ValueError('Missing journal')
            receipt=s.decode(row[0]); body=self.verify(receipt)
            if (body['generation'],body['digest'])!=(g,digest): raise ValueError('Head mismatch')
            return receipt
        return self._call(role, {'writer','reader','recovery'}, op)

    def checkpoint(self, role, generation):
        def op(db):
            if type(generation) is not int or not 1 <= generation <= s.MAX_GENERATIONS: raise ValueError('Generation')
            row=db.execute('SELECT receipt FROM bridge_journal WHERE generation=?',(generation,)).fetchone()
            if row is None: raise ValueError('Missing committed generation')
            receipt=s.decode(row[0]); self.verify(receipt); return receipt
        return self._call(role, {'reader','recovery'}, op)

    def fetch(self, role, digest):
        def op(db):
            if not s.valid_digest(digest): raise ValueError('Digest')
            # No enumeration or retrieval of orphan objects.
            committed=False
            for (raw,) in db.execute('SELECT receipt FROM bridge_journal ORDER BY generation LIMIT ?', (s.MAX_GENERATIONS,)):
                if self.verify(s.decode(raw))['digest']==digest: committed=True; break
            if not committed: raise PermissionError('Uncommitted identity')
            row=db.execute('SELECT payload FROM bridge_objects WHERE digest=?',(digest,)).fetchone()
            if row is None or s.sha(row[0])!=digest: raise ValueError('Missing/corrupt object')
            size=len(row[0]); used=db.execute('SELECT transfer FROM bridge_meta').fetchone()[0]
            if used+size>TRANSFER: raise ValueError('Transfer budget')
            db.execute('UPDATE bridge_meta SET transfer=transfer+?',(size,)); return row[0]
        return self._call(role, {'reader','recovery'}, op)


def reconstruct(store, role, floor, request, *, now):
    """Fresh disposable authority, never copy live DB; authenticated floor supplied externally."""
    trusted=store.verify(floor); head=store.head(role); top=store.verify(head)
    if top['generation']<trusted['generation']: raise ValueError('Checkpoint rollback')
    if store.checkpoint(role,trusted['generation'])!=floor: raise ValueError('Floor equivocation')
    with s.workspace() as root:
        host=s.HostedSimulator(root)  # creates only fresh synthetic schema, not forecasts
        parent=None;watermark=0;clock=-1;fence=0;total=0
        with closing(s.connect(host.path)) as db, db:
            for g in range(1,top['generation']+1):
                receipt=store.checkpoint(role,g); body=store.verify(receipt); payload=store.fetch(role,body['digest']);total+=len(payload)
                if total>s.MAX_SESSION_BYTES: raise ValueError('Reconstruction budget')
                data=s.snapshot(payload,body['digest'],g,parent,watermark,clock,fence)
                if any(body[k]!=data[k] for k in ('generation','parent','watermark','fence','committed_at')): raise ValueError('Receipt/object mismatch')
                for row in data['changes']:
                    if not s.insert(db,{k:v for k,v in row.items() if k!='seq'}): raise ValueError('Duplicate fact')
                if data['watermark']>projection.MAX_FACTS: raise ValueError('Fact budget')
                s.no_clobber(host.objects/(body['digest']+'.json'),payload)
                db.execute('INSERT INTO checkpoints VALUES(?,?,?,?)',(g,body['digest'],parent,data['watermark']))
                parent,watermark,clock,fence=body['digest'],data['watermark'],data['committed_at'],data['fence']
            if parent!=top['digest']: raise ValueError('Frozen head mismatch')
            db.execute('UPDATE control SET generation=?,digest=?,watermark=?,epoch=?,owner=NULL,expires=0',(top['generation'],parent,watermark,fence))
        return projection.Reader(root).project(request,floor={'generation':trusted['generation'],'digest':trusted['digest']},now=now),head
