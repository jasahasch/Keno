"""Exact persistent progressive search. Run init, work, verify, or audit."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'progressive-distinct'))
from run_distinct import (CAP,D,RECORD,TABLE,Strategy,Budget,Limit,canonical,check,metrics,
                          deletion,frontier,verify,proposals,Random,Counter,json,comb)
from types import SimpleNamespace
from itertools import combinations
from math import factorial,prod
from fractions import Fraction
import sqlite3,hashlib

DB=HERE/'search.sqlite'
ROOT=HERE.parents[1]
M=sum(comb(80,s) for s in range(2,11))
OLD=HERE.parent/'progressive-distinct'
FILES=[Path(__file__),ROOT/'unrestricted_resolution/zero.py',ROOT/'unrestricted_resolution/incidence.py',
       ROOT/'spot_strategy_framework/spot_strategy/pruning.py',OLD/'run_distinct.py',
       ROOT/'outputs/keno-expanded-paytables.json',HERE.parent/'incidence-ledger/ledger.json',
       HERE.parent/'payout-frequency-proof-extension/certificate.json']
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(o):
    return json.dumps(o,separators=(',',':'))

SCHEMA=f"""
CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS config(
 id INTEGER PRIMARY KEY, key TEXT UNIQUE NOT NULL, depth INTEGER NOT NULL CHECK(depth BETWEEN 1 AND 20),
 cards TEXT NOT NULL, composition TEXT NOT NULL, memberships TEXT NOT NULL,
 incidences INTEGER NOT NULL, support INTEGER NOT NULL, max_owner INTEGER NOT NULL,
 source TEXT NOT NULL, zero INTEGER CHECK(zero BETWEEN 0 AND {D}),
 wins INTEGER GENERATED ALWAYS AS ({D}-zero) VIRTUAL,
 state TEXT NOT NULL CHECK(state IN ('exact','count-deferred','canonical-deferred')),
 lower INTEGER NOT NULL DEFAULT 0, CHECK((state='exact')=(zero IS NOT NULL)));
CREATE INDEX IF NOT EXISTS ranking ON config(depth,zero) WHERE zero IS NOT NULL;
CREATE INDEX IF NOT EXISTS state_depth ON config(state,depth);
CREATE INDEX IF NOT EXISTS literal_cards ON config(depth,cards);
CREATE TABLE IF NOT EXISTS edge(parent INTEGER REFERENCES config, child INTEGER REFERENCES config,
 relation TEXT NOT NULL, PRIMARY KEY(parent,child,relation));
CREATE TABLE IF NOT EXISTS frontier(depth INTEGER, lane TEXT, config INTEGER REFERENCES config,
 PRIMARY KEY(depth,lane,config));
CREATE TABLE IF NOT EXISTS queue(
 id INTEGER PRIMARY KEY, kind TEXT, config INTEGER REFERENCES config, seed INTEGER, budget TEXT,
 status TEXT NOT NULL DEFAULT 'pending', result TEXT, UNIQUE(kind,config));
CREATE INDEX IF NOT EXISTS queue_pending ON queue(status,id);
CREATE TABLE IF NOT EXISTS branch(config INTEGER PRIMARY KEY REFERENCES config, remaining_choices INTEGER NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('open','terminal','certified')));
CREATE TABLE IF NOT EXISTS certificate(config INTEGER PRIMARY KEY REFERENCES config,
 zero_lower INTEGER NOT NULL, evidence TEXT NOT NULL, replay TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS verification(config INTEGER PRIMARY KEY REFERENCES config, evidence TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS provenance(name TEXT PRIMARY KEY, sha256 TEXT NOT NULL);
"""

def connect():
    db=sqlite3.connect(DB,timeout=20)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA synchronous=FULL')
    db.executescript(SCHEMA)
    return db

def key_for(cards):
    if len(cards)==1:return 'single:'+str(len(cards[0]))
    return canonical(Strategy(cards),550)['encoding']

def signature(cards):
    groups=Counter(sum(1<<i for i,c in enumerate(cards) if v in c) for v in range(1,81))
    return dump(sorted(groups.items()))

def put(db,cards,source,key=None,zero=None,state=None):
    check(cards)
    if key is None:
        try:key=key_for(cards)
        except Limit:
            key='literal:'+dump(sorted(cards))
            if zero is None:state='canonical-deferred'
    else:
        if len(cards)==1:key='single:'+str(len(cards[0]))
    t,s,d=metrics(cards)
    state='exact' if zero is not None else state or 'count-deferred'
    db.execute("""INSERT INTO config(key,depth,cards,composition,memberships,incidences,support,max_owner,source,zero,state)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(key) DO NOTHING""",
               (key,len(cards),dump(cards),dump(sorted(map(len,cards))),signature(cards),t,s,d,source,zero,state))
    row=db.execute('SELECT id,zero FROM config WHERE key=?',(key,)).fetchone()
    if zero is not None:
        if row['zero'] is not None:assert row['zero']==zero
        db.execute("UPDATE config SET zero=?,state='exact' WHERE id=?",(zero,row['id']))
    n=len(cards)
    db.execute('INSERT OR IGNORE INTO branch VALUES(?,?,?)',(row['id'],M-n if n<20 else 0,'open' if n<20 else 'terminal'))
    return row['id']

def balanced(cards):
    result=[]
    for c in cards:
        q,r=divmod(len(c),CAP[len(c)])
        groups=[]
        i=0
        for j in range(CAP[len(c)]):
            size=q+int(j<r)
            groups.append(c[i:i+size])
            i+=size
        result.append(groups)
    return result

MAX_COST=max(sum(comb(len(g),2) for g in gs) for gs in balanced(tuple(tuple(range(s)) for s in range(2,11))))

def clique_lower(cost):
    if cost>128:return 0
    x=Fraction(80**20,factorial(20))
    for i in range(1,20):x*=1-Fraction(i*(cost+40),3200)
    return -(-x.numerator//x.denominator)

def bound(db,id,cards,zero):
    groups=balanced(cards)
    edges={e for gs in groups for g in gs for e in combinations(g,2)}
    cost=len(edges)+(20-len(cards))*MAX_COST
    z=clique_lower(cost)
    if zero is not None:z=max(z,zero-(20-len(cards))*MAX_SINGLE)
    db.execute('UPDATE config SET lower=max(lower,?) WHERE id=?',(z,id))
    if len(cards)==20 or z<RECORD:return
    # Independently validate the partition implication on all subsets of each local size.
    independently_checked=[]
    for gs,c in zip(groups,cards):
        assert sorted(v for g in gs for v in g)==list(c)
        for b in range(1<<len(c)):
            if TABLE[len(c)][b.bit_count()]==0:continue
            selected={v for i,v in enumerate(c) if b>>i&1}
            assert any(len(selected.intersection(g))>=2 for g in gs)
        independently_checked.append(len(c))
    alternate={tuple(sorted((u,v))) for gs in groups for g in gs for j,u in enumerate(g) for v in g[:j]}
    assert alternate==edges
    if cost<=128:
        n=80*prod(3200-i*(cost+40) for i in range(1,20))
        d=40**19*factorial(20)
        assert clique_lower(cost)==(n+d-1)//d
    assert MAX_COST==9
    proof=dict(groups=groups,prefix_edges=len(edges),max_new_edges=MAX_COST,completion_edge_cap=cost,
               current_zero=zero,max_single_cover=MAX_SINGLE,benchmark=RECORD,
               theorem=str(FILES[-1].relative_to(ROOT)),theorem_sha256=sha(FILES[-1]))
    db.execute('INSERT OR REPLACE INTO certificate VALUES(?,?,?,?)',
               (id,z,dump(proof),dump(dict(pointwise_card_sizes=independently_checked,exact_integer_replay=True))))
    db.execute("UPDATE branch SET status='certified' WHERE config=?",(id,))

MAX_SINGLE=max(sum(comb(s,h)*comb(80-s,20-h) for h in range(CAP[s]+1,s+1)) for s in CAP)

def parent_key(cards):
    try:return key_for(cards)
    except Limit:return 'literal:'+dump(sorted(cards))

def manifest(db):
    actual={str(p.relative_to(ROOT)):sha(p) for p in FILES}
    old=json.loads(db.execute("SELECT value FROM metadata WHERE key='hashes'").fetchone()[0])
    if actual!=old:raise RuntimeError('Pinned mathematical or worker source changed. Use a new run or restore the pinned files.')

def init(db):
    if db.execute("SELECT 1 FROM metadata WHERE key='hashes'").fetchone():
        manifest(db)
        return
    names=[*(f'stage-{n:02d}' for n in range(1,21)),*(f'reopened-{n:02d}' for n in range(13,21)),'coordinated']
    with db:
        for name in names:
            path=OLD/(name+'.json')
            data=json.loads(path.read_text())
            db.execute('INSERT INTO provenance VALUES(?,?)',(str(path.relative_to(ROOT)),sha(path)))
            for row in data['rows']:
                cards=tuple(map(tuple,row['cards']))
                key=row.get('canonical')
                if key is None:key='literal:'+dump(sorted(cards))
                id=put(db,cards,'historical:'+name,key,row.get('zero'),row['status'])
                if len(cards)>1 and name!='coordinated':
                    # Every historical addition retains the original prefix order in its stored row.
                    p=db.execute('SELECT id FROM config WHERE cards=? AND depth=?',(dump(cards[:-1]),len(cards)-1)).fetchone()
                    if p is None:
                        prefix=parent_key(cards[:-1])
                        p=db.execute('SELECT id FROM config WHERE key=?',(prefix,)).fetchone()
                    if p:db.execute('INSERT OR IGNORE INTO edge VALUES(?,?,?)',(p['id'],id,'addition'))
            for row in data.get('beam',[]):
                key=row['canonical'] if len(row['cards'])>1 else 'single:'+str(len(row['cards'][0]))
                found=db.execute('SELECT id FROM config WHERE key=?',(key,)).fetchone()
                assert found
                db.execute('INSERT OR IGNORE INTO frontier VALUES(?,?,?)',(len(row['cards']),name,found['id']))
        for row in db.execute('SELECT * FROM config').fetchall():
            if row['depth']>=8:bound(db,row['id'],tuple(map(tuple,json.loads(row['cards']))),row['zero'])
        db.execute('INSERT INTO metadata VALUES(?,?)',('hashes',dump({str(p.relative_to(ROOT)):sha(p) for p in FILES})))
        db.execute('INSERT INTO metadata VALUES(?,?)',('root',dump(dict(individual_choices=M,
            distinct_unordered_layouts=str(comb(M,20)),open_extension='Any legal set not already present; sorted sequences give one path per portfolio.',
            inherited_ledger='../incidence-ledger/ledger.json',benchmark=RECORD,draw_denominator=D))))
        db.execute('INSERT INTO metadata VALUES(?,?)',('run',dump(dict(seed=418259,imported_proposals=25053,worker='per-task transactional'))))
        for r in db.execute("""SELECT c.id FROM config c JOIN branch b ON b.config=c.id
                WHERE c.state!='exact' AND b.status!='certified'
                ORDER BY depth DESC,id LIMIT 160""").fetchall():
            enqueue(db,'retry',r['id'])
        for depth in range(1,20):
            refresh(db,depth,16)
    print('initialized',db.execute('SELECT count(*) FROM config').fetchone()[0],flush=True)

def enqueue(db,kind,id):
    budget={'retry':[12000,.25,22000,.25],'expand':[2100,.08,4500,.07]}[kind]
    db.execute('INSERT OR IGNORE INTO queue(kind,config,seed,budget) VALUES(?,?,?,?)',
               (kind,id,418259+1009*id,dump(budget)))

def refresh(db,depth,width=10):
    # Keep independent overlap and composition lanes. No row is erased by queue selection.
    rows=db.execute("""SELECT c.* FROM config c JOIN branch b ON c.id=b.config
        WHERE depth=? AND zero IS NOT NULL AND b.status='open'
        ORDER BY lower,zero,id""",(depth,)).fetchall()
    used=set()
    for row in rows:
        tag=(min(6,row['incidences']-row['support']),min(5,row['max_owner']),row['incidences']//depth)
        if tag in used:continue
        used.add(tag)
        db.execute('INSERT OR IGNORE INTO frontier VALUES(?,?,?)',(depth,'persistent:'+dump(tag),row['id']))
        enqueue(db,'expand',row['id'])
        if len(used)>=width:break

def evaluate(cards,budget):
    st=SimpleNamespace(cards=cards)
    try:return deletion(st,TABLE,Budget(*budget[:2]))[0][20]
    except Limit:return frontier(st,TABLE,Budget(*budget[2:]))[0][20]

def work(db,limit):
    manifest(db)
    for step in range(limit):
        try:
            db.execute('BEGIN IMMEDIATE')
            job=db.execute("SELECT * FROM queue WHERE status='pending' ORDER BY id LIMIT 1").fetchone()
            if not job:
                db.commit()
                break
            row=db.execute('SELECT * FROM config WHERE id=?',(job['config'],)).fetchone()
            cards=tuple(map(tuple,json.loads(row['cards'])))
            result=Counter()
            budget=json.loads(job['budget'])
            if job['kind']=='retry':
                try:
                    z=evaluate(cards,budget)
                    db.execute("UPDATE config SET zero=?,state='exact' WHERE id=?",(z,row['id']))
                    bound(db,row['id'],cards,z)
                    result['exact']+=1
                    if len(cards)<20:enqueue(db,'expand',row['id'])
                except Limit:result['deferred']+=1
            else:
                rng=Random(job['seed'])
                for new,kind in proposals([dict(cards=cards)],rng):
                    result['generated']+=1
                    if len(set(new))!=len(new):
                        result['rejected_identical']+=1
                        continue
                    process(db,row['id'],new,kind,'addition',budget,result)
                if len(cards)>=2:
                    for size in range(2,11):
                        new=list(cards)
                        for i in rng.sample(range(len(cards)),2):
                            c=set(new[i])
                            replacement=rng.choice(sorted(set(range(1,81))-c))
                            c.remove(rng.choice(sorted(c)))
                            c.add(replacement)
                            new[i]=tuple(sorted(c))
                        new.append(tuple(sorted(rng.sample(range(1,81),size))))
                        result['generated']+=1
                        if len(set(new))!=len(new):
                            result['rejected_identical']+=1
                            continue
                        process(db,row['id'],tuple(new),'joint-restructure','restructure-then-add',budget,result)
            db.execute("UPDATE queue SET status='done',result=? WHERE id=?",(dump(result),job['id']))
            db.commit()
            if step%10==0:print('checkpoint',job['id'],job['kind'],dict(result),flush=True)
        except BaseException:
            db.rollback()
            raise

def process(db,parent,cards,source,relation,budget,result):
    old=db.total_changes
    id=put(db,cards,'new:'+source)
    row=db.execute('SELECT * FROM config WHERE id=?',(id,)).fetchone()
    db.execute('INSERT OR IGNORE INTO edge VALUES(?,?,?)',(parent,id,relation))
    if row['zero'] is not None or row['source']!='new:'+source or not old<db.total_changes-1:
        result['reused']+=1
        return
    try:
        z=evaluate(cards,budget)
        db.execute("UPDATE config SET zero=?,state='exact' WHERE id=?",(z,id))
        result['exact']+=1
    except Limit:
        z=None
        result['deferred']+=1
    bound(db,id,cards,z)

def verify_final(db):
    manifest(db)
    rows=db.execute("""SELECT * FROM config WHERE depth=20 AND zero IS NOT NULL
                      ORDER BY zero,id""").fetchall()
    groups={}
    for r in rows:
        labels=['overall']
        if r['source'].startswith('new:'):labels.append('new')
        if r['zero']<RECORD:labels.append('improvement:'+str(r['id']))
        if r['source'].startswith('new:') and r['max_owner']>1:labels.append('new-overlap')
        if r['source']=='new:joint-restructure':labels.append('new-joint')
        if all(k in groups for k in labels):continue
        cards=tuple(map(tuple,json.loads(r['cards'])))
        check(cards)
        try:v=verify(Strategy(cards),r['zero'])
        except Limit:continue
        with db:db.execute('INSERT OR REPLACE INTO verification VALUES(?,?)',(r['id'],dump(v)))
        for k in labels:groups.setdefault(k,dict(id=r['id'],source=r['source'],**v))
    (HERE/'leaders.json').write_text(json.dumps(groups,indent=2)+'\n')

def audit(db):
    manifest(db)
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    assert not db.execute("SELECT 1 FROM branch b JOIN config c ON c.id=b.config WHERE b.status='certified' AND NOT EXISTS(SELECT 1 FROM certificate e WHERE e.config=c.id AND e.zero_lower>=?)",(RECORD,)).fetchone()
    for row in db.execute('SELECT * FROM config'):
        cards=tuple(map(tuple,json.loads(row['cards'])))
        check(cards)
        assert len(cards)==row['depth'] and metrics(cards)==(row['incidences'],row['support'],row['max_owner'])
        assert signature(cards)==row['memberships']
        if row['zero'] is not None:assert row['wins']+row['zero']==D
    report={}
    for table in ('config','edge','branch','frontier','queue','certificate','verification'):
        report[table]=db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
    report['config_states']=[list(r) for r in db.execute('SELECT state,count(*) FROM config GROUP BY state')]
    report['branch_states']=[list(r) for r in db.execute('SELECT status,count(*) FROM branch GROUP BY status')]
    report['queue_states']=[list(r) for r in db.execute('SELECT kind,status,count(*) FROM queue GROUP BY kind,status')]
    report['new_states']=[list(r) for r in db.execute("SELECT state,count(*) FROM config WHERE source LIKE 'new:%' GROUP BY state")]
    report['new_final_states']=[list(r) for r in db.execute("SELECT state,count(*) FROM config WHERE source LIKE 'new:%' AND depth=20 GROUP BY state")]
    totals=Counter()
    for r in db.execute("SELECT result FROM queue WHERE status='done'"):totals.update(json.loads(r[0]))
    report['work']=dict(totals)
    report.update(integrity='ok',foreign_key_errors=0,denominator=D,journal_mode=db.execute('PRAGMA journal_mode').fetchone()[0])
    with sqlite3.connect(HERE/'search-backup.sqlite') as backup:
        db.backup(backup)
        assert backup.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert backup.execute('SELECT count(*) FROM config').fetchone()[0]==report['config']
    report['backup_integrity']='ok'
    (HERE/'integrity.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report,flush=True)

if __name__=='__main__':
    db=connect()
    cmd=sys.argv[1]
    if cmd=='init':init(db)
    elif cmd=='work':work(db,int(sys.argv[2]))
    elif cmd=='verify':verify_final(db)
    elif cmd=='audit':audit(db)
    elif cmd=='plan':
        manifest(db)
        with db:
            for depth in range(1,20):refresh(db,depth,24)
    else:raise SystemExit('Use init, work TASKS, plan, verify, or audit.')
