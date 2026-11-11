"""Audit the workspace migration and independently replay the synthetic fixture."""
from collections import Counter
from itertools import combinations
from fractions import Fraction
import json,sqlite3
from . import platform as p

def main():
    out=p.ROOT/'outputs/multi-game'
    before=json.loads((out/'before.json').read_text())
    preserved={}
    for path,v in before.items():
        if p.ROOT/path!=p.DATABASE:
            assert p.hash_file(p.ROOT/path)==v['sha256']
    with p.connect(p.DATABASE) as db:
        db.execute('ATTACH DATABASE ? AS old',((out/'pre-migration.sqlite').as_uri()+'?mode=ro',))
        for name,sql in db.execute("SELECT name,sql FROM old.sqlite_master WHERE type IN ('table','view','index','trigger') AND sql IS NOT NULL"):
            assert db.execute('SELECT sql FROM main.sqlite_master WHERE name=?',(name,)).fetchone()[0]==sql
        for name,n in before[str(p.DATABASE.relative_to(p.ROOT))]['tables'].items():
            assert db.execute(f'SELECT count(*) FROM main."{name}"').fetchone()[0]==n
            for left,right in (('old','main'),('main','old')):
                assert db.execute(f'SELECT * FROM {left}."{name}" EXCEPT SELECT * FROM {right}."{name}"').fetchone() is None
            preserved[name]=n
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        fixture={}
        valid=list(combinations([c for s in (2,3) for c in combinations(range(1,7),s)],2))
        for objective in ('any-payout','net-profit'):
            x,spec,table=p.context(db,'fixture-'+objective)
            assert x['cursor']==x['stop']=='595'
            expected={}
            for cards in valid:
                law=Counter()
                for draw in combinations(range(1,7),3):
                    gross=sum(table['payouts'][str(len(c))][len(set(c)&set(draw))] for c in cards)
                    law[gross]+=1
                threshold=0 if objective=='any-payout' else 2
                expected[p.dump(cards)]=(sum(v for q,v in law.items() if q>threshold),dict(law))
            rows=db.execute('''SELECT q.cards,e.* FROM mk_evaluation e JOIN mk_job j ON j.id=e.job
                               JOIN mk_pattern q ON q.id=j.pattern WHERE e.project=?''',(x['id'],)).fetchall()
            assert len(rows)==len(expected)==595
            for row in rows:
                wins,law=expected.pop(row['cards'])
                assert int(row['wins'])==wins and int(row['total'])==20
                assert row['probability']==str(Fraction(wins,20))
                assert {int(k):v for k,v in json.loads(row['law'])['gross_counts'].items()}==law
            assert not expected
            fixture[objective]=dict(exhaustively_verified=len(rows),leader=p.leaders(db,'fixture-'+objective,1)[0])
            with db:
                db.execute("""INSERT OR IGNORE INTO mk_certificate(project,rule_sha,paytable_sha,scope,assumptions,evidence)
                               VALUES(?,?,?,?,?,?)""",
                           (x['id'],x['rule_sha'],x['table_sha'],'all 595 unordered fixture layouts',
                            'Six physical numbers, fixed three-number draw, two distinct 2–3 spot cards, additive synthetic awards.',
                            p.dump(dict(project='fixture-'+objective,checked=len(rows),
                                        replay='python3 -m multi_keno.audit',replay_sha256=p.hash_file(__import__('pathlib').Path(__file__))))))
        a=p.leaders(db,'scenario1-any-payout',1)[0]
        assert int(a['total'])-int(a['wins'])==4**20
        pattern=db.execute("SELECT id FROM mk_pattern WHERE cards='[[1,2],[3,4]]'").fetchone()[0]
        variant=[]
        for name in ('fixture-any-payout','fixture-table-v2-any-payout'):
            x,_,_=p.context(db,name)
            row=db.execute('''SELECT e.wins,e.total,e.paytable_sha,e.probability FROM mk_evaluation e
                JOIN mk_job j ON j.id=e.job WHERE j.pattern=? AND e.project=?''',(pattern,x['id'])).fetchone()
            variant.append(dict(project=name,pattern=pattern,**dict(row)))
        assert variant[0]['wins']=='8' and variant[1]['wins']=='0'
        assert variant[0]['paytable_sha']!=variant[1]['paytable_sha']
        with sqlite3.connect(out/'post-migration.sqlite') as backup:
            db.backup(backup)
            assert backup.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    result=dict(integrity='ok',foreign_key_errors=0,backup_integrity='ok',
        historical_tables_exactly_equal=preserved,source_files_unchanged=True,
        legacy_record_a=dict(zero=4**20,**a),fixture=fixture,paytable_reevaluation=variant)
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
