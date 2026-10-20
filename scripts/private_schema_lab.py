"""Local synthetic private-schema extension; uses unchanged Phase10 authenticated Client.
No runtime provisioning, remote DSN, real sport data or provider client.
"""
from pathlib import Path
import concurrent.futures
import hashlib
import json
import os
import secrets
import subprocess
import time

API_ROLES = ('synthetic_api_anon', 'synthetic_api_authenticated')
EXTRA_ROLES = ('synthetic_legacy_owner', *API_ROLES)
SCHEMA = 'synthetic_private_ncaaf'

SETUP = """
CREATE ROLE synthetic_legacy_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
CREATE ROLE synthetic_api_anon NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
CREATE ROLE synthetic_api_authenticated NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
CREATE SCHEMA synthetic_legacy_mlb AUTHORIZATION synthetic_legacy_owner;
SET ROLE synthetic_legacy_owner;
CREATE TABLE synthetic_legacy_mlb.canary(id integer PRIMARY KEY,value integer NOT NULL);
INSERT INTO synthetic_legacy_mlb.canary VALUES(1,0);
ALTER TABLE synthetic_legacy_mlb.canary ENABLE ROW LEVEL SECURITY;
CREATE FUNCTION synthetic_legacy_mlb.bump() RETURNS void LANGUAGE sql SECURITY DEFINER
 SET search_path=pg_catalog,pg_temp AS $$ UPDATE synthetic_legacy_mlb.canary SET value=value+1 WHERE id=1 $$;
-- PUBLIC EXECUTE stays enabled to isolate schema-USAGE from function-EXECUTE semantics.
RESET ROLE;
CREATE SCHEMA synthetic_private_ncaaf AUTHORIZATION ncaaf_lab_owner;
SET ROLE ncaaf_lab_owner;
CREATE TABLE synthetic_private_ncaaf.control(id integer PRIMARY KEY CHECK(id=1),generation bigint NOT NULL,digest text,watermark bigint NOT NULL,fence bigint NOT NULL,expires timestamptz NOT NULL);
INSERT INTO synthetic_private_ncaaf.control VALUES(1,0,NULL,0,0,'epoch');
CREATE TABLE synthetic_private_ncaaf.objects(digest text PRIMARY KEY CHECK(length(digest)=64),payload bytea NOT NULL CHECK(octet_length(payload)<=1048576),CHECK(digest=encode(sha256(payload),'hex')));
CREATE TABLE synthetic_private_ncaaf.journal(generation bigint PRIMARY KEY,digest text UNIQUE NOT NULL REFERENCES synthetic_private_ncaaf.objects(digest),parent text,watermark bigint NOT NULL,fence bigint NOT NULL,source_committed_at bigint NOT NULL);
ALTER TABLE synthetic_private_ncaaf.objects ENABLE ROW LEVEL SECURITY;
ALTER TABLE synthetic_private_ncaaf.objects FORCE ROW LEVEL SECURITY;
ALTER TABLE synthetic_private_ncaaf.journal ENABLE ROW LEVEL SECURITY;
ALTER TABLE synthetic_private_ncaaf.journal FORCE ROW LEVEL SECURITY;
CREATE POLICY objects_owner ON synthetic_private_ncaaf.objects TO ncaaf_lab_owner USING(true) WITH CHECK(true);
CREATE POLICY journal_owner ON synthetic_private_ncaaf.journal TO ncaaf_lab_owner USING(true) WITH CHECK(true);
CREATE POLICY objects_read ON synthetic_private_ncaaf.objects FOR SELECT TO ncaaf_lab_reader,ncaaf_lab_recovery USING(true);
CREATE POLICY journal_read ON synthetic_private_ncaaf.journal FOR SELECT TO ncaaf_lab_reader,ncaaf_lab_recovery USING(true);
CREATE TRIGGER objects_immutable BEFORE UPDATE OR DELETE ON synthetic_private_ncaaf.objects FOR EACH ROW EXECUTE FUNCTION synthetic_ncaaf.immutable_guard();
CREATE TRIGGER journal_immutable BEFORE UPDATE OR DELETE ON synthetic_private_ncaaf.journal FOR EACH ROW EXECUTE FUNCTION synthetic_ncaaf.immutable_guard();
CREATE FUNCTION synthetic_private_ncaaf.claim(expected bigint) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE c synthetic_private_ncaaf.control%ROWTYPE;
BEGIN
 SELECT * INTO c FROM synthetic_private_ncaaf.control WHERE id=1 FOR UPDATE;
 IF c.fence<>expected OR c.expires>clock_timestamp() THEN RAISE EXCEPTION USING ERRCODE='40001',MESSAGE='Private lease/fence rejected'; END IF;
 UPDATE synthetic_private_ncaaf.control SET fence=c.fence+1,expires=clock_timestamp()+interval '20 minutes' WHERE id=1;
 RETURN c.fence+1;
END $$;
CREATE FUNCTION synthetic_private_ncaaf.publish(expected bigint,epoch bigint,payload bytea) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE c synthetic_private_ncaaf.control%ROWTYPE;doc jsonb;h text;
BEGIN
 SELECT * INTO c FROM synthetic_private_ncaaf.control WHERE id=1 FOR UPDATE;
 IF c.generation<>expected OR c.fence<>epoch OR c.expires<=clock_timestamp() THEN RAISE EXCEPTION USING ERRCODE='40001',MESSAGE='Private CAS/fence rejected'; END IF;
 doc=convert_from(payload,'UTF8')::jsonb;h=encode(sha256(payload),'hex');
 IF doc->>'format' IS DISTINCT FROM 'NCAAF_PHASE8B_SYNTHETIC_V1' OR doc->>'synthetic' IS DISTINCT FROM 'true'
 OR (doc->>'generation')::bigint IS DISTINCT FROM expected+1 OR doc->>'parent' IS DISTINCT FROM c.digest
 OR (doc->>'from_seq')::bigint IS DISTINCT FROM c.watermark OR (doc->>'watermark')::bigint<=c.watermark
 OR (doc->>'fence')::bigint IS DISTINCT FROM epoch THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Synthetic lineage/format mismatch'; END IF;
 INSERT INTO synthetic_private_ncaaf.objects VALUES(h,payload);
 INSERT INTO synthetic_private_ncaaf.journal VALUES(expected+1,h,c.digest,(doc->>'watermark')::bigint,epoch,(doc->>'committed_at')::bigint);
 UPDATE synthetic_private_ncaaf.control SET generation=expected+1,digest=h,watermark=(doc->>'watermark')::bigint WHERE id=1;
 RETURN expected+1;
END $$;
GRANT USAGE ON SCHEMA synthetic_private_ncaaf TO ncaaf_lab_writer,ncaaf_lab_reader,ncaaf_lab_recovery,ncaaf_lab_cleanup;
GRANT EXECUTE ON FUNCTION synthetic_private_ncaaf.claim(bigint),synthetic_private_ncaaf.publish(bigint,bigint,bytea) TO ncaaf_lab_writer;
GRANT SELECT ON synthetic_private_ncaaf.objects,synthetic_private_ncaaf.journal TO ncaaf_lab_reader,ncaaf_lab_recovery;
RESET ROLE;
"""


def extra_role_sql():
    return ';'.join('CREATE ROLE '+r+' NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS' for r in EXTRA_ROLES)+';'


def shadow_credentials(c):
    for role in API_ROLES:
        value=secrets.token_urlsafe(48);c.secrets.append(value)
        path=c.root/(str(c.port)+'-'+role+'.pgpass')
        path.write_bytes(f'127.0.0.1:{c.port}:synthetic_permission_lab:{role}:{value}\n'.encode());c.files[role]=path
        c.query('admin',"ALTER ROLE "+role+" LOGIN PASSWORD '"+value+"';")


def private_snapshot(c):
    result={}
    for table in ['synthetic_private_ncaaf.control','synthetic_private_ncaaf.objects','synthetic_private_ncaaf.journal','synthetic_legacy_mlb.canary']:
        result[table]=json.loads(c.query('admin',"SELECT COALESCE(json_agg(x ORDER BY row_to_json(x)::text),'[]') FROM "+table+' x;'))
    result['extra_roles']=json.loads(c.query('admin',"SELECT json_agg(x) FROM (SELECT rolname,rolsuper,rolcreatedb,rolcreaterole,rolbypassrls,rolinherit,rolcanlogin FROM pg_roles WHERE rolname LIKE 'synthetic_api_%' OR rolname='synthetic_legacy_owner' ORDER BY rolname) x;"))
    return result


def canonical_payloads():
    import synthetic_state_v1 as s
    with s.workspace() as root:
        host=s.HostedSimulator(root);epoch=host.claim('PRIVATE_SYNTHETIC',0,ttl=200000)
        result=[];parent=None;watermark=0
        for event in (1,2,3):
            host.commit('PRIVATE_SYNTHETIC',epoch,event-1,event*100+20,s.synthetic_batch(event))
            head=s.ReadOnlyTransport(host).head();payload=(host.objects/(head['digest']+'.json')).read_bytes()
            doc=s.snapshot(payload,head['digest'],event,parent,watermark)
            result.append(payload);parent=head['digest'];watermark=doc['watermark']
        return result


def run_private(c):
    from postgres_advanced_lab import ROLES
    checks=[]
    def ok(name):
        checks.append({'name':name,'status':'PASS'})
        (c.out/'PRIVATE_ASSERTIONS.json').write_bytes(json.dumps(checks,indent=2).encode())
    def eq(name,actual,expected):
        if actual!=expected:raise AssertionError(name+' mismatch STOP')
        ok(name)
    c.query('admin',SETUP);shadow_credentials(c)
    roles=(*ROLES,*API_ROLES)
    for role in roles:
        eq(role+' authenticated identity/attributes/memberships',c.query(role,"SELECT session_user,current_user,rolsuper,rolcreatedb,rolcreaterole,rolbypassrls,rolinherit,(SELECT count(*) FROM pg_auth_members WHERE member=r.oid) FROM pg_roles r WHERE rolname=current_user;"),role+'|'+role+'|f|f|f|f|f|0')
        eq(role+' schema name visible but not secret',c.query(role,"SELECT count(*) FROM pg_namespace WHERE nspname='synthetic_private_ncaaf';"),'1')
        eq(role+' private schema USAGE',c.query(role,"SELECT has_schema_privilege(current_user,'synthetic_private_ncaaf','USAGE');"),'f' if role in API_ROLES else 't')
        eq(role+' MLB USAGE denied',c.query(role,"SELECT has_schema_privilege(current_user,'synthetic_legacy_mlb','USAGE');"),'f')
        c.query(role,'SELECT * FROM synthetic_legacy_mlb.canary;','42501');ok(role+' MLB rows denied')
        c.query(role,'SELECT synthetic_legacy_mlb.bump();','42501');ok(role+' MLB definer denied by schema boundary despite PUBLIC EXECUTE')
        c.query(role,'SET ROLE ncaaf_lab_owner;','42501');ok(role+' owner escalation denied')
        c.query(role,'CREATE FUNCTION synthetic_private_ncaaf.escape() RETURNS integer LANGUAGE sql AS $$SELECT 1$$;','42501');ok(role+' privileged function creation denied')
        for table in ('objects','journal'):
            for operation,sql in [('SELECT','SELECT count(*) FROM '+SCHEMA+'.'+table),('INSERT','INSERT INTO '+SCHEMA+'.'+table+' SELECT * FROM '+SCHEMA+'.'+table+' WHERE false'),('UPDATE','UPDATE '+SCHEMA+'.'+table+' SET '+('digest=digest' if table=='objects' else 'generation=generation')+' WHERE false'),('DELETE','DELETE FROM '+SCHEMA+'.'+table+' WHERE false')]:
                allowed=operation=='SELECT' and role in ('ncaaf_lab_reader','ncaaf_lab_recovery')
                c.query(role,sql+';',None if allowed else '42501');ok(role+' private '+table+' '+operation)
        if role!='ncaaf_lab_writer':
            c.query(role,'SELECT synthetic_private_ncaaf.claim(0);','42501');ok(role+' private claim denied')
            c.query(role,"SELECT synthetic_private_ncaaf.publish(0,1,''::bytea);",'42501');ok(role+' private publish denied')
    # Deliberate EXPECTED risk phase, rolled back; no canary routine is called.
    risk=c.query('admin',"BEGIN; GRANT USAGE ON SCHEMA synthetic_legacy_mlb TO PUBLIC; SELECT has_schema_privilege('ncaaf_lab_writer','synthetic_legacy_mlb','USAGE'),has_function_privilege('ncaaf_lab_writer','synthetic_legacy_mlb.bump()','EXECUTE'); ROLLBACK;")
    eq('Expected PUBLIC capability risk independent of NOINHERIT (rollback probe)',risk,'t|t')
    eq('legacy canary remains unmodified',c.query('admin','SELECT value FROM synthetic_legacy_mlb.canary WHERE id=1;'),'0')
    eq('private functions not PUBLIC executable',c.query('admin',"SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace CROSS JOIN LATERAL aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a WHERE n.nspname='synthetic_private_ncaaf' AND a.grantee=0 AND a.privilege_type='EXECUTE';"),'0')
    payloads=canonical_payloads()
    def publish(g,payload):return "SELECT synthetic_private_ncaaf.publish("+str(g)+",1,decode('"+payload.hex()+"','hex'));"
    writer='ncaaf_lab_writer';reader='ncaaf_lab_reader'
    eq('initial private fence',c.query(writer,'SELECT synthetic_private_ncaaf.claim(0);'),'1')
    eq('canonical generation1 publication',c.query(writer,publish(0,payloads[0])),'1')
    before=private_snapshot(c)
    c.query(writer,publish(0,payloads[0]),'40001');ok('duplicate generation rejects stale CAS')
    eq('duplicate rejection no side effects',private_snapshot(c),before)
    # Hold the row lock in a genuinely authenticated process, then prove competing lock wait.
    def hold(label,sql):
        so=(c.out/(label+'.stdout.log')).open('wb');se=(c.out/(label+'.stderr.log')).open('wb')
        p=subprocess.Popen(c.command(),env=c.environment(writer,label),stdin=subprocess.PIPE,stdout=so,stderr=se,close_fds=True,creationflags=0x08000000 if os.name=='nt' else 0)
        p.stdin.write(('BEGIN;'+sql+"SELECT 'READY_PRIVATE';\n").encode());p.stdin.flush();deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            if 'READY_PRIVATE' in (c.out/(label+'.stdout.log')).read_text():return p,so,se
            if p.poll() is not None:break
            time.sleep(.05)
        if p.poll() is None:p.kill();p.wait(timeout=5)
        so.close();se.close();raise AssertionError('Private held session failed STOP')
    def finish(h,commit):
        p,so,se=h
        try:
            p.communicate(input=b'COMMIT;\n' if commit else b'ROLLBACK;\n',timeout=10);assert p.returncode==0
        finally:
            if p.poll() is None:p.kill();p.wait(timeout=5)
            so.close();se.close()
    h=hold('private-CAS',publish(1,payloads[1]))
    try:
        eq('reader cannot observe uncommitted generation2',c.query(reader,'SELECT count(*) FROM synthetic_private_ncaaf.journal;'),'1')
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            loser=pool.submit(c.query,writer,publish(1,payloads[1]),'40001');deadline=time.monotonic()+8
            while c.query('admin',"SELECT count(*) FROM pg_stat_activity WHERE usename='ncaaf_lab_writer' AND wait_event_type='Lock';")=='0':
                if time.monotonic()>deadline:raise AssertionError('Private CAS contention not observed STOP')
                time.sleep(.05)
            finish(h,True);h=None;loser.result(timeout=15)
        ok('actual concurrent private CAS exactly1winner1stale40001')
    finally:
        if h:finish(h,False)
    eq('exactly2committed generations',c.query(reader,'SELECT count(*),max(generation) FROM synthetic_private_ncaaf.journal;'),'2|2')
    stable=private_snapshot(c)
    c.query(writer,'BEGIN;'+publish(2,payloads[2])+'SELECT 1/0; COMMIT;','22012');ok('private transaction failure before COMMIT')
    eq('failed private publication fully rolls back',private_snapshot(c),stable)
    c.query('admin','UPDATE synthetic_private_ncaaf.objects SET digest=digest;','55000');ok('private objects immutable')
    c.query('admin','DELETE FROM synthetic_private_ncaaf.journal;','55000');ok('private journal immutable')
    c.query('admin',"ALTER POLICY objects_read ON synthetic_private_ncaaf.objects USING(false);")
    eq('forced RLS reader exclusion',c.query(reader,'SELECT count(*) FROM synthetic_private_ncaaf.objects;'),'0')
    c.query('admin','ALTER POLICY objects_read ON synthetic_private_ncaaf.objects USING(true);')
    c.query('admin','REVOKE EXECUTE ON FUNCTION synthetic_private_ncaaf.publish(bigint,bigint,bytea) FROM ncaaf_lab_writer;')
    c.query(writer,publish(2,payloads[2]),'42501');ok('fresh connection privilege revocation analogue')
    c.query('admin','GRANT EXECUTE ON FUNCTION synthetic_private_ncaaf.publish(bigint,bigint,bytea) TO ncaaf_lab_writer;')
    eq('qualified definer immune to temporary control shadow',c.query(writer,"BEGIN; CREATE TEMP TABLE control(generation bigint); INSERT INTO pg_temp.control VALUES(999); SET LOCAL search_path=pg_temp; "+publish(2,payloads[2])+"SELECT generation FROM pg_temp.control; ROLLBACK;").splitlines(),['3','999'])
    c.query('admin',"UPDATE synthetic_private_ncaaf.control SET expires='epoch';")
    c.query(writer,publish(2,payloads[2]),'40001');ok('private expired lease rejects writes')
    eq('private reviewed fixture takeover epoch2',c.query(writer,'SELECT synthetic_private_ncaaf.claim(1);'),'2')
    c.query(writer,publish(2,payloads[2]),'40001');ok('old epoch rejected after takeover')
    recovered=c.query('ncaaf_lab_recovery',"SELECT encode(payload,'hex') FROM synthetic_private_ncaaf.objects ORDER BY (convert_from(payload,'UTF8')::jsonb->>'generation')::integer;").splitlines()
    eq('canonical original payload bytes preserved',recovered,[v.hex() for v in payloads[:2]])
    (c.out/'PRIVATE_PAYLOAD_HASHES.json').write_bytes(json.dumps([hashlib.sha256(v).hexdigest() for v in payloads[:2]],indent=2).encode())
    return checks


def restored_checks(c):
    shadow_credentials(c);checks=[]
    for role in API_ROLES:
        actual=c.query(role,"SELECT session_user,current_user,rolsuper,rolcreatedb,rolcreaterole,rolbypassrls,rolinherit,(SELECT count(*) FROM pg_auth_members WHERE member=r.oid) FROM pg_roles r WHERE rolname=current_user;")
        assert actual==role+'|'+role+'|f|f|f|f|f|0';checks.append(role+' restored identity')
    from postgres_advanced_lab import ROLES
    for role in (*ROLES,*API_ROLES):
        c.query(role,'SELECT synthetic_legacy_mlb.bump();','42501');checks.append(role+' restored MLB denial')
        c.query(role,'DELETE FROM synthetic_private_ncaaf.journal;','42501');checks.append(role+' restored private mutation denial')
    assert c.query('ncaaf_lab_reader','SELECT count(*) FROM synthetic_private_ncaaf.journal;')=='2';checks.append('restored2canonical generations')
    return checks
