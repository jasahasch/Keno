"""Additive result storage and fair scheduling for the existing continuation queue."""
import argparse
import retention
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
HISTORY = OUT.parent / 'incidence-vector-export'
DATABASE = OUT / 'continuity.sqlite'
sys.path.insert(0, str(HISTORY))
# Load the existing worker under an explicit alias so the original stays immutable.
from importlib.util import spec_from_file_location, module_from_spec
spec = spec_from_file_location('continuation_legacy', HISTORY / 'continuity.py')
legacy = module_from_spec(spec)
spec.loader.exec_module(legacy)
from research_db import TABLE, Budget, Limit, RECORD, D, canonical, Strategy, check

PAYTABLE = ROOT / 'outputs/keno-expanded-paytables.json'
EVALUATOR = ROOT / 'unrestricted_resolution/zero.py'
CANONICALIZER = ROOT / 'unrestricted_resolution/incidence.py'
SOURCE = legacy.SOURCE

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS completed(
 id INTEGER PRIMARY KEY, canonical TEXT UNIQUE, literal TEXT UNIQUE NOT NULL,
 cards TEXT NOT NULL, composition TEXT NOT NULL, memberships TEXT NOT NULL,
 support INTEGER NOT NULL, incidences INTEGER NOT NULL, max_owner INTEGER NOT NULL,
 zero INTEGER NOT NULL CHECK(typeof(zero)='integer' AND zero BETWEEN 0 AND {D}),
 probability TEXT NOT NULL, evaluator_sha TEXT NOT NULL, paytable_sha TEXT NOT NULL,
 canonicalizer_sha TEXT NOT NULL, verification TEXT
);
CREATE INDEX IF NOT EXISTS completed_rank ON completed(zero,id);
CREATE INDEX IF NOT EXISTS completed_profile ON completed(incidences,support,max_owner);
CREATE VIEW IF NOT EXISTS leaderboard AS
    SELECT * FROM completed WHERE zero>={RECORD} OR verification IS NOT NULL;
CREATE TABLE IF NOT EXISTS evaluation(
 origin TEXT NOT NULL, identity INTEGER NOT NULL, result INTEGER NOT NULL REFERENCES completed,
 cards TEXT NOT NULL, evaluator_sha TEXT NOT NULL, paytable_sha TEXT NOT NULL,
 PRIMARY KEY(origin,identity));
CREATE TABLE IF NOT EXISTS scheduling(
 scope TEXT PRIMARY KEY REFERENCES scope, lane TEXT NOT NULL, depth INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS scheduling_lane ON scheduling(lane,depth);
CREATE TABLE IF NOT EXISTS lane_service(lane TEXT PRIMARY KEY,last_turn INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS invocation(
 id INTEGER PRIMARY KEY, first_turn INTEGER, last_turn INTEGER, counts TEXT NOT NULL
);
"""

def dump(obj):
    return json.dumps(obj, separators=(',', ':'))

def fingerprint():
    return dict(evaluator=legacy.sha(EVALUATOR), paytable=legacy.sha(PAYTABLE),
                canonicalizer=legacy.sha(CANONICALIZER), component=legacy.sha(OUT/'component_eval.py'))

def compatible(db, hashes):
    source_row = db.execute("SELECT value FROM metadata WHERE key='source'").fetchone()
    source_sha = source_row[0] if source_row else None
    if source_sha != legacy.sha(SOURCE):
        raise RuntimeError('Source research snapshot has changed.')
    with legacy.connect(SOURCE) as source:
        expected = json.loads(source.execute("SELECT value FROM metadata WHERE key='hashes'").fetchone()[0])
    if hashes['paytable'] != expected[str(PAYTABLE.relative_to(ROOT))] or TABLE.sha256 != hashes['paytable']:
        raise RuntimeError('Frozen paytable does not match source research.')

def connect(path):
    db = sqlite3.connect(path, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA synchronous=FULL')
    return db

def cards_of(row):
    return tuple(map(tuple, json.loads(row['cards'])))

def memberships(cards):
    return Counter(sum(1 << i for i, card in enumerate(cards) if v in card) for v in range(1, 81))

def profile(cards, kind):
    masks = memberships(cards)
    support = 80 - masks[0]
    total = sum(map(len, cards))
    degree = max(mask.bit_count() for mask in masks)
    sizes = sorted(set(map(len, cards)))
    return dump([kind, len(cards), sizes, total // 8, support // 8,
                 min(6, total-support), min(6, degree)]), len(cards)

def schedule(db, id, cards, kind):
    lane, depth = profile(cards, kind)
    db.execute('INSERT OR IGNORE INTO scheduling VALUES(?,?,?)', (id, lane, depth))

def save_result(db, cards, zero, hashes, origin, identity, verification=None):
    check(cards)
    assert len(cards) == 20 and type(zero) is int and 0 <= zero <= D
    literal = dump(sorted(cards))
    try:
        code = canonical(Strategy(cards), 550)['encoding']
    except Limit:
        code = None
    row = db.execute('SELECT id,zero,canonical FROM completed WHERE literal=? OR canonical=? ORDER BY id',
                     (literal, code)).fetchone()
    inserted = row is None
    if inserted:
        masks = memberships(cards)
        cur = db.execute("""INSERT INTO completed(canonical,literal,cards,composition,memberships,support,incidences,
                             max_owner,zero,probability,evaluator_sha,paytable_sha,canonicalizer_sha,verification)
                             VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (code,literal,dump(cards),dump(sorted(map(len,cards))),dump(sorted(masks.items())),
                          80-masks[0],sum(map(len,cards)),max(m.bit_count() for m in masks),zero,
                          str(Fraction(D-zero,D)),hashes['evaluator'],hashes['paytable'],
                          hashes['canonicalizer'],dump(verification) if verification else None))
        id = cur.lastrowid
    else:
        id = row['id']
        assert row['zero'] == zero, 'Same layout produced different exact counts.'
        if verification:
            db.execute('UPDATE completed SET verification=coalesce(verification,?) WHERE id=?',
                       (dump(verification),id))
        if code and row['canonical'] is None:
            db.execute('UPDATE OR IGNORE completed SET canonical=? WHERE id=?',(code,id))
    db.execute('INSERT INTO evaluation VALUES(?,?,?,?,?,?)',
               (origin,identity,id,dump(cards),hashes['evaluator'],hashes['paytable']))
    return inserted

def independent(cards, zero, states, seconds):
    st = SimpleNamespace(cards=cards)
    a,sa = legacy.deletion(st,TABLE,Budget(states,seconds))
    b,sb = legacy.frontier(st,TABLE,Budget(states,seconds))
    assert a == b and a[20] == zero
    return dict(polynomial=a,methods=[sa,sb])

def migrate(db, hashes):
    db.executescript(SCHEMA)
    if db.execute("SELECT 1 FROM metadata WHERE key='result_schema_v1'").fetchone():
        return
    with db:
        for row in db.execute('SELECT * FROM scope'):
            schedule(db,row['id'],cards_of(row),row['kind'])
        with legacy.connect(SOURCE) as source:
            pins=json.loads(source.execute("SELECT value FROM metadata WHERE key='hashes'").fetchone()[0])
            evidence_hashes=dict(hashes,evaluator=pins[str(EVALUATOR.relative_to(ROOT))])
            for row in source.execute('SELECT id,cards,zero FROM config WHERE depth=20 AND zero IS NOT NULL ORDER BY id'):
                cards=cards_of(row)
                receipt=independent(cards,row['zero'],32000,2) if row['zero']<=RECORD else None
                save_result(db,cards,row['zero'],evidence_hashes,'source',row['id'],receipt)
        for row in db.execute('''SELECT a.*,s.cards,s.zero FROM attempt a JOIN scope s ON s.id=a.scope
                                ORDER BY a.turn'''):
            result=row['result']
            prefix=cards_of(row)
            if result.startswith(('exact-completion:','independently-verified-improvement:')):
                cards=legacy.completion(prefix,int(row['cursor']))
                zero=int(result.rsplit(':',1)[1])
            elif result=='exact-existing-or-deferred' and len(prefix)==20 and row['zero'] is not None:
                cards=prefix
                zero=row['zero']
            else:continue
            past=json.loads(row['resource'])[0]
            old_hashes=dict(hashes,evaluator=past[1],paytable=past[2])
            assert old_hashes['paytable']==hashes['paytable']
            receipt=independent(cards,zero,32000,2) if zero<RECORD else None
            save_result(db,cards,zero,old_hashes,'historical-attempt',row['turn'],receipt)
        db.execute("INSERT INTO metadata VALUES('result_schema_v1','1')")

READY = """(s.status='open' OR (s.status='deferred' AND
             (s.last_resource IS NULL OR s.last_resource!=?)))"""

def choose(db, resource, turn, existing_only, exploratory=False):
    subset = "AND s.status='deferred' AND s.source_id IS NOT NULL" if existing_only else ''
    if exploratory:subset+=" AND s.id LIKE 'explore:%'"
    # Every fourth turn serves the globally oldest eligible scope.
    order = ("s.last_turn,s.id" if turn%4==0 else
             "coalesce(l.last_turn,0), s.last_turn, q.depth DESC, s.zero, s.id")
    if turn%4==2 and not existing_only:
        order="(s.status!='open'), "+order
    return db.execute(f"""SELECT s.*,q.lane FROM scope s JOIN scheduling q ON q.scope=s.id
                         LEFT JOIN lane_service l ON l.lane=q.lane
                         WHERE {READY} {subset} ORDER BY {order} LIMIT 1""",(resource,)).fetchone()

def defer_child(db, row, cards, turn, resource):
    id=f"{row['id']}@{row['cursor']}"
    db.execute('''INSERT INTO scope(id,kind,cards,cursor,stop,status,last_turn,last_resource,parent)
                  VALUES(?,?,?,?,?,?,?,?,?)''',
               (id,'terminal',dump(cards),'0','1','deferred',turn,resource,row['id']))
    schedule(db,id,cards,'terminal')
    return id

def run(db, steps, states, seconds, existing_only, hashes, batch=1, capture=False, exploratory=False):
    resource=dump([hashes,legacy.sha(Path(__file__)),states,seconds])
    totals=Counter()
    pending_totals=Counter()
    for i in range(steps):
        if not db.in_transaction:
            try:retention.disk(DATABASE)
            except OSError as e:
                totals['storage_stop']=1
                print(str(e),file=sys.stderr)
                break
            db.execute('BEGIN IMMEDIATE')
        try:
            turn=db.execute('SELECT coalesce(max(turn),0)+1 FROM attempt').fetchone()[0]
            row=choose(db,resource,turn,existing_only,exploratory)
            if row is None:
                db.commit()
                totals.update(pending_totals)
                break
            current=Counter()
            cursor=int(row['cursor'])
            prefix=cards_of(row)
            retry=row['status']=='deferred'
            first_exploration=row['id'].startswith('explore:') and row['last_turn']==0
            current['exploration_first_attempts']+=int(first_exploration)
            cards=prefix if retry else legacy.completion(prefix,cursor)
            current['generated']+=int(not retry)
            previous_best=db.execute('SELECT min(zero) FROM leaderboard').fetchone()[0]
            db.execute("UPDATE scope SET status='active' WHERE id=?",(row['id'],))
            z=row['zero']
            pending=False
            detail=None
            try:
                if capture:
                    detail=retention.evaluate(sys.modules[__name__],cards,states,seconds)
                    value=detail[0][20]
                else:value=legacy.evaluate(cards,states,seconds)
            except Limit:
                pending=True
                result='count-deferred'
            else:
                receipt=None
                if len(cards)==20:
                    if value<RECORD:
                        try:receipt=independent(cards,value,states,seconds)
                        except Limit:pending=True
                    inserted=save_result(db,cards,value,hashes,'worker',turn,receipt)
                    current['new_unique_completed']+=inserted
                    current['new_records']+=int(receipt is not None and value<min(RECORD,previous_best if previous_best is not None else RECORD))
                    current['completed_exact']+=1
                    if pending:current['verification_deferred']+=1
                else:
                    current['partial_exact']+=1
                result=f'exact-{"retry" if retry else "completion"}:{value}'
                if pending:result=f'exact-count-verification-deferred:{value}'
                if retry:z=value
            if retry:
                if pending:
                    status='deferred'
                    current['new_deferrals' if first_exploration else 'still_deferred']+=1
                else:
                    status='open' if row['kind']=='prefix' else 'resolved'
                    current['recovered_deferred']+=int(not first_exploration)
                    current['recovered_completed']+=int(not first_exploration and len(cards)==20)
            elif pending:
                child=defer_child(db,row,cards,turn,resource)
                current['new_deferrals']+=1
                result+=':'+child
            if not retry:
                cursor+=1
                status='open' if cursor<int(row['stop']) else 'scanned'
                current['cursor_advances']+=1
            db.execute('''UPDATE scope SET cursor=?,status=?,last_turn=?,last_resource=?,zero=? WHERE id=?''',
                       (str(cursor),status,turn,resource,z,row['id']))
            db.execute('INSERT INTO attempt VALUES(?,?,?,?,?)',(turn,row['id'],row['cursor'],resource,result))
            if detail is not None:
                db.execute('INSERT INTO evaluation_detail VALUES(?,?,?,?,?)',
                           (turn,dump(detail[0]),dump(detail[1]),hashes['evaluator'],hashes['paytable']))
            db.execute('INSERT INTO lane_service VALUES(?,?) ON CONFLICT(lane) DO UPDATE SET last_turn=excluded.last_turn',
                       (row['lane'],turn))
            pending_totals.update(current)
            pending_totals['attempts']+=1
            if (i+1)%batch==0 or i+1==steps:
                db.commit()
                totals.update(pending_totals)
                pending_totals.clear()
        except sqlite3.OperationalError as error:
            db.rollback()
            if getattr(error,'sqlite_errorcode',None)!=sqlite3.SQLITE_FULL:raise
            totals['storage_stop']=1
            print('SQLite storage is full. Uncommitted tasks remain at their prior checkpoints.',file=sys.stderr)
            break
        except BaseException:
            db.rollback()
            raise
    return totals

def report(db, totals, filename="latest-run.json"):
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    scope=dict(db.execute('SELECT status,count(*) FROM scope GROUP BY status'))
    for k in ('open','active','deferred','certified','resolved','scanned'):scope.setdefault(k,0)
    eligible=db.execute(f"""SELECT count(*) FROM scope s JOIN scheduling q ON q.scope=s.id
                             WHERE {READY}""",('future-resource-signature',)).fetchone()[0]
    assert eligible==scope['open']+scope['deferred']
    best=[dict(r) for r in db.execute('''SELECT id,cards,zero,probability,incidences,support,verification
                                      FROM leaderboard ORDER BY zero,id LIMIT 12''')]
    counts={k:totals[k] for k in ('attempts','generated','exploration_first_attempts','completed_exact','partial_exact','recovered_deferred',
            'recovered_completed','verification_deferred','new_deferrals','still_deferred','new_unique_completed','new_records','cursor_advances','storage_stop')}
    data=dict(invocation=counts,scope=scope,unresolved=eligible,reachable_under_new_resources=eligible,
              completed=db.execute('SELECT count(*) FROM completed').fetchone()[0],
              exact_evaluation_rows=db.execute('SELECT count(*) FROM evaluation').fetchone()[0],
              unresolved_canonical=db.execute('SELECT count(*) FROM completed WHERE canonical IS NULL').fetchone()[0],
              exploratory_scopes=db.execute("SELECT count(*) FROM scope WHERE id LIKE 'explore:%'").fetchone()[0],
              pattern_versions=db.execute('SELECT count(*) FROM pattern_version').fetchone()[0],
              disk_free_bytes=retention.shutil.disk_usage(OUT).free,
              lifetime_generated=sum(int(r[0]) for r in db.execute('SELECT cursor FROM scope')),
              attempts_total=db.execute('SELECT count(*) FROM attempt').fetchone()[0],
              integrity='ok',foreign_key_errors=0,benchmark=RECORD,best_zero=best[0]['zero'] if best else None,
              leaderboard=best)
    tmp=OUT/'latest-run.tmp'
    tmp.write_text(json.dumps(data,indent=2)+'\n')
    tmp.replace(OUT/filename)
    print(json.dumps({k:v for k,v in data.items() if k!='leaderboard'},indent=2))
    return data

def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('audit')
    work=sub.add_parser('work')
    work.add_argument('steps',type=int)
    work.add_argument('states',type=int)
    work.add_argument('seconds',type=float)
    work.add_argument('--existing-only',action='store_true')
    work.add_argument('--batch',type=int,default=4)
    work.add_argument('--explore-only',action='store_true')
    args=parser.parse_args()
    if args.action=='work' and min(args.steps,args.states,args.seconds,args.batch)<=0:parser.error('Work budgets must be positive.')
    if not DATABASE.is_file():parser.error('Corrected continuation snapshot is missing.')
    with connect(DATABASE) as db:
        hashes=fingerprint()
        compatible(db,hashes)
        retention.disk(DATABASE)
        migrate(db,hashes)
        retention.migrate(db)
        first=db.execute('SELECT coalesce(max(turn),0) FROM attempt').fetchone()[0]
        totals=run(db,args.steps,args.states,args.seconds,args.existing_only,hashes,args.batch,capture=True,exploratory=args.explore_only) if args.action=='work' else Counter()
        if args.action=='work':
            last=db.execute('SELECT coalesce(max(turn),0) FROM attempt').fetchone()[0]
            with db:
                db.execute('INSERT INTO invocation(first_turn,last_turn,counts) VALUES(?,?,?)',
                           (first+1 if last>first else None,last if last>first else None,dump(totals)))
        report(db,totals,'latest-run.json' if args.action=='work' else 'latest-audit.json')

if __name__=='__main__':main()
