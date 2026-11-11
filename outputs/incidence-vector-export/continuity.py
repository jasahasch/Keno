"""Resumable coverage queue. The historical source and export are read-only."""
from pathlib import Path
from math import comb
import sqlite3,json,sys,hashlib
from types import SimpleNamespace
from export_vectors import SOURCE,OUT,connect,sha
sys.path.insert(0,str(OUT.parent/'persistent-progressive'))
from research_db import TABLE,Budget,Limit,deletion,frontier,RECORD

OFFSETS={s:sum(comb(80,k) for k in range(2,s)) for s in range(2,11)}
M=sum(comb(80,k) for k in range(2,11))

def open_queue():
    db=sqlite3.connect(OUT/'continuity.sqlite',timeout=20)
    db.row_factory=sqlite3.Row
    db.executescript('''
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=FULL;
        CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS scope(
          id TEXT PRIMARY KEY, source_id INTEGER, kind TEXT NOT NULL,
          cards TEXT NOT NULL, cursor TEXT NOT NULL, stop TEXT NOT NULL,
          status TEXT NOT NULL, last_turn INTEGER NOT NULL DEFAULT 0,
          last_resource TEXT, parent TEXT REFERENCES scope, zero INTEGER);
        CREATE INDEX IF NOT EXISTS next_scope ON scope(status,last_turn,id);
        CREATE TABLE IF NOT EXISTS attempt(
          turn INTEGER PRIMARY KEY, scope TEXT REFERENCES scope, cursor TEXT NOT NULL,
          resource TEXT NOT NULL, result TEXT NOT NULL);
        PRAGMA foreign_keys=ON;
    ''')
    return db

def init(db):
    identity=sha(SOURCE)
    old=db.execute("SELECT value FROM metadata WHERE key='source'").fetchone()
    if old:
        assert old[0]==identity
        return
    with connect(SOURCE) as source,db:
        db.execute('INSERT INTO metadata VALUES(?,?)',('source',identity))
        db.execute('INSERT INTO scope(id,kind,cards,cursor,stop,status) VALUES(?,?,?,?,?,?)',
                   ('universal','all-distinct','[]','0',str(comb(M,20)),'open'))
        for r in source.execute('SELECT c.*,b.status AS branch_status FROM config c JOIN branch b ON c.id=b.config'):
            n=r['depth']
            prefix=r['branch_status']
            state=('certified' if prefix=='certified' else 'resolved' if n==20 and r['zero'] is not None
                   else 'deferred' if r['zero'] is None else 'open')
            db.execute('''INSERT INTO scope(id,source_id,kind,cards,cursor,stop,status,zero)
                          VALUES(?,?,?,?,?,?,?,?)''',
                       (f"stored:{r['id']:08d}",r['id'],'prefix' if n<20 else 'terminal',
                        r['cards'],'0',str(comb(M-n,20-n)) if n<20 else '1',state,r['zero']))

def unrank(n,k,rank):
    assert 0<=rank<comb(n,k)
    items=[]
    low=0
    while k:
        left,right=low,n-k
        base=comb(n-low,k)
        while left<right:
            mid=(left+right+1)//2
            if base-comb(n-mid,k)<=rank:left=mid
            else:right=mid-1
        rank-=base-comb(n-left,k)
        items.append(left)
        low=left+1
        k-=1
    return items

def card_rank(card):
    k=len(card)
    result=OFFSETS[k]
    low=0
    for v in card:
        result+=comb(80-low,k)-comb(81-v,k)
        low=v
        k-=1
    return result

def card_at(rank):
    size=max(s for s,i in OFFSETS.items() if i<=rank)
    return tuple(i+1 for i in unrank(80,size,rank-OFFSETS[size]))

def completion(prefix,rank):
    omitted=sorted(map(card_rank,prefix))
    indices=unrank(M-len(prefix),20-len(prefix),rank)
    cards=list(prefix)
    for ix in indices:
        for excluded in omitted:
            if excluded>ix:break
            ix+=1
        cards.append(card_at(ix))
    assert len(cards)==len(set(cards))==20
    return tuple(cards)

def evaluate(cards,states,seconds):
    st=SimpleNamespace(cards=cards)
    try:return deletion(st,TABLE,Budget(states,seconds))[0][20]
    except Limit:return frontier(st,TABLE,Budget(states,seconds))[0][20]

READY="""status='open' OR
        (status='deferred' AND (last_resource IS NULL OR last_resource!=?))"""

def run(db,steps,states,seconds,only_existing=False):
    root=OUT.parents[1]
    dependencies=[Path(__file__),root/'unrestricted_resolution/zero.py',root/'outputs/keno-expanded-paytables.json']
    hashes=[sha(p) for p in dependencies]
    resource=json.dumps([hashes,states,seconds],separators=(',',':'))
    for _ in range(steps):
        db.execute('BEGIN IMMEDIATE')
        try:
            clause=" AND status='deferred' AND source_id IS NOT NULL" if only_existing else ''
            row=db.execute(f"""SELECT * FROM scope WHERE ({READY}){clause}
                               ORDER BY last_turn,id LIMIT 1""",(resource,)).fetchone()
            if not row:
                db.commit()
                break
            turn=db.execute('SELECT coalesce(max(turn),0)+1 FROM attempt').fetchone()[0]
            db.execute("UPDATE scope SET status='active' WHERE id=?",(row['id'],))
            cards=tuple(map(tuple,json.loads(row['cards'])))
            cursor=int(row['cursor'])
            z=row['zero']
            if row['status']=='deferred':
                # For a deferred prefix, first recover its own count. Its completions stay open.
                try:
                    z=evaluate(cards,states,seconds)
                    if len(cards)==20 and z<RECORD:
                        a=deletion(SimpleNamespace(cards=cards),TABLE,Budget(states,seconds))[0]
                        b=frontier(SimpleNamespace(cards=cards),TABLE,Budget(states,seconds))[0]
                        assert a==b and a[20]==z
                    status='open' if row['kind']=='prefix' else 'resolved'
                    result='exact-existing-or-deferred'
                except Limit:
                    status='deferred'
                    result='count-deferred'
            else:
                new=completion(cards,cursor)
                try:
                    value=evaluate(new,states,seconds)
                    result=f'exact-completion:{value}'
                    if value<RECORD:
                        a=deletion(SimpleNamespace(cards=new),TABLE,Budget(states,seconds))[0]
                        b=frontier(SimpleNamespace(cards=new),TABLE,Budget(states,seconds))[0]
                        assert a==b and a[20]==value
                        result=f'independently-verified-improvement:{value}'
                except Limit:
                    child=f"{row['id']}@{cursor}"
                    db.execute('''INSERT INTO scope(id,kind,cards,cursor,stop,status,last_turn,last_resource,parent)
                                  VALUES(?,?,?,?,?,?,?,?,?)''',
                               (child,'terminal',json.dumps(new),'0','1','deferred',turn,resource,row['id']))
                    result='completion-deferred:'+child
                cursor+=1
                status='open' if cursor<int(row['stop']) else 'scanned'
            db.execute('UPDATE scope SET cursor=?,status=?,last_turn=?,last_resource=?,zero=? WHERE id=?',
                       (str(cursor),status,turn,resource,z,row['id']))
            db.execute('INSERT INTO attempt VALUES(?,?,?,?,?)',(turn,row['id'],row['cursor'],resource,result))
            db.commit()
        except BaseException:
            db.rollback()
            raise

def audit(db):
    statuses=dict(db.execute('SELECT status,count(*) FROM scope GROUP BY status'))
    all_ids={r[0] for r in db.execute("SELECT id FROM scope WHERE status IN ('open','deferred')")}
    eligible={r[0] for r in db.execute(f'SELECT id FROM scope WHERE {READY}',('future-resource-signature',))}
    assert all_ids==eligible
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    # Round-trip legal card ranks and test the first/last global completion.
    for rank in (0,1,M//2,M-1,*OFFSETS.values()):
        assert card_rank(card_at(rank))==rank
    for rank in (0,comb(M,20)-1):
        assert len(set(completion((),rank)))==20
    with connect(SOURCE) as source:
        n=source.execute('SELECT count(*) FROM config').fetchone()[0]
        assert n==db.execute('SELECT count(*) FROM scope WHERE source_id IS NOT NULL').fetchone()[0]
    result={k:statuses.get(k,0) for k in ('open','active','deferred','certified','resolved','scanned')}
    result.update(unresolved=len(all_ids),reachable_with_new_resources=len(eligible),
                  source_rows=n,universal_scope=True,
                  attempts=[dict(r) for r in db.execute('SELECT * FROM attempt ORDER BY turn DESC LIMIT 20')],
                  committed_attempts=db.execute('SELECT count(*) FROM attempt').fetchone()[0],
                  integrity='ok')
    (OUT/'continuity_report.json').write_text(json.dumps(result,indent=2)+'\n')
    print({k:v for k,v in result.items() if k!='attempts'})

if __name__=='__main__':
    db=open_queue()
    init(db)
    if len(sys.argv)>1 and sys.argv[1]=='work':
        run(db,int(sys.argv[2]),int(sys.argv[3]),float(sys.argv[4]),'--existing-only' in sys.argv)
    audit(db)
