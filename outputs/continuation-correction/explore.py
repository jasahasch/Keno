"""Queue independent twenty-card layouts and coordinated versions in the live worker."""
from collections import Counter
from random import Random
import hashlib
import continuity as w
import retention as r

def generate(db, seed, rounds):
    rng=Random(seed)
    proposals=[]
    parents=db.execute("""SELECT id,cards FROM leaderboard WHERE zero>? AND max_owner>1
                          ORDER BY zero,id LIMIT 36""",(w.RECORD,)).fetchall()
    for _ in range(rounds):
        for mode in ('whole-universe','dense','hub','mixed-sparse','large-neighborhood'):
            parent=None
            if mode=='large-neighborhood':
                row=rng.choice(parents)
                parent=row['id']
                old=w.cards_of(row)
                cards=list(old)
                slots=rng.sample(range(20),rng.choice((2,3,5,8)))
                for i in slots:
                    card=set(cards[i])
                    if rng.randrange(3)==0:
                        card=set(rng.sample(range(1,81),rng.randint(2,10)))
                    else:
                        other=set(cards[rng.randrange(20)])
                        choices=sorted(other-card) or sorted(set(range(1,81))-card)
                        if len(card)==10 or rng.randrange(2):card.remove(rng.choice(sorted(card))) if len(card)>2 else None
                        if len(card)<10:card.add(rng.choice(choices))
                    cards[i]=tuple(sorted(card))
                changes={chr(65+i):cards[i] for i in slots if cards[i]!=old[i]}
                if len(changes)<2:continue
            else:
                pool=rng.sample(range(1,81),rng.randint(12,38)) if mode=='dense' else list(range(1,81))
                hub=rng.sample(pool,8)
                cards=[]
                used=set()
                for _ in range(20):
                    size=rng.randint(2,10) if mode!='mixed-sparse' else rng.choice((3,4,4,5,6,7))
                    for _ in range(100):
                        if mode=='hub':
                            core=set(rng.sample(hub,rng.randint(1,min(4,size))))
                            candidate=tuple(sorted(core|set(rng.sample(sorted(set(pool)-core),size-len(core)))))
                        elif mode=='mixed-sparse':
                            fresh=sorted(set(pool)-used)
                            count=min(len(fresh),rng.randint(max(0,size-2),size))
                            first=set(rng.sample(fresh,count))
                            candidate=tuple(sorted(first|set(rng.sample(sorted(set(pool)-first),size-count))))
                        else:candidate=tuple(sorted(rng.sample(pool,size)))
                        if candidate not in cards:break
                    else:raise RuntimeError('Unable to generate distinct cards.')
                    cards.append(candidate)
                    used.update(candidate)
            cards=tuple(cards)
            if len(set(cards))!=20:continue
            w.check(cards)
            proposals.append((mode,cards,parent,changes if parent is not None else None))
    stats=Counter(proposed=len(proposals))
    with db:
        db.execute("""CREATE TABLE IF NOT EXISTS exploration(
                    scope TEXT PRIMARY KEY REFERENCES scope, mode TEXT NOT NULL,
                    seed INTEGER NOT NULL, parent INTEGER REFERENCES completed)""")
        known={row[0] for row in db.execute("SELECT canonical FROM completed WHERE canonical IS NOT NULL")}
        for mode,cards,parent,changes in proposals:
            raw=w.dump(cards)
            try:code=w.canonical(w.Strategy(cards),550)['encoding']
            except w.Limit:code=None
            if code and code in known and parent is None:
                stats['equivalent_skipped']+=1
                continue
            # Version observations keep their own lineage, even if their result later deduplicates.
            key=(code or w.dump(sorted(cards))) if parent is None else w.dump([parent,cards])
            id='explore:'+hashlib.sha256(key.encode()).hexdigest()
            if db.execute('SELECT 1 FROM scope WHERE id=?',(id,)).fetchone():
                stats['duplicate_proposal']+=1
                continue
            db.execute("INSERT INTO scope(id,kind,cards,cursor,stop,status) VALUES(?,'terminal',?,'0','1','deferred')",(id,raw))
            w.schedule(db,id,cards,'terminal')
            db.execute('INSERT INTO exploration VALUES(?,?,?,?)',(id,mode,seed,parent))
            if parent is not None:db.execute('INSERT INTO pattern_version VALUES(?,?,?,?)',(id,parent,raw,w.dump(changes)))
            if code:known.add(code)
            stats['queued']+=1
            stats[mode]+=1
    return stats

if __name__=='__main__':
    import sys,json
    with w.connect(w.DATABASE) as db:
        w.compatible(db,w.fingerprint())
        r.disk(w.DATABASE)
        print(json.dumps(generate(db,int(sys.argv[1]),int(sys.argv[2])),indent=2))
