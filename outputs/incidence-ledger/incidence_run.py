"""Persistent coverage ledger and exact incidence exploration."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'any-payout-expansion-3'))
import extend as ex
from extend import (CAP,D,RECORD,Strategy,Budget,Limit,TABLE,canonical,comb,compositions,
                    envelope,tails,multiply,make,verify,partitions,product,permutations,
                    combinations_with_replacement,Counter,Random,lru_cache,json)
from unrestricted_resolution.zero import deletion, frontier
from itertools import combinations

def save(name,value):
    path=HERE/name
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,indent=2)+'\n')
    tmp.replace(path)

def code(shape):
    # Sort card slots by their membership signatures for each column order.
    best=None
    for ordered in permutations(shape):
        vertices=set().union(*map(set,ordered))
        masks=sorted(sum(1<<j for j,e in enumerate(ordered) if v in e) for v in vertices)
        key=tuple(tuple(i for i,m in enumerate(masks) if m>>j&1) for j in range(len(ordered)))
        if best is None or key<best:best=key
    return best

def shapes85():
    source=json.loads((HERE.parent/'any-payout-expansion-3'/'audit84.json').read_text())
    out=set()
    for row in source:
        s=tuple(map(tuple,row['shape']))
        n=1+max(map(max,s))
        for a,b in combinations(range(n+2),2):
            if b==n+1 and a<n:continue
            out.add(code(s+((a,b),)))
        for j,e in enumerate(s):
            for i in set(range(n+1))-set(e):
                out.add(code(s[:j]+(e+(i,),)+s[j+1:]))
    return sorted(out)

@lru_cache(None)
def reduced(group):
    # A coefficientwise smaller law suffices for a universal lower bound.
    by_sum={}
    for s,p in ex.local_profiles(group):
        by_sum.setdefault(s,[]).append(p)
    result=[]
    for s,polys in by_sum.items():
        for p in polys:
            if not any(q!=p and len(q)<=len(p) and all(x<=y for x,y in zip(q,p)) for q in polys):
                result.append((s,p))
    return tuple(result)

def boundary():
    file=HERE/'boundary85.json'
    rows=json.loads(file.read_text()) if file.exists() else []
    seen={tuple(map(tuple,r['shape'])) for r in rows}
    for shape in shapes85():
        if shape in seen:continue
        groups=Counter(code(g) for g in ex.components_of(shape))
        n=1+max(map(max,shape))
        # Split high-work branches out explicitly so the bounded run never silently drops them.
        if n>4:
            rows.append(dict(shape=shape,status='unresolved-audit-width'))
            save(file.name,rows)
            continue
        opts=[tuple(combinations_with_replacement(reduced(g),m)) for g,m in groups.items()]
        checked=0
        best=D
        for choices in product(*opts):
            profiles=sum(choices,())
            rem=85-sum(s for s,_ in profiles)
            if not 2*(20-n)<=rem<=10*(20-n):continue
            p=(1,)
            for _,q in profiles:p=multiply(p,q)
            z=sum(v*envelope(20-n,rem)[20-k] for k,v in enumerate(p))
            if z<RECORD:
                z=min(sum(v*q[20-k] for k,v in enumerate(p) if 20-k<len(q))
                      for q in tails(20-n,rem))
            best=min(best,z)
            checked+=1
        rows.append(dict(shape=shape,status='bound-ready' if best>=RECORD else 'unresolved-bound',
                         lower=best,profiles=checked))
        save(file.name,rows)
        if len(rows)%10==0:print('85 geometry',len(rows),flush=True)

def saturation(cards,rng):
    cards=[set(c) for c in cards]
    missing=set(range(1,81))-set().union(*cards)
    while missing:
        counts=Counter(v for c in cards for v in c)
        i,v=rng.choice([(i,v) for i,c in enumerate(cards) for v in sorted(c) if counts[v]>1])
        cards[i].remove(v)
        cards[i].add(min(missing))
        missing.remove(min(missing))
    return cards

def search():
    rng=Random(519871)
    seen=set()
    old=[('any-payout-expansion','search.json'),('any-payout-expansion-2','unique-search.json'),
         ('any-payout-expansion-3','search.json'),('any-payout-expansion-3','core-search.json')]
    for folder,name in old:
        for row in json.loads((HERE.parent/folder/name).read_text()):
            try:seen.add(canonical(Strategy(tuple(map(tuple,row['cards']))),250)['encoding'])
            except Limit:pass
    counts=Counter()
    checkpoint=HERE/'candidates.json'
    rows=json.loads(checkpoint.read_text()) if checkpoint.exists() else []
    through=max((r['incidences'] for r in rows),default=84)
    for row in rows:
        if row['status']=='canonical-deferred':continue
        seen.add(canonical(Strategy(tuple(map(tuple,row['cards']))),500)['encoding'])
    def eval_cards(cards,mode):
        st=Strategy(tuple(tuple(sorted(c)) for c in cards))
        s=sum(map(len,st.cards))
        if s<=through:return
        owners=Counter(v for c in st.cards for v in c)
        r=dict(mode=mode,incidences=s,support=len(owners),max_owner=max(owners.values()),
               excess=sorted(n-1 for n in owners.values() if n>1),cards=st.cards)
        try:k=canonical(st,500)['encoding']
        except Limit:
            counts['canonical_deferred']+=1
            r['status']='canonical-deferred'
            rows.append(r)
            return
        if k in seen:
            counts['duplicate']+=1
            return
        seen.add(k)
        try:
            p,_=deletion(st,TABLE,Budget(1050,.09))
            r.update(zero=p[20],status='exact')
        except Limit:
            try:
                p,_=frontier(st,TABLE,Budget(3300,.06))
                r.update(zero=p[20],status='exact')
            except Limit:r['status']='count-deferred'
        rows.append(r)
    for total in range(85,201):
        for j in range(14):
            if j<7:
                # Direct high-order memberships followed by private allocation.
                cards=[set() for _ in range(20)]
                excess=total-80
                number=1
                while excess and number<=80:
                    eligible=[i for i,c in enumerate(cards) if len(c)<9]
                    if len(eligible)<2:break
                    d=rng.randint(2,min(excess+1,len(eligible),2+j*2))
                    for i in rng.sample(eligible,d):cards[i].add(number)
                    number+=1
                    excess-=d-1
                if excess:
                    if total>through:counts['infeasible_generator_attempt']+=1
                    continue
                while number<=80:
                    low=[i for i,c in enumerate(cards) if len(c)<2]
                    pick=low or [i for i,c in enumerate(cards) if len(c)<10]
                    cards[rng.choice(pick)].add(number)
                    number+=1
                if min(map(len,cards))>=2:eval_cards(cards,'direct-membership')
            else:
                sizes=[2]*20
                for _ in range(total-40):
                    i=rng.choice([i for i,s in enumerate(sizes) if s<10])
                    sizes[i]+=1
                support=rng.randint(max(sizes),80)
                cards=[rng.sample(range(1,support+1),s) for s in sizes]
                eval_cards(saturation(cards,rng),'saturated-arbitrary')
        if total%10==0:
            save('candidates.json',rows)
            print(total,len(rows),flush=True)
    save('candidates.json',rows)
    save('search-counts.json',counts)
    leaders={}
    for r in sorted((r for r in rows if r['status']=='exact'),key=lambda r:r['zero']):
        keys=[r['mode'], 'high-order' if r['max_owner']>=3 else 'pair-only']
        if r['zero']<RECORD:keys.append(str(r['cards']))
        if all(k in leaders for k in keys):continue
        try:v=verify(Strategy(r['cards']),r['zero'])
        except Limit:continue
        for k in keys:leaders.setdefault(k,v)
    save('leaders.json',leaders)

if __name__=='__main__':
    for task in sys.argv[1:]:globals()[task]()
