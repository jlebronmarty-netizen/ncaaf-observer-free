"""Exact staged synthetic fixture runner: localhost only, fresh authenticated connections.
No cluster provisioning, remote DSN, service installation or hosted-provider API.
"""
from pathlib import Path
import os
import json
import re
import secrets
import subprocess

ROLES = ('ncaaf_lab_writer','ncaaf_lab_reader','ncaaf_lab_recovery','ncaaf_lab_cleanup')
MARKER = 'NCAAF_SYNTHETIC_PG_LAB_V1'


def stages(text):
    result=[];role=None;lines=[]
    for line in text.splitlines():
        if line.startswith('-- LAB_SESSION: '):
            if role is not None and any(x.strip() and not x.lstrip().startswith('--') for x in lines):result.append((role,'\n'.join(lines)))
            role=line.split(': ',1)[1];lines=[]
            if role not in ('admin',*ROLES):raise ValueError('Unapproved identity')
        elif role is not None and not line.startswith('\\'):lines.append(line)
    if role is not None and any(x.strip() and not x.lstrip().startswith('--') for x in lines):result.append((role,'\n'.join(lines)))
    if not result or result[0][0]!='admin' or not text.rstrip().endswith('-- LAB_COMPLETE'):raise ValueError('Incomplete staged fixture')
    for role,sql in result:
        if role!='admin' and re.search(r'^\s*(?:SET|RESET)\s+ROLE\b',sql,re.M|re.I):raise ValueError('Restricted session must authenticate directly')
    return result


def run_fixture(bin_dir,port,admin_passfile,private_root,artifact_dir,fixture):
    root=Path(private_root).resolve();binary=Path(bin_dir).resolve();out=Path(artifact_dir).resolve();admin=Path(admin_passfile).resolve()
    if (root/'.ncaaf-pg-lab').read_text()!=MARKER or binary!=root/'pgsql/bin' or not admin.is_relative_to(root) or type(port)is not int or not 1024<=port<=65535:raise ValueError('Unowned local fixture runtime')
    text=Path(fixture).read_text();plan=stages(text);records=[];passwords={};passfiles={'admin':admin};known_secrets=[]
    def invoke(label,role,sql,secret=False):
        username='synthetic_lab_admin' if role=='admin' else role
        env={k:v for k,v in os.environ.items() if not k.startswith(('PG','POSTGRES'))}
        env.update(PGHOST='127.0.0.1',PGPORT=str(port),PGUSER=username,PGDATABASE='synthetic_permission_lab',PGPASSFILE=str(passfiles[role]),PGCONNECT_TIMEOUT='5',PGAPPNAME='NCAAF_SYNTHETIC_ROLE_LAB')
        command=[str(binary/'psql.exe'),'-X','-w','-A','-t','-v','ON_ERROR_STOP=1']
        p=subprocess.run(command,input=sql.encode(),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=0x08000000 if os.name=='nt' else 0,close_fds=True,timeout=30)
        stdout=p.stdout.decode(errors='replace');stderr=p.stderr.decode(errors='replace')
        for key in known_secrets:stdout=stdout.replace(key,'[REDACTED]');stderr=stderr.replace(key,'[REDACTED]')
        (out/(label+'.stdout.log')).write_bytes(stdout.encode());(out/(label+'.stderr.log')).write_bytes(stderr.encode())
        record={'label':label,'identity':username,'exit':p.returncode,'timeout_seconds':30,'authenticated':True,'credential_file_scope':'admin-only' if role=='admin' else 'one-restricted-identity-only','sql_omitted_for_secret_setup':secret,'denial_passes':re.findall(r'EXPECTED_DENIAL_PASS: (.*?) \[([^\]]+)\]',stderr)}
        records.append(record);(out/'ROLE_SESSION_RESULTS.json').write_bytes(json.dumps(records,indent=2).encode())
        if p.returncode:raise RuntimeError('SQL assertion/auth failure in '+label+'; STOP')
        return stdout,stderr
    try:
        for index,(role,sql) in enumerate(plan):
            if index==1:
                # No password appears in argv, Git, logs, environment values or generated SQL files.
                commands=[]
                for name in ROLES:
                    value=secrets.token_urlsafe(48);known_secrets.append(value);passwords[name]=value
                    path=root/(name+'.pgpass');path.write_bytes(('127.0.0.1:'+str(port)+':synthetic_permission_lab:'+name+':'+value+'\n').encode());passfiles[name]=path
                    commands.append("ALTER ROLE "+name+" LOGIN PASSWORD '"+value+"';")
                invoke('role-credentials-setup','admin','\n'.join(commands),secret=True)
            if role!='admin':
                identity_sql="SELECT session_user,current_user,r.rolsuper,r.rolcreatedb,r.rolcreaterole,r.rolbypassrls,r.rolinherit,(SELECT count(*) FROM pg_auth_members WHERE member=r.oid),current_database(),inet_server_addr(),inet_server_port() FROM pg_roles r WHERE r.rolname=current_user;"
                value,_=invoke('identity-'+str(index),role,identity_sql)
                expected='|'.join([role,role,'f','f','f','f','f','0','synthetic_permission_lab','127.0.0.1',str(port)])
                if value.strip()!=expected:raise RuntimeError('Unexpected effective identity or role membership; STOP')
                records[-1]['identity_verified']=True;(out/'ROLE_SESSION_RESULTS.json').write_bytes(json.dumps(records,indent=2).encode())
            stdout,stderr=invoke('stage-'+str(index),role,'BEGIN;\n'+sql+'\nCOMMIT;')
        denials=[entry for record in records for entry in record['denial_passes']]
        expected=len(re.findall(r'SELECT synthetic_checks\.expect_state\(',text))
        if len(denials)!=expected or 'SYNTHETIC_POSTGRES_PERMISSION_LAB_PASS' not in stdout:raise RuntimeError('Incomplete engine coverage; STOP')
        return {'ENGINE_VERIFIED':True,'denials_passed':len(denials),'expected_denials':expected,'failures':0,'not_reached':0,'restricted_identities_verified':list(ROLES),'stages':len(plan),'source_fixture_sha256_required':'Recorded by owning launcher'}
    finally:
        for role,path in passfiles.items():
            if role!='admin' and path.exists():path.unlink()
        passwords.clear();known_secrets.clear()
