from itertools import combinations
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import TestCase
import sqlite3
from . import engine
from . import platform as p

class PlatformTests(TestCase):
    def setUp(self):
        temp=TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db=p.connect(Path(temp.name)/'fixture.sqlite')
        self.addCleanup(self.db.close)
        self.db.execute('CREATE TABLE historical(id INTEGER PRIMARY KEY, evidence TEXT)')
        self.db.execute("INSERT INTO historical VALUES(1,'preserve')")
        self.db.commit()
        p.migrate(self.db)
        self.spec,self.table=p.fixture()
        _,self.pid=p.register(self.db,self.spec,self.table)
        p.project(self.db,'pay',self.pid,'any-payout')

    def test_migration_is_idempotent_and_preserves_old_tables(self):
        p.migrate(self.db)
        self.assertEqual(tuple(self.db.execute('SELECT * FROM historical').fetchone()),(1,'preserve'))
        self.assertEqual(self.db.execute('SELECT count(*) FROM mk_migration').fetchone()[0],2)
        self.assertEqual(self.db.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def test_immutable_rule_and_paytable_versions(self):
        with self.assertRaises(ValueError):
            p.register(self.db,dict(self.spec,draw=2),self.table)
        with self.assertRaises(ValueError):
            p.register(self.db,self.spec,dict(self.table,payouts={'2':[0,0,7],'3':[0,0,1,5]}))
        with self.assertRaises(ValueError):
            p.register(self.db,dict(self.spec,mechanics=dict(p.MECHANICS,bonus='unknown')),self.table)

    def test_deferral_and_enumeration_resume(self):
        result=p.work(self.db,'pay',2,1,True)
        self.assertEqual((result['generated'],result['deferred']),(1,1))
        self.assertEqual(p.context(self.db,'pay')[0]['cursor'],'1')
        self.assertEqual(p.work(self.db,'pay',1,100,True)['exact'],1)
        self.assertEqual(p.context(self.db,'pay')[0]['cursor'],'1')
        p.work(self.db,'pay',2,100,True)
        self.assertEqual(p.context(self.db,'pay')[0]['cursor'],'2')

    def test_pattern_edit_preserves_parent_and_rejects_duplicate(self):
        x,spec,_=p.context(self.db,'pay')
        with self.db:parent=p.store_pattern(self.db,x,spec,((1,2),(3,4)))
        with self.assertRaises(ValueError):p.edit(self.db,'pay',parent,{'2':[1,2]})
        child=p.edit(self.db,'pay',parent,{'2':[2,4,5]})
        self.assertNotEqual(parent,child)
        self.assertEqual(self.db.execute('SELECT cards FROM mk_pattern WHERE id=?',(parent,)).fetchone()[0],'[[1,2],[3,4]]')
        self.assertEqual(self.db.execute('SELECT count(*) FROM mk_version WHERE parent=? AND child=?',(parent,child)).fetchone()[0],1)

    def test_same_pattern_different_paytable_and_objective(self):
        x,spec,_=p.context(self.db,'pay')
        cards=((1,2),(3,4))
        with self.db:a=p.store_pattern(self.db,x,spec,cards)
        p.work(self.db,'pay',1,100)
        other=dict(self.table,version='v2',payouts={'2':[0,0,0],'3':[0,0,1,5]})
        _,id=p.register(self.db,self.spec,other)
        p.project(self.db,'other',id,'any-payout')
        p.project(self.db,'profit',self.pid,'net-profit')
        with self.db:
            for name in ('other','profit'):
                y,s,_=p.context(self.db,name)
                self.assertEqual(p.store_pattern(self.db,y,s,cards),a)
        p.work(self.db,'other',1,100)
        p.work(self.db,'profit',1,100)
        self.assertEqual(p.leaders(self.db,'pay',1)[0]['wins'],'8')
        self.assertEqual(p.leaders(self.db,'other',1)[0]['wins'],'0')
        self.assertEqual(p.leaders(self.db,'profit',1)[0]['wins'],'8')
        self.assertEqual(self.db.execute('SELECT count(DISTINCT paytable_sha) FROM mk_evaluation').fetchone()[0],2)

    def test_exact_enumerator_matches_literal_legal_space(self):
        cards=[c for s in self.spec['sizes'] for c in combinations(range(1,7),s)]
        actual={engine.candidate(self.spec,i) for i in range(engine.scope(self.spec))}
        self.assertEqual(actual,set(combinations(cards,2)))
        from itertools import combinations_with_replacement
        repeated=dict(self.spec,duplicates=True)
        self.assertEqual({engine.candidate(repeated,i) for i in range(engine.scope(repeated))},
                         set(combinations_with_replacement(cards,2)))

    def test_relabeling_and_zero_hit_payout(self):
        table=dict(self.table,payouts={'2':[1,0,3],'3':[0,0,1,5]})
        a=((1,2),(2,3,4))
        b=((4,6),(1,5,6))
        self.assertEqual(engine.identity(self.spec,a),engine.identity(self.spec,b))
        self.assertEqual(engine.evaluate(self.spec,table,a,1000),engine.evaluate(self.spec,table,b,1000))

    def test_record_a_exact_adapter(self):
        spec,table=p.legacy_data()
        cards=tuple(tuple(range(i,i+4)) for i in range(1,81,4))
        wins,law,_=p.evaluate(spec,table,cards,'any-payout',200000,True)
        self.assertEqual(law['zero_polynomial'][20],4**20)
        self.assertEqual(wins,3535316142212174320-4**20)
