from pathlib import Path
import sys
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent/'any-payout-expansion-2'))
from scan import *
OUT=Path(__file__).resolve().parent
from unrestricted_resolution.incidence import canonical
from itertools import combinations as choose
from math import prod
def save(name,obj):
    (OUT/name).write_text(json.dumps(obj,indent=2)+'\n')

def partitions(n,lo=1):
    if not n:yield ()
    for k in range(lo,n+1):
        for rest in partitions(n-k,k):yield (k,)+rest

def labels(edges):
    ids={}
    return tuple(tuple(ids.setdefault(i,len(ids)) for i in edge) for edge in edges)

def shapes(excess):
    # Extend normalized geometries one shared number at a time.
    result=set()
    for parts in partitions(excess):
        stage={()}
        for part in parts:
            nxt=set()
            for shape in stage:
                n=1+max(map(max,shape),default=-1)
                for take in range(min(n,part+1)+1):
                    for edge in choose(range(n),take):
                        nxt.add(labels(shape+(edge+tuple(range(n,n+part+1-take)),)))
            stage=nxt
        for shape in stage:
            n=1+max(map(max,shape))
            result.add(min(tuple(sorted(tuple(sorted(p[i] for i in e)) for e in shape))
                           for p in permutations(range(n))))
    return sorted(result)

def components_of(shape):
    todo=list(shape)
    while todo:
        group=[todo.pop()]
        while True:
            used=set().union(*map(set,group))
            more=[e for e in todo if used.intersection(e)]
            if not more:break
            for e in more:todo.remove(e)
            group+=more
        yield labels(tuple(sorted(group)))

@lru_cache(None)
def local_profiles(shape):
    n=1+max(map(max,shape))
    permutations_safe=[p for p in permutations(range(n))
                       if tuple(sorted(tuple(sorted(p[i] for i in e)) for e in shape))==tuple(sorted(tuple(sorted(e)) for e in shape))]
    profiles=set()
    for sizes in product(range(2,11),repeat=n):
        if any(tuple(sizes[i] for i in p)<sizes for p in permutations_safe):continue
        private=[s-sum(i in r for r in shape) for i,s in enumerate(sizes)]
        if min(private)<0:continue
        poly=[0]*21
        for bits in product((0,1),repeat=len(shape)):
            p=(0,)*sum(bits)+(1,)
            for i,v in enumerate(private):
                cap=CAP[sizes[i]]-sum(b for b,e in zip(bits,shape) if i in e)
                if cap<0:break
                p=multiply(p,tuple(comb(v,k) for k in range(min(cap,v)+1)))
            else:
                for k,w in enumerate(p):poly[k]+=w
        while not poly[-1]:poly.pop()
        profiles.add((sum(sizes),tuple(poly)))
    return tuple(sorted(profiles))

def boundary(name='boundary84.json'):
    total=84
    file=OUT/name
    rows=json.loads(file.read_text()) if file.exists() else []
    done={tuple(map(tuple,r['shape'])) for r in rows}
    for shape in shapes(4):
        if shape in done:continue
        groups=Counter(components_of(shape))
        n=1+max(map(max,shape))
        families=[combinations_with_replacement(local_profiles(g),m) for g,m in groups.items()]
        best=D
        checked=fallback=0
        for chunks in product(*families):
            chunks=sum(chunks,())
            remain=total-sum(s for s,_ in chunks)
            if not 2*(20-n)<=remain<=10*(20-n):continue
            checked+=1
            poly=(1,)
            for _,p in chunks:poly=multiply(poly,p)
            terms=[(20-k,v) for k,v in enumerate(poly) if v]
            lower=sum(v*envelope(20-n,remain)[k] for k,v in terms)
            if lower<RECORD:
                fallback+=1
                lower=min(sum(v*p[k] for k,v in terms if k<len(p)) for p in tails(20-n,remain))
            best=min(best,lower)
        rows.append(dict(shape=shape,distinct_component_profile_tuples=checked,fallback=fallback,lower=best))
        save(name,rows)
        print(len(rows),shape,checked,best,flush=True)

def search():
    rng=Random(912413)
    prior=set()
    for folder,name in [('any-payout-expansion','search.json'),('any-payout-expansion-2','unique-search.json')]:
        for r in json.loads((OUT.parent/folder/name).read_text()):
            try:prior.add(canonical(Strategy(tuple(map(tuple,r['cards']))),500)['encoding'])
            except Limit:pass
    rows=[]
    stats=Counter()
    def evaluate(cards,mode):
        stats['generated']+=1
        st=Strategy(tuple(tuple(sorted(c)) for c in cards))
        try:code=canonical(st,500)['encoding']
        except Limit:
            stats['canonical_deferred']+=1
            return
        if code in prior:
            stats['isomorphic_skipped']+=1
            return
        prior.add(code)
        r=dict(cards=st.cards,mode=mode,incidences=sum(map(len,cards)),support=len(st.support))
        try:
            p,_=frontier(st,TABLE,Budget(2300,.07))
            r['zero']=p[20]
        except Limit:
            try:
                from unrestricted_resolution.zero import deletion
                p,_=deletion(st,TABLE,Budget(320,.045))
                r['zero']=p[20]
            except Limit:pass
        rows.append(r)
        return r
    # Vary the number of active cards in each component, with full support.
    for t in range(84,201):
        for block in (2,3,4,5,7,10,20):
            for rep in range(5):
                slots=list(range(20))
                rng.shuffle(slots)
                owners=[slots[i:i+block] for i in range(0,20,block)]
                deck=list(range(1,81))
                rng.shuffle(deck)
                sizes=[4]*20
                for _ in range(13):
                    a,b=rng.sample(slots,2)
                    if sizes[a]>2 and sizes[b]<8:sizes[a]-=1;sizes[b]+=1
                cards=[]
                start=0
                for s in sizes:
                    cards.append(set(deck[start:start+s]))
                    start+=s
                neighborhoods={i:set().union(*(cards[j] for j in g)) for g in owners for i in g}
                for _ in range(t-80):
                    eligible=[i for i in slots if len(cards[i])<10 and neighborhoods[i]-cards[i]]
                    if not eligible:
                        eligible=[i for i in slots if len(cards[i])<10]
                    i=rng.choice(eligible)
                    cards[i].add(rng.choice(sorted((neighborhoods[i]-cards[i]) or (set(deck)-cards[i]))))
                evaluate(cards,'block-'+str(block))
        if t%10==0:
            save('search.json',rows)
            save('coverage.json',stats)
            print(t,len(rows),sum('zero' in r for r in rows),flush=True)
    # Exhaust pairs of overlapping cards on eight numbers beside eighteen four-spots.
    for k in range(4,9):
        for a,b in combinations_with_replacement(range(2,11),2):
            if a>=k and a+b-k==8:
                evaluate(make((a,b)+(4,)*18,((0,1),)*k).cards,'pair-core')
    seeds={}
    for r in sorted((r for r in rows if 'zero' in r),key=lambda r:r['zero']):
        seeds.setdefault((r['mode'],r['incidences']//10),r)
    for seed in seeds.values():
        best=seed
        for _ in range(10):
            cards=[set(c) for c in best['cards']]
            i,j=rng.sample(range(20),2)
            a=cards[i]-cards[j]
            b=cards[j]-cards[i]
            if not a or not b:continue
            x,y=rng.choice(sorted(a)),rng.choice(sorted(b))
            cards[i].remove(x)
            cards[j].remove(y)
            cards[i].add(y)
            cards[j].add(x)
            r=evaluate(cards,'cross-component-swaps')
            if r and 'zero' in r and r['zero']<best['zero']:best=r
    save('search.json',rows)
    save('coverage.json',stats)
    leaders={}
    for r in sorted((r for r in rows if 'zero' in r),key=lambda r:r['zero']):
        if r['mode'] in leaders and r['zero']>=RECORD:continue
        try:v=verify(Strategy(r['cards']),r['zero'])
        except Limit:continue
        leaders.setdefault(r['mode'],v)
        if r['zero']<RECORD:leaders[str(r['cards'])]=v
    save('leaders.json',leaders)

if __name__=='__main__':
    for task in sys.argv[1:]:globals()[task]()
