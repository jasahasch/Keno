"""Search and version existing continuation patterns, and retain incremental backups."""
import argparse
import hashlib
from fractions import Fraction
import json
from pathlib import Path
import shutil
import sqlite3
import struct
from tempfile import TemporaryDirectory

RESERVE = 64 * 1024 * 1024

SCHEMA = """
CREATE TABLE IF NOT EXISTS pattern_number(
 result INTEGER REFERENCES completed, number INTEGER, multiplicity INTEGER,
 PRIMARY KEY(result,number));
CREATE INDEX IF NOT EXISTS pattern_number_lookup ON pattern_number(number,multiplicity,result);
CREATE TABLE IF NOT EXISTS pattern_size(
 result INTEGER REFERENCES completed, spots INTEGER, copies INTEGER,
 PRIMARY KEY(result,spots));
CREATE INDEX IF NOT EXISTS pattern_size_lookup ON pattern_size(spots,copies,result);
CREATE INDEX IF NOT EXISTS pattern_support ON completed(support,incidences,zero);
CREATE INDEX IF NOT EXISTS pattern_composition ON completed(composition);
CREATE INDEX IF NOT EXISTS pattern_overlap ON completed(incidences-support);
CREATE INDEX IF NOT EXISTS pattern_memberships ON completed(memberships);
CREATE INDEX IF NOT EXISTS scope_status_kind ON scope(status,kind);
CREATE INDEX IF NOT EXISTS evaluation_result ON evaluation(result,origin,identity);
CREATE TABLE IF NOT EXISTS evaluation_detail(
 turn INTEGER PRIMARY KEY REFERENCES attempt, zero_polynomial TEXT NOT NULL,
 evaluator TEXT NOT NULL, evaluator_sha TEXT NOT NULL, paytable_sha TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS pattern_version(
 scope TEXT PRIMARY KEY REFERENCES scope, parent INTEGER NOT NULL REFERENCES completed,
 cards TEXT NOT NULL, changes TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS index_pattern AFTER INSERT ON completed BEGIN
 INSERT INTO pattern_number
 SELECT new.id, v.value, count(*) FROM json_each(new.cards) c, json_each(c.value) v GROUP BY v.value;
 INSERT INTO pattern_size
 SELECT new.id, s.value, count(*) FROM json_each(new.composition) s GROUP BY s.value;
END;
CREATE VIEW IF NOT EXISTS pattern_history AS
 SELECT e.*, a.scope, a.cursor, s.parent AS scope_parent
 FROM evaluation e LEFT JOIN attempt a ON e.origin IN ('worker','historical-attempt') AND a.turn=e.identity
 LEFT JOIN scope s ON s.id=a.scope;
"""

def evaluate(w,cards,states,seconds):
    from types import SimpleNamespace
    from component_eval import evaluate as cached
    try:
        fast=cached(w,cards,states,seconds)
        if fast is not None:return fast
    except w.Limit:pass
    st=SimpleNamespace(cards=cards)
    try:return w.legacy.deletion(st,w.TABLE,w.Budget(states,seconds))
    except w.Limit:return w.legacy.frontier(st,w.TABLE,w.Budget(states,seconds))


def migrate(db):
    db.executescript(SCHEMA)
    with db:
        db.execute("""INSERT OR IGNORE INTO pattern_number
            SELECT p.id,v.value,count(*) FROM completed p,json_each(p.cards) c,json_each(c.value) v
            WHERE NOT EXISTS(SELECT 1 FROM pattern_number n WHERE n.result=p.id)
            GROUP BY p.id,v.value""")
        db.execute("""INSERT OR IGNORE INTO pattern_size
            SELECT p.id,s.value,count(*) FROM completed p,json_each(p.composition) s
            WHERE NOT EXISTS(SELECT 1 FROM pattern_size n WHERE n.result=p.id)
            GROUP BY p.id,s.value""")

def disk(path, extra=0):
    free=shutil.disk_usage(path.parent).free
    need=RESERVE+extra
    if free<need:
        raise OSError(f'Insufficient disk space: {free} bytes available, {need} bytes required. Resume after freeing space.')

def search(db,args):
    terms=[]
    values=[]
    for n in args.number:
        terms.append('EXISTS(SELECT 1 FROM pattern_number n WHERE n.result=c.id AND n.number=?)')
        values.append(n)
    for s in args.spots:
        terms.append('EXISTS(SELECT 1 FROM pattern_size s WHERE s.result=c.id AND s.spots=?)')
        values.append(s)
    for column,value in [('id',args.id),('zero',args.zero),('support',args.support),('incidences',args.incidences),('max_owner',args.max_owner)]:
        if value is not None:terms.append(f'c.{column}=?');values.append(value)
    if args.composition is not None:
        terms.append('c.composition=?')
        values.append(json.dumps(sorted(map(int,args.composition.split(','))),separators=(',',':')))
    if args.overlap is not None:terms.append('c.incidences-c.support=?');values.append(args.overlap)
    if args.memberships is not None:terms.append('c.memberships=?');values.append(json.dumps(json.loads(args.memberships),separators=(',',':')))
    if args.min_probability is not None:
        from continuity import D
        probability=Fraction(args.min_probability)
        if not 0<=probability<=1:raise ValueError('Probability must be between zero and one.')
        cap=(1-probability)*D
        terms.append('c.zero<=?')
        values.append(cap.numerator//cap.denominator)
    if args.max_zero is not None:terms.append('c.zero<=?');values.append(args.max_zero)
    if args.status=='verification-pending':
        terms.append('c.zero<? AND c.verification IS NULL')
        values.append(4**20)
    elif args.status=='verified':
        terms.append('c.verification IS NOT NULL')
    if args.status=='deferred':
        if args.id is not None:raise ValueError('Result IDs identify completed patterns; deferred patterns have scope IDs.')
        from continuity import cards_of,memberships
        from collections import Counter
        for row in db.execute("SELECT id,cards,kind,parent,zero FROM scope WHERE status='deferred' ORDER BY id"):
            cards=cards_of(row)
            sizes=set(map(len,cards))
            counts=Counter(v for c in cards for v in c)
            support=len(counts)
            total=sum(map(len,cards))
            if args.zero is not None and row['zero']!=args.zero:continue
            if args.composition is not None and sorted(map(len,cards))!=sorted(map(int,args.composition.split(','))):continue
            if not set(args.number)<=counts.keys() or not set(args.spots)<=sizes:continue
            if any(a is not None and a!=b for a,b in (
                (args.support,support),(args.incidences,total),(args.max_owner,max(counts.values(),default=0)),
                (args.overlap,total-support))):continue
            if args.memberships is not None and json.loads(args.memberships)!=[list(x) for x in sorted(memberships(cards).items())]:continue
            if args.min_probability is not None or args.max_zero is not None:
                if len(cards)!=20 or row['zero'] is None:continue
                if args.min_probability is not None and row['zero']>cap:continue
                if args.max_zero is not None and row['zero']>args.max_zero:continue
            print(json.dumps(dict(row)))
        return
    where=' WHERE '+' AND '.join(terms) if terms else ''
    for row in db.execute('SELECT c.* FROM completed c'+where+' ORDER BY c.zero,c.id',values):
        print(json.dumps(dict(row)))

def edit(db,w,parent,changes):
    row=db.execute('SELECT cards FROM completed WHERE id=?',(parent,)).fetchone()
    if not row:raise ValueError('Unknown parent result.')
    cards=list(w.cards_of(row))
    normalized={}
    for change in changes:
        slot,text=change.split('=',1)
        if len(slot)!=1 or not 'A'<=slot<='T' or slot in normalized:raise ValueError('Use each A–T slot at most once.')
        new=tuple(sorted(map(int,text.split(','))))
        cards[ord(slot)-65]=new
        normalized[slot]=new
    w.check(tuple(cards))
    if tuple(cards)==w.cards_of(row):raise ValueError('The edit must change a card.')
    if set(cards)==set(w.cards_of(row)):raise ValueError('The edit must change a selection, rather than permuting slots.')
    raw=w.dump(cards)
    id=f'version:{parent}:'+hashlib.sha256(raw.encode()).hexdigest()
    with db:
        db.execute("""INSERT OR IGNORE INTO scope(id,kind,cards,cursor,stop,status)
                      VALUES(?,'terminal',?,'0','1','deferred')""",(id,raw))
        w.schedule(db,id,tuple(cards),'terminal')
        db.execute('INSERT OR IGNORE INTO pattern_version VALUES(?,?,?,?)',(id,parent,raw,w.dump(normalized)))
    return id

def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def incremental(db,base,target):
    """Write a lossless changed-page overlay against the named immutable base."""
    if target.exists():raise FileExistsError(target)
    if not base.is_file():raise FileNotFoundError(base)
    disk(target,3*db.execute("PRAGMA page_count").fetchone()[0]*db.execute("PRAGMA page_size").fetchone()[0])
    with TemporaryDirectory(dir=target.parent) as tmp:
        snapshot=Path(tmp)/'snapshot.sqlite'
        with sqlite3.connect(snapshot) as copy:
            db.backup(copy,pages=128)
            assert copy.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            page=copy.execute('PRAGMA page_size').fetchone()[0]
        metadata=dict(base=str(base.resolve()),base_sha256=digest(base),snapshot_sha256=digest(snapshot),
                      page_size=page,size=snapshot.stat().st_size)
        delta=Path(tmp)/'changes.pages'
        count=0
        with base.open('rb') as a,snapshot.open('rb') as b,delta.open('wb') as out:
            out.write(json.dumps(metadata).encode()+b'\n')
            for i in range(metadata['size']//page):
                new=b.read(page)
                if a.read(page)!=new:
                    out.write(struct.pack('>Q',i));out.write(new);count+=1
        restored=Path(tmp)/'restore.sqlite'
        restore(base,delta,restored)
        with sqlite3.connect(restored.as_uri()+'?immutable=1',uri=True) as copy:
            assert copy.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        delta.rename(target)
    return dict(metadata,changed_pages=count,delta_bytes=target.stat().st_size)

def restore(base,delta,target):
    if target.exists():raise FileExistsError(target)
    with delta.open('rb') as inp:
        m=json.loads(inp.readline())
        if digest(base)!=m['base_sha256']:raise ValueError('Wrong backup base.')
        disk(target,m['size'])
        temp=target.with_suffix(target.suffix+'.tmp')
        try:
            shutil.copyfile(base,temp)
            with temp.open('r+b') as out:
                out.truncate(m['size'])
                while index:=inp.read(8):
                    i=struct.unpack('>Q',index)[0]
                    data=inp.read(m['page_size'])
                    if len(data)!=m['page_size'] or (i+1)*len(data)>m['size']:raise ValueError('Invalid delta page.')
                    out.seek(i*len(data));out.write(data)
            if digest(temp)!=m['snapshot_sha256']:raise ValueError('Restored snapshot checksum mismatch.')
            temp.rename(target)
        finally:
            if temp.exists():temp.unlink()

def main():
    import continuity as w
    p=argparse.ArgumentParser()
    commands=p.add_subparsers(dest='action',required=True)
    find=commands.add_parser('search')
    for f in ('number','spots'):find.add_argument('--'+f,action='append',type=int,default=[])
    for f in ('id','zero','support','incidences','max-owner','overlap','max-zero'):find.add_argument('--'+f,type=int)
    find.add_argument('--memberships')
    find.add_argument('--composition',help='Comma-separated individual card sizes')
    find.add_argument('--min-probability')
    find.add_argument('--status',choices=['exact','verified','verification-pending','deferred'],default='exact')
    change=commands.add_parser('edit')
    change.add_argument('parent',type=int)
    change.add_argument('cards',nargs='+')
    backup=commands.add_parser('backup')
    backup.add_argument('base',type=Path)
    backup.add_argument('delta',type=Path)
    recover=commands.add_parser('restore')
    for name in ('base','delta','target'):recover.add_argument(name,type=Path)
    args=p.parse_args()
    if args.action=='restore':restore(args.base,args.delta,args.target);return
    if not w.DATABASE.is_file():p.error('Continuation database is missing.')
    with w.connect(w.DATABASE) as db:
        w.compatible(db,w.fingerprint())
        if args.action=='edit':
            disk(w.DATABASE)
            print(edit(db,w,args.parent,args.cards))
        elif args.action=='search':search(db,args)
        else:print(json.dumps(incremental(db,args.base,args.delta),indent=2))

if __name__=='__main__':main()
