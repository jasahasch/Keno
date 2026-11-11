"""Additive, game-scoped registry, research queue and CLI."""
import argparse
from fractions import Fraction
import hashlib
import json
from math import comb
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

from . import engine

ROOT=Path(__file__).resolve().parents[1]
LEGACY=ROOT/'outputs/continuation-correction'
DATABASE=LEGACY/'continuity.sqlite'
MECHANICS=dict(draw='uniform-without-replacement',award='additive-hit-count',bonus=None,multiplier=None)
SCHEMA="""
CREATE TABLE IF NOT EXISTS mk_migration(version INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS mk_rule(id INTEGER PRIMARY KEY, game TEXT NOT NULL, version TEXT NOT NULL,
 body TEXT NOT NULL, sha TEXT NOT NULL, UNIQUE(game,version));
CREATE TABLE IF NOT EXISTS mk_paytable(id INTEGER PRIMARY KEY, rule INTEGER NOT NULL REFERENCES mk_rule,
 name TEXT NOT NULL, version TEXT NOT NULL, body TEXT NOT NULL, sha TEXT NOT NULL, UNIQUE(rule,name,version));
CREATE TABLE IF NOT EXISTS mk_project(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL,
 paytable INTEGER NOT NULL REFERENCES mk_paytable, objective TEXT NOT NULL,
 cursor TEXT NOT NULL, stop TEXT NOT NULL, rejected INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS mk_pattern(id INTEGER PRIMARY KEY, rule INTEGER NOT NULL REFERENCES mk_rule,
 parent INTEGER REFERENCES mk_pattern, cards TEXT NOT NULL, equivalence TEXT NOT NULL, changes TEXT,
 UNIQUE(rule,cards));
CREATE INDEX IF NOT EXISTS mk_equivalence ON mk_pattern(rule,equivalence);
CREATE TABLE IF NOT EXISTS mk_version(child INTEGER REFERENCES mk_pattern,parent INTEGER REFERENCES mk_pattern,
 changes TEXT NOT NULL,PRIMARY KEY(child,parent));
CREATE TABLE IF NOT EXISTS mk_run(id INTEGER PRIMARY KEY,project INTEGER NOT NULL REFERENCES mk_project,
 budget INTEGER NOT NULL, engine_sha TEXT NOT NULL, operations INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS mk_job(id INTEGER PRIMARY KEY,project INTEGER NOT NULL REFERENCES mk_project,
 pattern INTEGER NOT NULL REFERENCES mk_pattern, state TEXT NOT NULL, last_budget INTEGER, reason TEXT,
 UNIQUE(project,pattern));
CREATE INDEX IF NOT EXISTS mk_queue ON mk_job(project,state,id);
CREATE TABLE IF NOT EXISTS mk_evaluation(id INTEGER PRIMARY KEY,job INTEGER UNIQUE NOT NULL REFERENCES mk_job,
 project INTEGER NOT NULL REFERENCES mk_project, run INTEGER REFERENCES mk_run,
 wins TEXT NOT NULL, total TEXT NOT NULL, probability TEXT NOT NULL, law TEXT NOT NULL,
 method TEXT NOT NULL, rule_sha TEXT NOT NULL, paytable_sha TEXT NOT NULL, evaluator_sha TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS mk_certificate(id INTEGER PRIMARY KEY,project INTEGER NOT NULL REFERENCES mk_project,
 rule_sha TEXT NOT NULL,paytable_sha TEXT NOT NULL,scope TEXT NOT NULL,assumptions TEXT NOT NULL,
 evidence TEXT NOT NULL, UNIQUE(project,scope));
CREATE TABLE IF NOT EXISTS mk_legacy(project INTEGER PRIMARY KEY REFERENCES mk_project,
 source TEXT NOT NULL, source_table_sha TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS mk_evaluation_rank ON mk_evaluation(project,length(wins),wins);
"""

def dump(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'))

def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def evaluator_sha(method):
    paths=[Path(__file__),Path(engine.__file__)]
    if method=='legacy-zero':
        paths.extend([ROOT/'unrestricted_resolution/zero.py',
                      ROOT/'spot_strategy_framework/spot_strategy/model.py'])
    return hashlib.sha256(dump({str(p.relative_to(ROOT)):hash_file(p) for p in paths}).encode()).hexdigest()

def connect(path=DATABASE):
    db=sqlite3.connect(path,timeout=20)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA journal_mode=WAL')
    return db

def migrate(db):
    # Explicit transaction covers the whole additive migration.
    db.executescript('BEGIN IMMEDIATE;'+SCHEMA+'INSERT OR IGNORE INTO mk_migration VALUES(1);COMMIT;')
    db.executescript("""BEGIN IMMEDIATE;
       CREATE TABLE IF NOT EXISTS mk_note(id INTEGER PRIMARY KEY,
        project INTEGER NOT NULL REFERENCES mk_project, kind TEXT NOT NULL
        CHECK(kind IN ('hypothesis','progress')), body TEXT NOT NULL);
       INSERT OR IGNORE INTO mk_migration VALUES(2);
       COMMIT;""")


def _immutable(db,table,keys,body):
    s=dump(body)
    sha=hashlib.sha256(s.encode()).hexdigest()
    fields=[*keys,'body','sha']
    sql='INSERT OR IGNORE INTO '+table+'('+','.join(fields)+') VALUES('+','.join('?' for _ in fields)+')'
    db.execute(sql,(*keys.values(),s,sha))
    row=db.execute('SELECT id,sha FROM '+table+' WHERE '+' AND '.join(k+'=?' for k in keys),tuple(keys.values())).fetchone()
    if row['sha']!=sha:raise ValueError('Version already registered with different content. Register a new version.')
    return row['id']

def register(db,spec,table):
    engine.rules(spec)
    engine.paytable(spec,table)
    with db:
        rid=_immutable(db,'mk_rule',dict(game=spec['game'],version=spec['version']),spec)
        pid=_immutable(db,'mk_paytable',dict(rule=rid,name=table['id'],version=table['version']),table)
    return rid,pid

def project(db,name,table_id,objective):
    row=db.execute('SELECT r.body FROM mk_paytable p JOIN mk_rule r ON r.id=p.rule WHERE p.id=?',(table_id,)).fetchone()
    if row is None:raise ValueError('Unknown paytable.')
    spec=json.loads(row['body'])
    if objective not in spec['objectives']:raise ValueError('Unsupported objective for this game.')
    with db:
        db.execute('INSERT OR IGNORE INTO mk_project(name,paytable,objective,cursor,stop) VALUES(?,?,?,?,?)',
                   (name,table_id,objective,'0',str(engine.scope(spec))))
        row=db.execute('SELECT * FROM mk_project WHERE name=?',(name,)).fetchone()
        if (row['paytable'],row['objective'])!=(table_id,objective):raise ValueError('Project name is already bound.')
    return row['id']

def context(db,name):
    row=db.execute('''SELECT x.*,p.body AS table_body,p.sha AS table_sha,p.rule,
                      r.body AS rule_body,r.sha AS rule_sha FROM mk_project x
                      JOIN mk_paytable p ON p.id=x.paytable JOIN mk_rule r ON r.id=p.rule WHERE x.name=?''',(name,)).fetchone()
    if row is None:raise ValueError('Unknown research project.')
    return row,json.loads(row['rule_body']),json.loads(row['table_body'])

def store_pattern(db,x,spec,cards,parent=None,changes=None):
    cards=engine.pattern(spec,cards)
    if parent is not None:
        old=db.execute('SELECT rule,cards FROM mk_pattern WHERE id=?',(parent,)).fetchone()
        if old is None or old['rule']!=x['rule']:raise ValueError('Parent belongs to another rule model.')
        if dump(cards)==old['cards']:raise ValueError('Edit changes no card.')
    db.execute('INSERT OR IGNORE INTO mk_pattern(rule,parent,cards,equivalence,changes) VALUES(?,?,?,?,?)',
               (x['rule'],parent,dump(cards),dump(engine.identity(spec,cards)),dump(changes) if changes is not None else None))
    id=db.execute('SELECT id FROM mk_pattern WHERE rule=? AND cards=?',(x['rule'],dump(cards))).fetchone()[0]
    if parent is not None:
        db.execute('INSERT OR IGNORE INTO mk_version VALUES(?,?,?)',(id,parent,dump(changes)))
    db.execute("INSERT OR IGNORE INTO mk_job(project,pattern,state) VALUES(?,?,'pending')",(x['id'],id))
    return id

def edit(db,name,parent,changes):
    x,spec,_=context(db,name)
    row=db.execute('SELECT * FROM mk_pattern WHERE id=? AND rule=?',(parent,x['rule'])).fetchone()
    if not row:raise ValueError('Unknown pattern in this game.')
    cards=json.loads(row['cards'])
    for slot,numbers in changes.items():
        if not slot.isdecimal() or not 1<=int(slot)<=len(cards):raise ValueError('Use 1-based card slots.')
        cards[int(slot)-1]=numbers
    with db:return store_pattern(db,x,spec,cards,parent,changes)

def legacy_adapter():
    """Load the original zero counters without requiring a research database."""
    framework=str(ROOT/'spot_strategy_framework')
    if framework not in sys.path:sys.path.insert(0,framework)
    from spot_strategy.model import Paytable, DENOMINATOR
    from unrestricted_resolution import zero
    return SimpleNamespace(TABLE=Paytable(ROOT/'outputs/keno-expanded-paytables.json'),
                           legacy=zero,Budget=zero.Budget,Limit=zero.Limit,D=DENOMINATOR)

def verify_record_a():
    spec,table=legacy_data()
    cards=engine.pattern(spec,tuple(tuple(range(i,i+4)) for i in range(1,81,4)))
    wins,law,method=evaluate(spec,table,cards,'any-payout',200000,True)
    total=comb(spec['universe'],spec['draw'])
    zero=total-wins
    if zero!=4**20:raise ArithmeticError('Record A compatibility check failed.')
    return dict(zero=zero,draws=total,probability=str(Fraction(wins,total)),
                paytable_sha256=legacy_adapter().TABLE.sha256,method=method,evidence=law)

def legacy_data():
    w=legacy_adapter()
    rule=dict(game='spot-keno-20',name='20 Card Keno',version='scenario-1-distinct-v1',universe=80,draw=20,
              cards=20,sizes=list(range(2,11)),duplicates=False,overlap=True,wager=1,unit='credit',
              mechanics=MECHANICS,objectives=['any-payout','net-profit'])
    table=dict(id='wizard-spot-table-4',version='frozen-scenario-1',
               source='https://wizardofodds.com/games/keno/spot-keno/ [frozen archive SHA-256 '+w.TABLE.sha256+']',
               payouts={str(s):list(w.TABLE[s]) for s in rule['sizes']},bonus=None)
    return rule,table

def bind_legacy(db):
    spec,table=legacy_data()
    _,pid=register(db,spec,table)
    id=project(db,'scenario1-any-payout',pid,'any-payout')
    x,_,_=context(db,'scenario1-any-payout')
    w=legacy_adapter()
    with db:
        db.execute('INSERT OR IGNORE INTO mk_legacy VALUES(?,?,?)',(id,str(DATABASE.relative_to(ROOT)),w.TABLE.sha256))
        evidence=ROOT/'outputs/phase4-discovery/coverage-final.json'
        if evidence.is_file():
            db.execute('INSERT OR IGNORE INTO mk_certificate(project,rule_sha,paytable_sha,scope,assumptions,evidence) VALUES(?,?,?,?,?,?)',
                       (id,x['rule_sha'],x['table_sha'],'85-incidence proof',
                        'Scenario 1 uniform 20 of 80, 20 distinct cards, sizes 2–10, any-positive payout; support splitting',
                        dump(dict(path=str(evidence.relative_to(ROOT)),sha256=hash_file(evidence)))))
    return id

def evaluate(spec,table,cards,objective,budget,legacy_allowed=False):
    if legacy_allowed and objective=='any-payout':
        w=legacy_adapter()
        st=SimpleNamespace(cards=cards)
        try:
            a=w.legacy.deletion(st,w.TABLE,w.Budget(budget,5))[0]
            b=w.legacy.frontier(st,w.TABLE,w.Budget(budget,5))[0]
        except w.Limit as error:raise engine.Deferred(str(error)) from error
        if a!=b:raise ArithmeticError('Legacy zero polynomials disagree.')
        return w.D-a[20],dict(zero_polynomial=a,verification=['legacy-deletion','legacy-frontier']),'legacy-zero'
    law=engine.evaluate(spec,table,cards,budget)
    return engine.score(spec,law,objective),dict(gross_counts=dict(law),verification=['membership-regions','literal-subsets']),'independent-gross'

def work(db,name,steps,budget,enumerate_more=False):
    if steps<1 or budget<1:raise ValueError('Positive steps and budget required.')
    x,spec,table=context(db,name)
    legacy_allowed=db.execute('SELECT 1 FROM mk_legacy WHERE project=?',(x['id'],)).fetchone() is not None
    # Any fingerprint mismatch disables the specialized route, never changes its payout assumptions.
    if legacy_allowed and (spec,table)!=legacy_data():raise ValueError('Legacy rules or paytable fingerprint mismatch.')
    total=comb(spec['universe'],spec['draw'])
    with db:
        run=db.execute('INSERT INTO mk_run(project,budget,engine_sha) VALUES(?,?,?)',
                       (x['id'],budget,evaluator_sha('legacy-zero' if legacy_allowed else 'independent-gross'))).lastrowid
    counters=dict(exact=0,deferred=0,generated=0,rejected=0)
    for _ in range(steps):
        db.execute('BEGIN IMMEDIATE')
        try:
            job=db.execute("""SELECT j.*,p.cards FROM mk_job j JOIN mk_pattern p ON p.id=j.pattern
                WHERE j.project=? AND (j.state='pending' OR (j.state='deferred' AND j.last_budget<?))
                ORDER BY j.id LIMIT 1""",(x['id'],budget)).fetchone()
            if job is None and enumerate_more:
                row=db.execute('SELECT cursor,stop FROM mk_project WHERE id=?',(x['id'],)).fetchone()
                rank=int(row['cursor'])
                if rank<int(row['stop']):
                    cards=engine.candidate(spec,rank)
                    try:engine.pattern(spec,cards)
                    except ValueError:
                        db.execute('UPDATE mk_project SET rejected=rejected+1 WHERE id=?',(x['id'],))
                        counters['rejected']+=1
                    else:
                        store_pattern(db,x,spec,cards)
                        counters['generated']+=1
                    db.execute('UPDATE mk_project SET cursor=? WHERE id=?',(str(rank+1),x['id']))
                    db.execute('UPDATE mk_run SET operations=operations+1 WHERE id=?',(run,))
                    db.commit()
                    continue
            if job is None:
                db.commit()
                break
            cards=tuple(map(tuple,json.loads(job['cards'])))
            try:wins,law,method=evaluate(spec,table,cards,x['objective'],budget,legacy_allowed)
            except engine.Deferred as error:
                db.execute("UPDATE mk_job SET state='deferred',last_budget=?,reason=? WHERE id=?",(budget,str(error),job['id']))
                counters['deferred']+=1
            else:
                db.execute('''INSERT INTO mk_evaluation(job,project,run,wins,total,probability,law,method,rule_sha,paytable_sha,evaluator_sha)
                              VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                           (job['id'],x['id'],run,str(wins),str(total),str(Fraction(wins,total)),dump(law),method,
                            x['rule_sha'],x['table_sha'],evaluator_sha(method)))
                db.execute("UPDATE mk_job SET state='verified',last_budget=?,reason=NULL WHERE id=?",(budget,job['id']))
                counters['exact']+=1
            db.execute('UPDATE mk_run SET operations=operations+1 WHERE id=?',(run,))
            db.commit()
        except BaseException:
            db.rollback()
            raise
    return counters

def leaders(db,name,limit):
    if limit<1:raise ValueError('Positive leaderboard limit required.')
    x,spec,_=context(db,name)
    rows=[dict(r) for r in db.execute("""SELECT e.id AS evaluation_id,p.id AS pattern_id,p.cards,e.wins,e.total,e.probability,e.method
         FROM mk_evaluation e JOIN mk_job j ON j.id=e.job JOIN mk_pattern p ON p.id=j.pattern
         WHERE e.project=? ORDER BY length(e.wins) DESC,e.wins DESC,e.id LIMIT ?""",(x['id'],limit))]
    if db.execute('SELECT 1 FROM mk_legacy WHERE project=?',(x['id'],)).fetchone():
        total=comb(spec['universe'],spec['draw'])
        # Only legacy two-counter verifications are promoted on this view.
        for r in db.execute('SELECT id,cards,zero,probability FROM leaderboard WHERE verification IS NOT NULL ORDER BY zero,id LIMIT ?',(limit,)):
            rows.append(dict(legacy_result_id=r['id'],cards=r['cards'],wins=str(total-r['zero']),
                             total=str(total),probability=r['probability'],method='legacy-verified'))
        rows.sort(key=lambda r:-int(r['wins']))
    return rows[:limit]

def fixture():
    spec=dict(game='synthetic-mini',name='Synthetic six-number fixture',version='v1',universe=6,draw=3,
              cards=2,sizes=[2,3],duplicates=False,overlap=True,wager=1,unit='test-credit',
              mechanics=MECHANICS,objectives=['any-payout','net-profit'])
    return spec,dict(id='test-awards',version='v1',source='Explicit synthetic test fixture; no commercial game rules.',
                     payouts={'2':[0,0,3],'3':[0,0,1,5]},bonus=None)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--db',type=Path,default=DATABASE)
    subs=p.add_subparsers(dest='cmd',required=True)
    subs.add_parser('init')
    subs.add_parser('fixture')
    subs.add_parser('verify-record-a')
    g=subs.add_parser('register')
    g.add_argument('rules',type=Path);g.add_argument('paytable',type=Path)
    a=subs.add_parser('project')
    a.add_argument('name');a.add_argument('paytable',type=int);a.add_argument('objective')
    for name in ('add','edit','queue','work','leaders','status','patterns','compare'):
        s=subs.add_parser(name);s.add_argument('name')
        if name=='add':s.add_argument('cards',help='JSON array of cards')
        if name in ('edit','queue'):s.add_argument('pattern',type=int)
        if name=='compare':s.add_argument('patterns',nargs='+',type=int)
        if name=='edit':s.add_argument('changes',help='JSON object keyed by 1-based card slot')
        if name=='work':
            s.add_argument('steps',type=int);s.add_argument('budget',type=int)
            s.add_argument('--enumerate',action='store_true')
        if name=='leaders':s.add_argument('--limit',type=int,default=10)
        if name=='patterns':
            s.add_argument('--number',type=int);s.add_argument('--spots',type=int)
    note=subs.add_parser('note')
    note.add_argument('name');note.add_argument('kind',choices=('hypothesis','progress'))
    note.add_argument('body')
    notes=subs.add_parser('notes')
    notes.add_argument('name')
    args=p.parse_args()
    if args.cmd=='verify-record-a':
        print(json.dumps(verify_record_a(),indent=2))
        return
    if not args.db.is_file():p.error('Use an existing continuation SQLite file.')
    with connect(args.db) as db:
        migrate(db)
        if args.cmd=='init':out={'legacy_project':bind_legacy(db)}
        elif args.cmd=='fixture':
            _,pid=register(db,*fixture())
            out={o:project(db,'fixture-'+o,pid,o) for o in ('any-payout','net-profit')}
        elif args.cmd=='register':out=register(db,json.loads(args.rules.read_text()),json.loads(args.paytable.read_text()))
        elif args.cmd=='project':out=project(db,args.name,args.paytable,args.objective)
        elif args.cmd=='edit':out=edit(db,args.name,args.pattern,json.loads(args.changes))
        elif args.cmd=='work':out=work(db,args.name,args.steps,args.budget,args.enumerate)
        elif args.cmd=='leaders':out=leaders(db,args.name,args.limit)
        else:
            x,spec,_=context(db,args.name)
            if args.cmd=='note':
                if not args.body.strip():raise ValueError('A research note cannot be empty.')
                with db:out=db.execute('INSERT INTO mk_note(project,kind,body) VALUES(?,?,?)',
                                       (x['id'],args.kind,args.body)).lastrowid
            elif args.cmd=='notes':
                out=[dict(r) for r in db.execute('SELECT id,kind,body FROM mk_note WHERE project=? ORDER BY id',(x['id'],))]
            elif args.cmd in ('add','queue'):
                if args.cmd=='queue':
                    row=db.execute('SELECT cards FROM mk_pattern WHERE id=? AND rule=?',(args.pattern,x['rule'])).fetchone()
                    if row is None:raise ValueError('Pattern belongs to another game or does not exist.')
                    cards=json.loads(row['cards'])
                else:cards=json.loads(args.cards)
                with db:out=store_pattern(db,x,spec,cards)
            elif args.cmd=='compare':
                out=[]
                for id in args.patterns:
                    row=db.execute('''SELECT p.id,p.cards,j.state,e.wins,e.total,e.probability,e.method
                                      FROM mk_pattern p LEFT JOIN mk_job j ON p.id=j.pattern AND j.project=?
                                      LEFT JOIN mk_evaluation e ON e.job=j.id WHERE p.rule=? AND p.id=?''',
                                   (x['id'],x['rule'],id)).fetchone()
                    if not row:raise ValueError(f'Unknown pattern {id} in this game.')
                    out.append(dict(row))
            elif args.cmd=='patterns':
                out=[]
                for row in db.execute('SELECT * FROM mk_pattern WHERE rule=? ORDER BY id',(x['rule'],)):
                    cards=json.loads(row['cards'])
                    if args.number is not None and not any(args.number in c for c in cards):continue
                    if args.spots is not None and not any(len(c)==args.spots for c in cards):continue
                    out.append(dict(id=row['id'],parent=row['parent'],cards=cards))
            else:
                states=dict(db.execute('SELECT state,count(*) FROM mk_job WHERE project=? GROUP BY state',(x['id'],)))
                out=dict(cursor=x['cursor'],stop=x['stop'],rejected=x['rejected'],jobs=states,
                         enumerated_and_evaluated=x['cursor']==x['stop'] and not(states.get('pending') or states.get('deferred')))
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
