"""Exact payout-frequency search and incidence-boundary enumeration."""
from collections import Counter
from fractions import Fraction
from functools import lru_cache
from itertools import combinations, combinations_with_replacement
from math import comb
from pathlib import Path
from random import Random
import json
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path[:0] = [str(ROOT),str(ROOT/'spot_strategy_framework')]
from spot_strategy.model import Strategy, Paytable
from unrestricted_resolution.zero import frontier, deletion, Budget, Limit, multiply

TABLE = Paytable(ROOT/'outputs/keno-expanded-paytables.json')
CAP = {s:next(h for h,p in enumerate(TABLE[s]) if p)-1 for s in range(2,11)}
assert CAP == dict(zip(range(2,11), (1,1,1,2,2,2,3,3,4)))
assert all(all(p==0 for p in TABLE[s][:c+1]) and all(p>0 for p in TABLE[s][c+1:])
           for s,c in CAP.items())
D = comb(80,20)

def write(name,data):
    (OUT/name).write_text(json.dumps(data,indent=2)+'\n')

def make(sizes, shared):
    cards = [set() for _ in sizes]
    for v, owners in enumerate(shared,1):
        for i in owners:
            cards[i].add(v)
    v = len(shared)+1
    for c,s in zip(cards,sizes):
        assert len(c)<=s
        count=s-len(c)
        c.update(range(v,v+count))
        v+=count
    assert v<=81
    return Strategy(tuple(tuple(sorted(c)) for c in cards))

def verify(strategy, expected=None):
    a,sa=frontier(strategy,TABLE,Budget(800000,12))
    b,sb=deletion(strategy,TABLE,Budget(300000,12))
    assert a==b and (expected is None or a[20]==expected)
    return dict(cards=strategy.assignments(),spots=list(map(len,strategy.cards)),
                incidences=sum(map(len,strategy.cards)),support=len(strategy.support),
                zero=a[20],frequency=str(Fraction(D-a[20],D)),polynomial=a,methods=[sa,sb])

@lru_cache(None)
def compositions(n,total,lo=2):
    if n==0:
        return [()] if total==0 else []
    if total<lo*n or total>10*n:
        return []
    return [(s,*rest) for s in range(lo,11) for rest in compositions(n-1,total-s,s)]

def boundary():
    # Shared number memberships up to simultaneous permutations of marked cards.
    patterns={81:[((0,1),)],82:[((0,1,2),),((0,1),(0,1)),((0,1),(0,2)),((0,1),(2,3))]}
    results={}
    for total,types in patterns.items():
        for regions in types:
            m=1+max(max(r) for r in regions)
            best=None
            counts=0
            # Visit ordered marked sizes, allowing redundant symmetric instances.
            from itertools import product
            for sizes in product(range(2,11),repeat=m):
                local=Counter()
                private=[s-sum(i in mask for mask in regions) for i,s in enumerate(sizes)]
                if min(private)<0:continue
                for hit in product((0,1),repeat=len(regions)):
                    law=(0,)*sum(hit)+(1,)
                    for i,p in enumerate(private):
                        cap=CAP[sizes[i]]-sum(h for h,r in zip(hit,regions) if i in r)
                        law=multiply(law,tuple(comb(p,k) for k in range(min(p,cap)+1)))
                        if not law:break
                    for k,v in enumerate(law):local[k]+=v
                for rest in compositions(20-m,total-sum(sizes)):
                    counts+=1
                    law=free_law(rest)
                    z=sum(v*law[20-k] for k,v in local.items() if 0<=20-k<len(law))
                    if best is None or z<best[0]:
                        best=z,sizes+rest
            z,sizes=best
            results[str((total,regions))]=dict(covered_representatives_with_redundancy=counts,
                                               best=verify(make(sizes,regions),z))
            write('boundary.json',results)
            print(total,regions,counts,z,flush=True)

@lru_cache(None)
def free_law(sizes):
    if not sizes:return (1,)
    s=sizes[0]
    return multiply(tuple(comb(s,k) for k in range(CAP[s]+1)),free_law(sizes[1:]))

def search():
    rng=Random(91827)
    seen=set()
    rows=[]
    def evaluate(cards,family):
        key=tuple(sorted(tuple(sorted(c)) for c in cards))
        if key in seen:return
        seen.add(key)
        st=Strategy(key)
        row=dict(family=family,cards=key,incidences=sum(map(len,key)),
                 support=len(st.support),unique=len(set(key)),
                 pair_overlap=sum(len(set(a)&set(b)) for a,b in combinations(key,2)))
        try:
            law,stats=frontier(st,TABLE,Budget(6000,.15))
            row.update(zero=law[20],work=stats)
        except Limit:
            row['deferred']=True
        rows.append(row)
        return row

    def profile(total):
        sizes=[2]*20
        for _ in range(total-40):
            sizes[rng.choice([i for i,s in enumerate(sizes) if s<10])]+=1
        return sizes

    # Cyclic interval layouts with varying overlap, independent of record seeds.
    for total in range(40,201):
        for stride in (2,3,4,5,7):
            sizes=profile(total)
            evaluate([[(stride*i+j)%80+1 for j in range(s)] for i,s in enumerate(sizes)],
                     'cyclic-interval')
    # Sample general incidences, including dense support and deliberately copied cards.
    for support in range(2,81):
        for _ in range(4):
            cards=[]
            for i in range(20):
                if cards and rng.randrange(5)==0:
                    cards.append(rng.choice(cards))
                else:
                    cards.append(rng.sample(range(1,support+1),rng.randint(2,min(support,10))))
            evaluate(cards,'general-incidence')
    # Optimize from separate size/support strata using only exact objective counts.
    pools={}
    for r in rows:
        if 'zero' not in r:continue
        key=(r['incidences']//20,r['support']//20)
        if key not in pools or r['zero']<pools[key]['zero']:pools[key]=r
    for seed in pools.values():
        best=seed
        for _ in range(25):
            cards=list(best['cards'])
            for i in rng.sample(range(20),rng.choice((1,1,2,4))):
                card=list(cards[i])
                mode=rng.randrange(5)
                if mode==0:
                    card=list(rng.choice(cards))
                elif mode==1:
                    card=rng.sample(range(1,81),rng.randint(2,10))
                elif mode==2 and len(card)<10:
                    card.append(rng.choice(list(set(range(1,81))-set(card))))
                elif mode==3 and len(card)>2:
                    card.remove(rng.choice(card))
                else:
                    card.remove(rng.choice(card))
                    card.append(rng.choice(list(set(range(1,81))-set(card))))
                cards[i]=card
            r=evaluate(cards,'exact-guided-edits')
            if r and 'zero' in r and r['zero']<best['zero']:best=r
    write('search.json',rows)
    leaders={}
    ranked=sorted((r for r in rows if 'zero' in r),key=lambda r:r['zero'])
    for r in ranked:
        categories=[r['family'],'any', 'repeated' if r['unique']<20 else 'distinct']
        if r['incidences']>100:categories.append('above-100')
        if r['support']==80:categories.append('support-80')
        if r['zero']<4**20:categories.append(str(r['cards']))
        needed=[c for c in categories if c not in leaders]
        if not needed:continue
        try: result=verify(Strategy(tuple(r['cards'])),r['zero'])
        except Limit:continue
        for k in needed:leaders[k]=result
    write('leaders.json',leaders)
    print(len(rows),len(ranked),[(k,v['zero']) for k,v in leaders.items()],flush=True)

if __name__=='__main__':
    for task in sys.argv[1:]:globals()[task]()
