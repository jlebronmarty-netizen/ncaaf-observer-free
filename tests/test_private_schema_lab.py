"""Offline regressions; no PostgreSQL engine is started or connected by these tests."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import private_schema_lab as lab
import synthetic_state_v1 as s


class PrivateSchemaContract(unittest.TestCase):
    def test_canonical_payloads_preserve_original_lineage_contract(self):
        payloads=lab.canonical_payloads();self.assertEqual(len(payloads),3)
        parent=None;watermark=0
        for generation,payload in enumerate(payloads,1):
            digest=s.sha(payload);doc=s.snapshot(payload,digest,generation,parent,watermark)
            self.assertEqual(doc['format'],s.FORMAT);self.assertTrue(doc['synthetic'])
            self.assertEqual(s.encode(doc),payload);self.assertEqual(doc['fence'],1)
            parent=digest;watermark=doc['watermark']

    def test_shadow_roles_are_explicitly_unprivileged(self):
        for role in lab.EXTRA_ROLES:
            self.assertIn('CREATE ROLE '+role+' NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS',lab.SETUP)
            self.assertIn(role,lab.extra_role_sql())

    def test_private_ledger_has_hash_lineage_and_immutable_guards(self):
        for value in ['digest=encode(sha256(payload)', 'FORCE ROW LEVEL SECURITY', 'objects_immutable', 'journal_immutable', "ERRCODE='40001'", "ERRCODE='23514'", "'NCAAF_PHASE8B_SYNTHETIC_V1'"]:
            self.assertIn(value,lab.SETUP)
        self.assertNotIn('GRANT ALL',lab.SETUP)

    def test_api_roles_receive_no_private_grants(self):
        grants=[line for line in lab.SETUP.splitlines() if line.startswith('GRANT')]
        for line in grants:
            self.assertFalse(any(role in line for role in lab.API_ROLES))
            self.assertNotIn('TO PUBLIC',line)

    def test_expected_public_risk_is_rollback_probe_not_a_hosted_fix(self):
        text=(ROOT/'scripts/private_schema_lab.py').read_text()
        self.assertIn("Expected PUBLIC capability risk",text)
        self.assertIn('GRANT USAGE ON SCHEMA synthetic_legacy_mlb TO PUBLIC;',text)
        self.assertIn("ROLLBACK;\")",text)
        self.assertNotIn('sync_mlb_pitcher_win_forward_',text)

    def test_only_new_synthetic_namespaces_and_qualified_definers(self):
        self.assertIn('SET search_path=pg_catalog,pg_temp',lab.SETUP)
        self.assertIn('synthetic_private_ncaaf.control',lab.SETUP)
        self.assertIn('synthetic_legacy_mlb.canary',lab.SETUP)
        self.assertNotIn('CREATE EXTENSION',lab.SETUP)
        self.assertNotIn('ALTER FUNCTION synthetic_ncaaf.publish',lab.SETUP)


if __name__=='__main__':unittest.main()
