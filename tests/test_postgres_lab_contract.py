"""Static fixture assertions ONLY. Never execute PostgreSQL or claim database PASS."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
SQL=ROOT/'templates/phase10b-permission-lab.sql.disabled'


class PostgresLabContract(unittest.TestCase):
    def test_disposable_transaction_guard(self):
        text=SQL.read_text();self.assertIn("current_database() <> 'synthetic_permission_lab'",text)
        self.assertIn('Refuse existing roles',text);self.assertIn('\\set ON_ERROR_STOP on',text)
        self.assertTrue(text.rstrip().endswith('ROLLBACK;'))

    def test_no_remote_connection_or_credential_commands(self):
        text=SQL.read_text()
        for pattern in [r'\\connect',r'CREATE\s+EXTENSION',r'CREATE\s+SERVER',r'COPY\s+.*PROGRAM',r'PASSWORD',r'https?://',r'supabase\.co']:
            self.assertIsNone(re.search(pattern,text,re.I),pattern)
        self.assertNotIn('sync_mlb_pitcher_win_forward_',text)

    def test_role_and_default_privilege_matrix(self):
        text=SQL.read_text()
        for role in ['owner','writer','reader','recovery','cleanup']:
            self.assertIn('CREATE ROLE ncaaf_lab_'+role+' NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;',text)
        self.assertIn('ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;',text)
        self.assertNotIn('ALTER DEFAULT PRIVILEGES IN SCHEMA synthetic_ncaaf REVOKE EXECUTE',text)
        self.assertIn('REVOKE EXECUTE ON FUNCTION synthetic_mlb.bump_canary() FROM PUBLIC;',text)

    def test_negative_controls_and_recovery_are_present_not_executed(self):
        text=SQL.read_text()
        for label in ['stale generation','stale fence','immutable ID duplicate','writer raw SELECT','writer raw INSERT','writer raw UPDATE','writer raw DELETE','reader MLB function','schema CREATE','role escalation','new privileged role','checkpoint immutable','expired prior epoch','recovery publication']:
            self.assertIn("'"+label+"'",text)
        self.assertIn('SAVEPOINT synthetic_interrupted;',text)
        self.assertIn('ROLLBACK TO SAVEPOINT synthetic_interrupted;',text)
        self.assertIn('RLS exclusion failed',text)
        self.assertIn('FORCE ROW LEVEL SECURITY',text)
        self.assertIn('SET search_path=pg_catalog,pg_temp',text)
        self.assertNotIn('SECURITY DEFINER SET search_path=public',text)

    def test_only_approved_fixture_objects(self):
        text=SQL.read_text()
        created=re.findall(r'CREATE (?:TABLE|FUNCTION|SCHEMA)\s+([a-z_][a-z_0-9.]*)',text,re.I)
        self.assertTrue(created)
        self.assertTrue(all(x.startswith(('synthetic_mlb','synthetic_ncaaf','synthetic_checks')) for x in created))
        self.assertGreaterEqual(text.count('synthetic_checks.expect_state('),30)


if __name__=='__main__':unittest.main()
