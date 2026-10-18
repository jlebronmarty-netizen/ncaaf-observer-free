"""Synthetic-only, localhost PostgreSQL engine probes; no provisioning or provider client.

Requires the unchanged Phase10D fixture in a fresh private owned cluster.
All credentials are temporary private passfiles, never argv or test records.
"""
from pathlib import Path
import concurrent.futures
import hashlib
import json
import os
import re
import secrets
import subprocess
import threading
import time

ROLES = ('ncaaf_lab_writer', 'ncaaf_lab_reader', 'ncaaf_lab_recovery', 'ncaaf_lab_cleanup')
MARKER = 'NCAAF_SYNTHETIC_PG_LAB_V1'


def verify_backup(path, expected_hash, maximum=16 * 1024 * 1024):
    """A trusted external expected hash is required; never trust a colocated replacement."""
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= maximum:
        raise ValueError('Missing/unsafe/oversized recovery material')
    if not re.fullmatch('[0-9a-f]{64}', expected_hash):
        raise ValueError('Invalid trusted digest')
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
        raise ValueError('Recovery integrity mismatch')
    return path


class Client:
    def __init__(self, binary, port, private_root, admin_passfile, artifacts):
        self.root = Path(private_root).resolve()
        self.binary = Path(binary).resolve()
        self.out = Path(artifacts).resolve()
        if (self.root / '.ncaaf-pg-lab').read_text() != MARKER or self.binary != self.root / 'pgsql/bin':
            raise ValueError('Unowned runtime')
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError('Invalid local port')
        self.port = port
        self.files = {'admin': Path(admin_passfile).resolve()}
        if not self.files['admin'].is_relative_to(self.root):
            raise ValueError('Unowned admin passfile')
        self.secrets = []
        self.records = []
        self.counter = 0
        self.log_lock = threading.Lock()

    def environment(self, role, app='NCAAF_SYNTHETIC_PHASE10E'):
        env = {k: v for k, v in os.environ.items() if not k.startswith(('PG', 'POSTGRES'))}
        env.update(PGHOST='127.0.0.1', PGPORT=str(self.port), PGUSER='synthetic_lab_admin' if role == 'admin' else role,
                   PGDATABASE='synthetic_permission_lab', PGPASSFILE=str(self.files[role]),
                   PGCONNECT_TIMEOUT='5', PGAPPNAME=app)
        return env

    def command(self):
        return [str(self.binary / 'psql.exe'), '-X', '-w', '-q', '-A', '-t', '-v', 'ON_ERROR_STOP=1', '-v', 'VERBOSITY=verbose']

    def query(self, role, sql, expected_error=None):
        p = subprocess.run(self.command(), input=sql.encode(), env=self.environment(role), stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=20, close_fds=True, creationflags=0x08000000 if os.name == 'nt' else 0)
        stdout = p.stdout.decode(errors='replace'); stderr = p.stderr.decode(errors='replace')
        for value in self.secrets:
            stdout = stdout.replace(value, '[REDACTED]'); stderr = stderr.replace(value, '[REDACTED]')
        with self.log_lock:
            self.counter += 1
            label = f'query-{self.counter:04d}'
            (self.out / (label + '.stdout.log')).write_bytes(stdout.encode())
            (self.out / (label + '.stderr.log')).write_bytes(stderr.encode())
            record = {'label': label, 'identity': role, 'exit': p.returncode, 'expected_error': expected_error}
            self.records.append(record)
            (self.out / 'QUERIES.json').write_bytes(json.dumps(self.records, indent=2).encode())
        if expected_error is None:
            if p.returncode: raise AssertionError(label + ': unexpected SQL/authentication failure; STOP')
        elif p.returncode == 0 or not re.search(r'ERROR:\s+' + expected_error + r':', stderr):
            raise AssertionError(label + ': expected precise SQLSTATE absent; STOP')
        return stdout.strip()

    def credentials(self):
        for role in ROLES:
            value = secrets.token_urlsafe(48); self.secrets.append(value)
            path = self.root / (str(self.port) + '-' + role + '.pgpass')
            path.write_bytes(f'127.0.0.1:{self.port}:synthetic_permission_lab:{role}:{value}\n'.encode())
            self.files[role] = path
            self.query('admin', "ALTER ROLE " + role + " LOGIN PASSWORD '" + value + "';")

    def close(self):
        for role, path in self.files.items():
            if role != 'admin': path.unlink(missing_ok=True)
        self.secrets.clear()


SETUP = """
CREATE SCHEMA synthetic_unrelated;
CREATE TABLE synthetic_unrelated.canary(id integer);
INSERT INTO synthetic_unrelated.canary VALUES(1);
CREATE SCHEMA synthetic_phase10e AUTHORIZATION ncaaf_lab_owner;
SET ROLE ncaaf_lab_owner;
CREATE TABLE synthetic_phase10e.settlements(
 forecast_id text PRIMARY KEY REFERENCES synthetic_ncaaf.forecasts(id),
 result integer NOT NULL, marker text NOT NULL CHECK(marker='NCAAF_SYNTHETIC'));
ALTER TABLE synthetic_phase10e.settlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE synthetic_phase10e.settlements FORCE ROW LEVEL SECURITY;
CREATE POLICY settlement_owner ON synthetic_phase10e.settlements TO ncaaf_lab_owner USING(true) WITH CHECK(true);
CREATE POLICY settlement_read ON synthetic_phase10e.settlements FOR SELECT TO ncaaf_lab_reader,ncaaf_lab_recovery USING(true);
CREATE TRIGGER settlement_immutable BEFORE UPDATE OR DELETE ON synthetic_phase10e.settlements FOR EACH ROW EXECUTE FUNCTION synthetic_ncaaf.immutable_guard();
CREATE FUNCTION synthetic_phase10e.settle(fid text, outcome integer) RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE actual integer;
BEGIN
 INSERT INTO synthetic_phase10e.settlements VALUES(fid,outcome,'NCAAF_SYNTHETIC') ON CONFLICT DO NOTHING RETURNING result INTO actual;
 IF NOT FOUND THEN SELECT result INTO actual FROM synthetic_phase10e.settlements WHERE forecast_id=fid; END IF;
 IF actual IS DISTINCT FROM outcome THEN RAISE EXCEPTION USING ERRCODE='23505',MESSAGE='Conflicting immutable synthetic settlement'; END IF;
 RETURN actual;
END $$;
GRANT USAGE ON SCHEMA synthetic_phase10e TO ncaaf_lab_writer,ncaaf_lab_reader,ncaaf_lab_recovery,ncaaf_lab_cleanup;
GRANT EXECUTE ON FUNCTION synthetic_phase10e.settle(text,integer) TO ncaaf_lab_writer;
GRANT SELECT ON synthetic_phase10e.settlements TO ncaaf_lab_reader,ncaaf_lab_recovery;
-- Live default-privilege canaries created after baseline hardening.
CREATE TABLE synthetic_ncaaf.default_probe(id integer);
CREATE FUNCTION synthetic_ncaaf.default_probe() RETURNS integer LANGUAGE sql AS 'SELECT 1';
RESET ROLE;
"""


def snapshot(c):
    """Canonical rows plus relevant definitions/privileges; excludes random passwords/OIDs."""
    rows = {}
    for table in ['synthetic_ncaaf.control', 'synthetic_ncaaf.forecasts', 'synthetic_ncaaf.checkpoints', 'synthetic_phase10e.settlements']:
        rows[table] = json.loads(c.query('admin', "SELECT COALESCE(json_agg(x ORDER BY row_to_json(x)::text),'[]') FROM " + table + ' x;'))
    queries = {
        'roles': "SELECT rolname,rolsuper,rolinherit,rolcreaterole,rolcreatedb,rolcanlogin,rolbypassrls FROM pg_roles WHERE rolname LIKE 'ncaaf_lab_%' ORDER BY rolname",
        'constraints': "SELECT n.nspname,c.conname,pg_get_constraintdef(c.oid) AS definition FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname LIKE 'synthetic_%' ORDER BY 1,2",
        'tables': "SELECT n.nspname,c.relname,c.relrowsecurity,c.relforcerowsecurity,c.relacl::text FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname LIKE 'synthetic_%' AND c.relkind='r' ORDER BY 1,2",
        'schemas': "SELECT nspname,nspacl::text FROM pg_namespace WHERE nspname LIKE 'synthetic_%' ORDER BY 1",
        'policies': "SELECT * FROM pg_policies WHERE schemaname LIKE 'synthetic_%' ORDER BY schemaname,tablename,policyname",
        'functions': "SELECT n.nspname,p.proname,pg_get_functiondef(p.oid) AS definition,p.proacl::text FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname LIKE 'synthetic_%' ORDER BY 1,2",
        'triggers': "SELECT n.nspname,c.relname,t.tgname,pg_get_triggerdef(t.oid) AS definition FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname LIKE 'synthetic_%' AND NOT t.tgisinternal ORDER BY 1,2,3",
        'defaults': "SELECT r.rolname,d.defaclobjtype,n.nspname,d.defaclacl::text FROM pg_default_acl d JOIN pg_roles r ON r.oid=d.defaclrole LEFT JOIN pg_namespace n ON n.oid=d.defaclnamespace WHERE r.rolname LIKE 'ncaaf_lab_%' ORDER BY 1,2,3",
        'memberships': "SELECT a.rolname AS member,b.rolname AS parent,m.admin_option,m.inherit_option,m.set_option FROM pg_auth_members m JOIN pg_roles a ON a.oid=m.member JOIN pg_roles b ON b.oid=m.roleid WHERE a.rolname LIKE 'ncaaf_lab_%' OR b.rolname LIKE 'ncaaf_lab_%' ORDER BY 1,2",
    }
    for key, sql in queries.items(): rows[key] = json.loads(c.query('admin', "SELECT COALESCE(json_agg(x),'[]') FROM (" + sql + ') x;'))
    return rows


def run_advanced(c):
    results = []
    def passed(name, detail=None):
        results.append({'name': name, 'status': 'PASS', 'detail': detail})
        (c.out / 'ADVANCED_ASSERTIONS.json').write_bytes(json.dumps(results, indent=2).encode())
    def eq(name, actual, expected):
        if actual != expected: raise AssertionError(name + ': mismatch; STOP')
        passed(name, actual)
    c.credentials()
    c.query('admin', SETUP)
    writer, reader, recovery, cleanup = ROLES
    # Exhaustive finite matrix: all listed roles x tables x CRUD/TRUNCATE/REFERENCES/TRIGGER.
    tables = ['synthetic_ncaaf.control','synthetic_ncaaf.forecasts','synthetic_ncaaf.checkpoints','synthetic_ncaaf.default_probe','synthetic_phase10e.settlements','synthetic_mlb.canary','synthetic_unrelated.canary']
    functions = ['synthetic_ncaaf.claim(bigint,integer)','synthetic_ncaaf.publish(bigint,bigint,text,integer)','synthetic_ncaaf.cleanup_receipt()','synthetic_ncaaf.default_probe()','synthetic_mlb.bump_canary()','synthetic_phase10e.settle(text,integer)']
    oids = {table: c.query('admin',"SELECT '"+table+"'::regclass::oid;") for table in tables}
    for role in ROLES:
        identity = c.query(role, "SELECT session_user,current_user,rolsuper,rolcreatedb,rolcreaterole,rolbypassrls,rolinherit,(SELECT count(*) FROM pg_auth_members WHERE member=r.oid) FROM pg_roles r WHERE rolname=current_user;")
        eq(role + ' direct identity/attributes/memberships', identity, role+'|'+role+'|f|f|f|f|f|0')
        for schema, allowed in [('synthetic_ncaaf',True),('synthetic_phase10e',True),('synthetic_mlb',True),('synthetic_unrelated',False)]:
            eq(role+' schema USAGE '+schema,c.query(role,"SELECT has_schema_privilege(current_user,'"+schema+"','USAGE');"),'t' if allowed else 'f')
            eq(role+' schema CREATE '+schema,c.query(role,"SELECT has_schema_privilege(current_user,'"+schema+"','CREATE');"),'f')
        for table in tables:
            canread = role in (reader,recovery) and table in ('synthetic_ncaaf.forecasts','synthetic_ncaaf.checkpoints','synthetic_phase10e.settlements')
            for privilege in ('SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'):
                allowed = canread and privilege == 'SELECT'
                eq(role+' '+privilege+' ACL '+table,c.query(role,"SELECT has_table_privilege(current_user,"+oids[table]+"::oid,'"+privilege+"');"),'t' if allowed else 'f')
            # Actual engine operations (not just ACL predicates), no-op mutations still require permission.
            commands = [('SELECT','SELECT count(*) FROM '+table),('INSERT','INSERT INTO '+table+' SELECT * FROM '+table+' WHERE false'),('UPDATE','UPDATE '+table+' SET '+('forecast_id=forecast_id' if 'settlements' in table else 'id=id' if table.endswith(('control','forecasts','default_probe','canary')) else 'generation=generation')+' WHERE false'),('DELETE','DELETE FROM '+table+' WHERE false'),('TRUNCATE','TRUNCATE '+table)]
            for op, sql in commands:
                c.query(role,sql+';',None if canread and op=='SELECT' else '42501');passed(role+' actual '+op+' '+table)
        for f in functions:
            allowed = (role==writer and ('.claim(' in f or '.publish(' in f or '.settle(' in f)) or (role==cleanup and '.cleanup_receipt(' in f)
            eq(role+' function ACL '+f,c.query(role,"SELECT has_function_privilege(current_user,'"+f+"','EXECUTE');"),'t' if allowed else 'f')
            if not allowed:
                call=f.split('(')[0]+('()' if f.endswith('()') else "(2,2,'SYNTHETIC-DENIED',1)" if '.publish(' in f else '(2,1)' if '.claim(' in f else "('SYNTHETIC-FIRST',21)")
                c.query(role,'SELECT '+call+';','42501');passed(role+' actual function denial '+f)
        for target in ('ncaaf_lab_owner', *[r for r in ROLES if r!=role], 'synthetic_lab_admin'):
            c.query(role,'SET ROLE '+target+';','42501');passed(role+' escalation denied '+target)
        c.query(role,'CREATE ROLE synthetic_escape SUPERUSER;','42501');passed(role+' role creation denied')
    c.query('admin', "DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace CROSS JOIN LATERAL aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a WHERE n.nspname IN ('synthetic_ncaaf','synthetic_phase10e') AND a.grantee=0 AND a.privilege_type='EXECUTE') THEN RAISE EXCEPTION 'PUBLIC executable'; END IF; END $$;")
    passed('PUBLIC EXECUTE defaults deny live canaries')
    # Start a long-lived *restricted* psql connection. Its output marker is bounded and no secret is logged.
    def held(label, sql):
        output=c.out/(label+'.stdout.log');error=c.out/(label+'.stderr.log')
        so=output.open('wb');se=error.open('wb')
        p=subprocess.Popen(c.command(),env=c.environment(writer,label),stdin=subprocess.PIPE,stdout=so,stderr=se,close_fds=True,creationflags=0x08000000 if os.name=='nt' else 0)
        p.stdin.write(('BEGIN;\n'+sql+"\nSELECT 'HOLD_READY';\n").encode());p.stdin.flush()
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            if 'HOLD_READY' in output.read_text(errors='replace'):return p,so,se
            if p.poll() is not None:break
            time.sleep(.05)
        if p.poll() is None:p.kill();p.wait(timeout=5)
        so.close();se.close();raise AssertionError('Held writer did not become ready; STOP')
    def finish(handle, commit=True):
        p,so,se=handle
        try:
            p.communicate(input=b'COMMIT;\n' if commit else b'ROLLBACK;\n',timeout=10)
            if p.returncode:raise AssertionError('Held session failure; STOP')
        finally:
            if p.poll() is None:p.kill();p.wait(timeout=5)
            so.close();se.close()
    # Re-fence the expired/old epoch before collision. Clock expiry forced by administrative failure injection only.
    c.query('admin',"UPDATE synthetic_ncaaf.control SET expires='epoch';")
    eq('new fencing epoch',c.query(writer,'SELECT synthetic_ncaaf.claim(2,1200);'),'3')
    before=snapshot(c)
    c.query(writer,"SELECT synthetic_ncaaf.publish(2,2,'SYNTHETIC-OLD-FENCE',9);",'40001')
    eq('stale fence has zero effects',snapshot(c),before)
    handle=held('cas-holder',"SELECT synthetic_ncaaf.publish(2,3,'SYNTHETIC-CAS-WIN',31);")
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(c.query,writer,"SELECT synthetic_ncaaf.publish(2,3,'SYNTHETIC-CAS-LOSE',41);",'40001')
            deadline=time.monotonic()+8;blocked=False
            while time.monotonic()<deadline:
                if c.query('admin',"SELECT count(*) FROM pg_stat_activity WHERE usename='ncaaf_lab_writer' AND wait_event_type='Lock';")!='0':blocked=True;break
                time.sleep(.05)
            if not blocked:raise AssertionError('No actual concurrent writer lock contention; STOP')
            finish(handle);handle=None;future.result(timeout=15)
        passed('simultaneous CAS: one commit, one blocked stale40001')
    finally:
        if handle:finish(handle,False)
    eq('CAS exactly one generation/forecast',c.query(reader,"SELECT (SELECT count(*) FROM synthetic_ncaaf.forecasts),(SELECT max(generation) FROM synthetic_ncaaf.checkpoints),(SELECT count(*) FROM synthetic_ncaaf.forecasts WHERE id='SYNTHETIC-CAS-LOSE');"),'3|3|0')
    after=snapshot(c)
    for item in before['synthetic_ncaaf.forecasts']:
        if item not in after['synthetic_ncaaf.forecasts']:raise AssertionError('Original forecast changed; STOP')
    for item in before['synthetic_ncaaf.checkpoints']:
        if item not in after['synthetic_ncaaf.checkpoints']:raise AssertionError('Original checkpoint changed; STOP')
    passed('all original immutable forecast/checkpoint rows unchanged')
    c.query(writer,"SELECT synthetic_ncaaf.publish(3,3,'SYNTHETIC-FIRST',999);",'23505')
    eq('conflicting immutable identity leaves state unchanged',snapshot(c),after)
    # Transaction-level failure is a genuine unhandled error, not an expected-denial savepoint.
    c.query(writer,"BEGIN; SELECT synthetic_ncaaf.publish(3,3,'SYNTHETIC-ERROR',5); SELECT 1/0; COMMIT;",'22012')
    eq('controlled failure before COMMIT rolls back all rows',snapshot(c),after)
    handle=held('interrupted-holder',"SELECT synthetic_ncaaf.publish(3,3,'SYNTHETIC-PARTIAL',55);")
    try:
        eq('concurrent authenticated reader sees committed generation only',c.query(reader,"SELECT count(*),max(generation) FROM synthetic_ncaaf.checkpoints;"),'3|3')
        eq('no uncommitted forecast visible',c.query(reader,"SELECT count(*) FROM synthetic_ncaaf.forecasts WHERE id='SYNTHETIC-PARTIAL';"),'0')
        handle[0].kill();handle[0].wait(timeout=5);handle[1].close();handle[2].close();handle=None
        deadline=time.monotonic()+5
        while c.query('admin',"SELECT count(*) FROM pg_stat_activity WHERE application_name='interrupted-holder';")!='0':
            if time.monotonic()>deadline:raise AssertionError('Interrupted backend did not exit; STOP')
            time.sleep(.05)
    finally:
        if handle:finish(handle,False)
    eq('interrupted disconnected publication never authoritative',snapshot(c),after)
    # Duplicate settlements exercise an explicit NEW canary contract, not authentic sport state.
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        settled=list(pool.map(lambda _:c.query(writer,"SELECT synthetic_phase10e.settle('SYNTHETIC-FIRST',21);"),range(2)))
    eq('two duplicate settlement submissions idempotent',settled,['21','21'])
    eq('one immutable settlement row',c.query(reader,'SELECT count(*) FROM synthetic_phase10e.settlements;'),'1')
    settled_state=snapshot(c)
    c.query(writer,"SELECT synthetic_phase10e.settle('SYNTHETIC-FIRST',99);",'23505');passed('conflicting settlement rejected23505')
    c.query('admin','UPDATE synthetic_phase10e.settlements SET result=99;','55000');passed('settlement update immutable55000')
    eq('settlement conflicts preserve full authority',snapshot(c),settled_state)
    c.query('admin',"UPDATE synthetic_ncaaf.control SET expires='epoch';")
    expired=snapshot(c)
    c.query(writer,"SELECT synthetic_ncaaf.publish(3,3,'SYNTHETIC-EXPIRED',1);",'40001');passed('expired lease denied')
    eq('expired lease rejection atomic',snapshot(c),expired)
    eq('expired lease takeover epoch4',c.query(writer,'SELECT synthetic_ncaaf.claim(3,1200);'),'4')
    c.query(writer,"SELECT synthetic_ncaaf.publish(3,3,'SYNTHETIC-STALE-TOKEN',1);",'40001');passed('stale owner epoch denied after takeover')
    return results
