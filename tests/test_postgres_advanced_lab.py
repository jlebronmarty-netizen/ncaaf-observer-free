"""Offline helper/security regressions. These tests never start or connect PostgreSQL."""
from pathlib import Path
import hashlib
import importlib.util
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('advanced_lab', ROOT/'scripts/postgres_advanced_lab.py')
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


class AdvancedLabHelpers(unittest.TestCase):
    def test_valid_backup_requires_exact_trusted_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'synthetic.dump';p.write_bytes(b'SYNTHETIC_CANARY')
            self.assertEqual(lab.verify_backup(p,hashlib.sha256(p.read_bytes()).hexdigest()),p)

    def test_missing_material_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):lab.verify_backup(Path(directory)/'missing','0'*64)

    def test_tampered_material_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'synthetic.dump';p.write_bytes(b'ORIGINAL_SYNTHETIC')
            digest=hashlib.sha256(p.read_bytes()).hexdigest();p.write_bytes(b'TAMPERED_SYNTHETIC')
            with self.assertRaises(ValueError):lab.verify_backup(p,digest)

    def test_empty_and_oversized_material_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'synthetic.dump'
            for content in (b'',b'abc'):
                p.write_bytes(content)
                with self.assertRaises(ValueError):lab.verify_backup(p,hashlib.sha256(content).hexdigest(),maximum=2)

    def test_invalid_trusted_hash_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'synthetic.dump';p.write_bytes(b'synthetic')
            for digest in ('', 'x'*64, '0'*63, 'A'*64):
                with self.assertRaises(ValueError):lab.verify_backup(p,digest)

    def test_local_identity_and_authentication_contract(self):
        text=(ROOT/'scripts/postgres_advanced_lab.py').read_text()
        for required in ["PGHOST='127.0.0.1'", "'synthetic_permission_lab'", "PGPASSFILE=str(self.files[role])", "session_user,current_user", "rolbypassrls,rolinherit", "pg_auth_members", "timeout=20"]:
            self.assertIn(required,text)
        self.assertNotIn('PGPASSWORD=',text)
        self.assertEqual(len(lab.ROLES),4)

    def test_owned_runtime_rejects_invalid_root_before_connection(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'.ncaaf-pg-lab').write_text('NOT_OWNED')
            with self.assertRaises(ValueError):lab.Client(root/'pgsql/bin',54321,root,root/'admin',root)

    def test_runtime_port_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'.ncaaf-pg-lab').write_text(lab.MARKER)
            for port in (True,0,1023,65536,'54321'):
                with self.assertRaises(ValueError):lab.Client(root/'pgsql/bin',port,root,root/'admin',root)

    def test_only_separate_canary_settlement_contract(self):
        self.assertIn('CREATE TABLE synthetic_phase10e.settlements',lab.SETUP)
        self.assertIn("CHECK(marker='NCAAF_SYNTHETIC')",lab.SETUP)
        self.assertIn('ON CONFLICT DO NOTHING',lab.SETUP)
        self.assertIn("ERRCODE='23505'",lab.SETUP)
        self.assertIn('FORCE ROW LEVEL SECURITY',lab.SETUP)
        self.assertIn('SET search_path=pg_catalog,pg_temp',lab.SETUP)
        self.assertNotIn('ALTER FUNCTION synthetic_ncaaf.publish',lab.SETUP)


if __name__=='__main__':unittest.main()
