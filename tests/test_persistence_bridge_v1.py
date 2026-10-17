from pathlib import Path
import sys
import unittest
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import synthetic_state_v1 as s
import readonly_projection_v1 as a
import persistence_bridge_v1 as b


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=s.workspace();self.root=self.temp.__enter__();self.addCleanup(self.temp.__exit__,None,None,None)
        self.tick=0.0;self.key=bytes(range(32));self.store=b.Store(self.root,self.key,lambda:self.tick)
        self.lease=self.store.claim('writer','W',ttl=1200)
        self.host=s.HostedSimulator(self.root);self.epoch=self.host.claim('source',0,ttl=10000)
        self.request={'version':a.VERSION,'offset':0,'limit':50,'max_age':1000}

    def payload(self,number=1,final=False):
        g=self.host.website_view()['generation'];now=number*100+(60 if final else 20)
        self.host.commit('source',self.epoch,g,now,s.synthetic_batch(number,final))
        h=s.ReadOnlyTransport(self.host).head();return (self.host.objects/(h['digest']+'.json')).read_bytes()

    def publish(self,payload,expected=0,**kw):
        digest=self.store.put('writer',payload)
        return self.store.publish('writer','W',self.lease,expected,digest,**kw)

    def seed(self): return self.publish(self.payload())

    def test_projection_identity_and_settlement_parity(self):
        floor=self.seed();self.publish(self.payload(final=True),1)
        actual,head=b.reconstruct(self.store,'reader',floor,self.request,now=160)
        expected=a.Reader(self.root).project(self.request,floor={'generation':1,'digest':floor['body']['digest']},now=160)
        self.assertEqual(actual,expected);self.assertEqual(head,self.store.head('reader'))

    def test_durable_restart_and_recovery_identity(self):
        floor=self.seed();self.publish(self.payload(2),1)
        restarted=b.Store(self.root,self.key,lambda:self.tick)
        first=b.reconstruct(self.store,'reader',floor,self.request,now=220)
        self.assertEqual(first,b.reconstruct(restarted,'recovery',floor,self.request,now=220))

    def test_roles_deny_mutations_and_orphan_enumeration(self):
        payload=self.payload();digest=self.store.put('writer',payload)
        for role in ['reader','recovery','anonymous']:
            with self.assertRaises(PermissionError): self.store.put(role,payload)
            with self.assertRaises(PermissionError): self.store.claim(role,'bad')
            with self.assertRaises(PermissionError): self.store.publish(role,'W',self.lease,0,digest)
        with self.assertRaises(PermissionError): self.store.fetch('reader',digest)

    def test_interrupted_publication_clean_retry(self):
        payload=self.payload()
        with self.assertRaises(OSError): self.publish(payload,fault=True)
        with self.assertRaises(ValueError): self.store.head('reader')
        receipt=self.publish(payload);self.assertEqual(receipt,self.publish(payload))
        self.assertEqual(s.decode(b.reconstruct(self.store,'reader',receipt,self.request,now=120)[0])['generation'],1)

    def test_writer_fence_expiry_and_takeover(self):
        payload=self.payload();digest=self.store.put('writer',payload);self.tick=1200
        with self.assertRaises(ValueError): self.store.publish('writer','W',self.lease,0,digest)
        with self.assertRaises(ValueError): self.store.claim('writer','new')
        self.lease=self.store.claim('writer','new',reviewed=True)
        with self.assertRaises(ValueError): self.store.publish('writer','W',self.lease-1,0,digest)
        self.store.publish('writer','new',self.lease,0,digest)

    def test_generation_cas_and_simultaneous_publication(self):
        floor=self.seed();payload=self.payload(2);digest=self.store.put('writer',payload)
        def submit(_):return self.store.publish('writer','W',self.lease,1,digest)
        with ThreadPoolExecutor(max_workers=2) as pool: answers=list(pool.map(submit,range(2)))
        self.assertEqual(answers[0],answers[1])
        with self.assertRaises(ValueError): self.store.publish('writer','W',self.lease,0,digest)
        self.assertEqual(s.decode(b.reconstruct(self.store,'recovery',floor,self.request,now=220)[0])['total'],4)

    def test_tampered_object_and_clean_recovery(self):
        floor=self.seed();digest=floor['body']['digest']
        with closing(s.connect(self.store.path)) as db,db:
            original=db.execute('SELECT payload FROM bridge_objects').fetchone()[0]
            db.execute('DROP TRIGGER bridge_objects_immutable');db.execute("UPDATE bridge_objects SET payload=?",(b'corrupt',))
        with self.assertRaises(ValueError): b.reconstruct(self.store,'reader',floor,self.request,now=120)
        with closing(s.connect(self.store.path)) as db,db:db.execute('UPDATE bridge_objects SET payload=? WHERE digest=?',(original,digest))
        b.reconstruct(self.store,'recovery',floor,self.request,now=120)

    def test_missing_generation_and_object(self):
        floor=self.seed();self.publish(self.payload(2),1)
        with closing(s.connect(self.store.path)) as db,db:db.execute('DELETE FROM bridge_journal WHERE generation=1')
        with self.assertRaises(ValueError): b.reconstruct(self.store,'reader',floor,self.request,now=220)

    def test_checkpoint_rollback_and_wrong_key(self):
        old=self.seed();latest=self.publish(self.payload(2),1)
        wrong=b.Store(self.root,bytes(reversed(range(32))),lambda:self.tick)
        with self.assertRaises(ValueError): wrong.head('reader')
        with closing(s.connect(self.store.path)) as db,db:
            db.execute('DELETE FROM bridge_journal WHERE generation=2');db.execute('UPDATE bridge_meta SET generation=1,digest=?',(old['body']['digest'],))
        with self.assertRaises(ValueError): b.reconstruct(self.store,'reader',latest,self.request,now=220)

    def test_receipt_tampering_and_foreign_namespace(self):
        floor=self.seed()
        for field,value in [('digest','a'*64),('version','NBA'),('synthetic',False),('generation',2)]:
            bad={'body':{**floor['body'],field:value},'tag':floor['tag']}
            with self.assertRaises(ValueError): b.reconstruct(self.store,'reader',bad,self.request,now=120)

    def test_semantic_corruption_never_published(self):
        raw=s.decode(self.payload());raw['changes'][0]['body']['synthetic']=False
        payload=s.encode(raw)
        with self.assertRaises(ValueError): self.publish(payload)
        with self.assertRaises(ValueError): self.store.head('reader')

    def test_pilot_request_transfer_footprint_limits(self):
        payload=self.payload()
        with mock.patch.object(b,'REQUESTS',1):
            with self.assertRaises(ValueError): self.store.put('writer',payload)
        with mock.patch.object(b,'TRANSFER',1):
            with self.assertRaises(ValueError): self.store.put('writer',payload)
        with mock.patch.object(b,'FOOTPRINT',1):
            with self.assertRaises(ValueError): self.store.put('writer',payload)
        self.publish(payload)

    def test_runtime_and_clock_rollback_fail_closed_after_restart(self):
        self.seed();self.tick=1201
        with self.assertRaises(ValueError): self.store.head('reader')
        self.tick=-1;restarted=b.Store(self.root,self.key,lambda:self.tick)
        with self.assertRaises(ValueError): restarted.head('reader')

    def test_failed_identity_attempts_count_and_no_workspace_leaks(self):
        self.seed();before=set(self.root.parent.glob('ncaaf-phase8b-synthetic-*'))
        for _ in range(3):
            with self.assertRaises(PermissionError): self.store.head('anonymous')
        with closing(s.connect(self.store.path,readonly=True)) as db:self.assertGreaterEqual(db.execute('SELECT requests FROM bridge_meta').fetchone()[0],6)
        floor=self.store.head('reader');b.reconstruct(self.store,'recovery',floor,self.request,now=120)
        self.assertEqual(before,set(self.root.parent.glob('ncaaf-phase8b-synthetic-*')))



    def test_committed_object_missing_rejects_recovery(self):
        floor=self.seed()
        with closing(s.connect(self.store.path)) as db,db:db.execute('DELETE FROM bridge_objects')
        with self.assertRaises(ValueError):b.reconstruct(self.store,'recovery',floor,self.request,now=120)

    def test_budgets_persist_across_store_restart(self):
        floor=self.seed();self.store.fetch('reader',floor['body']['digest'])
        with closing(s.connect(self.store.path,readonly=True)) as db:
            requests,transfer=db.execute('SELECT requests,transfer FROM bridge_meta').fetchone()
        reopened=b.Store(self.root,self.key,lambda:self.tick)
        with mock.patch.object(b,'REQUESTS',requests):
            with self.assertRaises(ValueError):reopened.head('reader')
        with mock.patch.object(b,'TRANSFER',transfer):
            with self.assertRaises(ValueError):reopened.fetch('reader',floor['body']['digest'])

    def test_signed_receipt_replay_cannot_replace_new_floor(self):
        old=self.seed();latest=self.publish(self.payload(2),1)
        with mock.patch.object(self.store,'head',return_value=old):
            with self.assertRaises(ValueError):b.reconstruct(self.store,'reader',latest,self.request,now=220)

    def test_exact_request_and_transfer_boundaries(self):
        floor=self.seed();digest=floor['body']['digest']
        with closing(s.connect(self.store.path)) as db,db:db.execute('UPDATE bridge_meta SET requests=999')
        self.store.head('reader')
        with self.assertRaises(ValueError):self.store.head('reader')
        with closing(s.connect(self.store.path)) as db,db:
            size=db.execute('SELECT length(payload) FROM bridge_objects').fetchone()[0]
            db.execute('UPDATE bridge_meta SET requests=0,transfer=?',(b.TRANSFER-size,))
        self.store.fetch('reader',digest)
        with self.assertRaises(ValueError):self.store.fetch('reader',digest)


    def test_corrupt_metadata_never_publishes(self):
        payload=self.payload();digest=self.store.put('writer',payload)
        with closing(s.connect(self.store.path)) as db,db:db.execute('UPDATE bridge_meta SET generation=-1')
        with self.assertRaises(ValueError):self.store.publish('writer','W',self.lease,-1,digest)
        with closing(s.connect(self.store.path)) as db,db:db.execute('UPDATE bridge_meta SET generation=0,requests=-1')
        with self.assertRaises(ValueError):self.store.head('reader')


if __name__=='__main__':unittest.main()
