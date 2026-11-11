"""Continue the full-support zero-payout investigation."""
from collections import Counter
from functools import lru_cache
from itertools import combinations, combinations_with_replacement, permutations, product
from pathlib import Path
from random import Random
from math import comb, factorial
import sys

OUT = Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent/'any-payout-expansion'))
from run import CAP, D, TABLE, Strategy, Budget, Limit, compositions, free_law, frontier, make, multiply, verify, json

RECORD = 4**20

def save(name,data):
    (OUT/name).write_text(json.dumps(data,indent=2)+'\n')

def geometries():
    representatives=set()
    edges=list(combinations(range(6),2))
    options=[((0,1,2,3),)]
    options.extend(((0,1,2),e) for e in edges)
    options.extend(combinations_with_replacement(edges,3))
    for regions in options:
        owners=sorted(set().union(*map(set,regions)))
        representatives.add(min(tuple(sorted(tuple(sorted(mapping[i] for i in r)) for r in regions))
                                for p in permutations(range(len(owners)))
                                for mapping in [dict(zip(owners,p))]))
    return sorted(representatives)

@lru_cache(None)
def tails(n,total):
    return tuple(free_law(c) for c in compositions(n,total))

@lru_cache(None)
def envelope(n,total):
    laws=tails(n,total)
    return tuple(min(p[k] if k<len(p) else 0 for p in laws) for k in range(21))

def boundary():
    checkpoint=OUT/'boundary83.json'
    results=json.loads(checkpoint.read_text()) if checkpoint.exists() else []
    done={tuple(map(tuple,r['regions'])) for r in results}
    for regions in geometries():
        if regions in done:continue
        n=1+max(map(max,regions))
        counts=Counter()
        guarantee=D
        if n==6:
            assert regions==((0,1),(2,3),(4,5))
            options=((a+b+c, factorial(3)*2**sum(x!=y for x,y in (a,b,c))
                      // __import__('math').prod(factorial(v) for v in Counter((a,b,c)).values()))
                     for a,b,c in combinations_with_replacement(list(combinations_with_replacement(range(2,11),2)),3))
        else:
            options=((sizes,1) for sizes in product(range(2,11),repeat=n))
        for sizes,weight in options:
            remaining=83-sum(sizes)
            if not 2*(20-n)<=remaining<=10*(20-n):continue
            private=[s-sum(i in r for r in regions) for i,s in enumerate(sizes)]
            if min(private)<0:continue
            counts['marked_profiles']+=1
            counts['represented']+=weight*len(compositions(20-n,remaining))
            local=Counter()
            for bits in product((0,1),repeat=len(regions)):
                poly=(0,)*sum(bits)+(1,)
                for i,p in enumerate(private):
                    c=CAP[sizes[i]]-sum(b for b,r in zip(bits,regions) if i in r)
                    if c<0:break
                    poly=multiply(poly,tuple(comb(p,k) for k in range(min(c,p)+1)))
                else:
                    for k,w in enumerate(poly):
                        if w:local[20-k]+=w
            lower=sum(v*envelope(20-n,remaining)[k] for k,v in local.items())
            if lower<RECORD:
                counts['fallback_profiles']+=1
                lower=min(sum(v*p[k] for k,v in local.items() if k<len(p))
                          for p in tails(20-n,remaining))
            guarantee=min(lower,guarantee)
        results.append(dict(regions=regions,counts=dict(counts),lower=guarantee))
        save('boundary83.json',results)
        print(regions,dict(counts),guarantee,flush=True)

def search():
    rng=Random(773921)
    previous=json.loads((OUT.parent/'any-payout-expansion/search.json').read_text())
    seen={tuple(sorted(map(tuple,r['cards']))) for r in previous}
    rows=[]
    def evaluate(cards,tag):
        key=tuple(sorted(tuple(sorted(c)) for c in cards))
        if key in seen:return
        seen.add(key)
        st=Strategy(key)
        row=dict(cards=key,tag=tag,incidences=sum(map(len,key)),support=len(st.support))
        try:
            p,_=frontier(st,TABLE,Budget(8500,.22))
            row['zero']=p[20]
        except Limit:
            pass
        rows.append(row)
        return row
    # Start with a partition of all 80 numbers, then add shared incidences.
    for total in range(83,201):
        for mode in ('local','hub','global'):
            for _ in range(2):
                sizes=[4]*20
                for _ in range(9):
                    a,b=rng.sample(range(20),2)
                    if sizes[a]>2 and sizes[b]<7:sizes[a]-=1;sizes[b]+=1
                cards=[]
                start=1
                for s in sizes:
                    cards.append(set(range(start,start+s)))
                    start+=s
                hub=rng.sample(range(1,81),8)
                for _ in range(total-80):
                    i=rng.choice([i for i,c in enumerate(cards) if len(c)<10])
                    pool=(cards[(i+1)%20]|cards[(i-1)%20]) if mode=='local' else set(hub) if mode=='hub' else set()
                    cards[i].add(rng.choice(sorted((pool-cards[i]) or (set(range(1,81))-cards[i]))))
                evaluate(cards,mode)
    # Exhaust marked spot profiles on a single pair sharing three to eight numbers
    # while all other cards are disjoint four-spots.
    for k in range(3,9):
        for a,b in combinations_with_replacement(range(2,11),2):
            if min(a,b)>=k and a+b-k==8:
                evaluate(make((a,b)+(4,)*18,((0,1),)*k).cards,'two-card-core')
    save('search.json',rows)
    leaders={}
    for r in sorted((r for r in rows if 'zero' in r),key=lambda r:r['zero']):
        keys=[r['tag'],'all']
        if all(k in leaders for k in keys) and r['zero']>=RECORD:continue
        try: report=verify(Strategy(tuple(r['cards'])),r['zero'])
        except Limit:continue
        for k in keys:leaders.setdefault(k,report)
        if r['zero']<RECORD:leaders[str(r['cards'])]=report
    save('leaders.json',leaders)
    print('search',len(rows),sum('zero' in r for r in rows),[(k,r['zero']) for k,r in leaders.items()],flush=True)

if __name__=='__main__':
    for task in sys.argv[1:]:globals()[task]()
