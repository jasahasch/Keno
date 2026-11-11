"""Bounded progressive any-payout search with distinct-card enforcement."""
from pathlib import Path
import sys
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent/'reverse-incidence'))
from reverse_search import CAP,D,RECORD,Strategy,Budget,Limit,TABLE,canonical,comb,verify,Counter,Random,json
from unrestricted_resolution.zero import deletion,frontier
from types import SimpleNamespace
from fractions import Fraction

def save(name,data):
    p=OUT/name
    tmp=p.with_suffix('.tmp')
    tmp.write_text(json.dumps(data,indent=2)+'\n')
    tmp.replace(p)

def metrics(cards):
    degree=Counter(v for c in cards for v in c)
    return sum(map(len,cards)),len(degree),max(degree.values())

def check(cards):
    assert len(set(cards))==len(cards)
    assert all(2<=len(c)<=10 and tuple(sorted(set(c)))==c and all(1<=v<=80 for v in c) for c in cards)

def count(cards):
    st=SimpleNamespace(cards=cards)
    try:return deletion(st,TABLE,Budget(1000,.09))[0][20]
    except Limit:return frontier(st,TABLE,Budget(3500,.06))[0][20]

def evaluate(proposals,n):
    rows=[]
    seen=set()
    stats=Counter()
    for cards,kind in proposals:
        stats['proposed']+=1
        if len(set(cards))!=n:
            stats['identical_card_rejections']+=1
            continue
        check(cards)
        st=Strategy(cards) if n>1 else None
        t,s,d=metrics(cards)
        r=dict(cards=cards,method=kind,incidences=t,support=s,max_owner=d)
        try:key=canonical(st,240)['encoding'] if st else str(len(cards[0]))
        except Limit:
            stats['canonical_deferred']+=1
            r['status']='canonical-deferred'
            rows.append(r)
            continue
        if key in seen:
            stats['relabeling_duplicates']+=1
            continue
        seen.add(key)
        r['canonical']=key
        try:
            r['zero']=count(cards)
            r['status']='exact'
        except Limit:r['status']='count-deferred'
        stats[r['status']]+=1
        rows.append(r)
    return rows,stats

def rank(rows):
    return sorted((r for r in rows if r['status']=='exact'),key=lambda r:r['zero'])

def retain(rows):
    # Reserve separate slots for overlap density, sizes, and used-number degree.
    ordered=rank(rows)
    selected={r['canonical']:r for r in ordered[:5]}
    buckets=set()
    for r in ordered:
        n=len(r['cards'])
        d=r['max_owner']
        t=r['incidences']
        gap=t-r['support']
        key=(min(3,gap*2//n),min(3,d-1),t//n,len(set(map(len,r['cards'])))>1)
        if key not in buckets:
            buckets.add(key)
            selected.setdefault(r['canonical'],r)
        if len(selected)>=19:break
    return list(selected.values())

def proposals(beam,rng):
    for row in beam:
        cards=tuple(map(tuple,row['cards']))
        used=sorted(set(v for c in cards for v in c))
        fresh=sorted(set(range(1,81))-set(used))
        degree=Counter(v for c in cards for v in c)
        for size in range(2,11):
            yield cards+(tuple(sorted(rng.sample(range(1,81),size))),),'whole-universe'
            if len(fresh)>=size:
                yield cards+(tuple(fresh[:size]),),'fresh'
            for j in (1,2,max(1,size-1),size):
                if len(used)<j or size<j or len(fresh)<size-j:continue
                chosen=rng.sample(used,j)
                yield cards+(tuple(sorted(chosen+fresh[:size-j])),),'controlled-overlap'
            parent=rng.choice(cards)
            kept=rng.sample(parent,min(len(parent),max(1,size-2)))
            pool=sorted(set(range(1,81))-set(kept))
            yield cards+(tuple(sorted(kept+rng.sample(pool,size-len(kept)))),),'parent-overlap'
            hotspot=sorted(used,key=lambda v:(-degree[v],v))[:max(size+3,10)]
            if len(hotspot)>=size:
                yield cards+(tuple(sorted(rng.sample(hotspot,size))),),'high-order'

def edits(beam,rng):
    for r in beam:
        old=tuple(map(tuple,r['cards']))
        for step in range(50):
            slots=rng.sample(range(20),rng.choice((2,2,3,4,6)))
            cards=list(old)
            for i in slots:
                if step%3==0:
                    cards[i]=tuple(sorted(rng.sample(range(1,81),rng.randint(2,10))))
                    continue
                card=set(old[i])
                if step%3==1 and len(card)<10:
                    card.add(rng.choice(sorted(set(range(1,81))-card)))
                else:
                    missing=sorted(set(range(1,81))-card)
                    card.remove(rng.choice(sorted(card)))
                    card.add(rng.choice(missing))
                cards[i]=tuple(sorted(card))
            if sum((Counter(old)-Counter(cards)).values())>=2:yield tuple(cards),'coordinated'

def verify_best(rows):
    leaders={}
    for r in rank(rows):
        cards=tuple(map(tuple,r['cards']))
        check(cards)
        keys=[r['method']]
        if r['max_owner']>1:keys.append('overlapping')
        if len(set(map(len,cards)))>1:keys.append('mixed')
        keys.append('overall')
        if r['zero']<RECORD:keys.append(r['canonical'])
        if all(k in leaders for k in keys):continue
        try:v=verify(Strategy(cards),r['zero'])
        except Limit:continue
        for k in keys:leaders.setdefault(k,dict(r,verified=v))
    return leaders

def main():
    rng=Random(2301527)
    ledger=[]
    beam=[]
    for n in range(1,21):
        if n==1:
            candidates=(((tuple(range(1,s+1)),),'single-size') for s in range(2,11))
        elif n==2:
            candidates=(((tuple(range(1,a+1)),tuple(range(1,k+1))+tuple(range(a+1,a+b-k+1))),
                         'two-card-geometry') for a in range(2,11) for b in range(a,11) for k in range(a+1))
        else:candidates=proposals(beam,rng)
        rows,stats=evaluate(candidates,n)
        beam=retain(rows)
        best=rank(rows)[0]
        ledger.append(dict(cards=n,**stats,retained=len(beam),best_zero=best['zero'],
                           scope='exhaustive up to relabeling' if n<=2 else 'bounded beam; all ungenerated and unretained extensions stay unresolved'))
        save(f'stage-{n:02d}.json',dict(rows=rows,beam=beam))
        save('ledger.json',ledger)
        print(n,dict(stats),'best',best['zero'],flush=True)
    edited,stats=evaluate(edits(beam,rng),20)
    final_keys={r.get('canonical') for r in rows}
    stats['also_in_final_stage']=sum(r.get('canonical') in final_keys for r in edited if 'canonical' in r)
    save('coordinated.json',dict(rows=edited,stats=stats))
    save('leaders.json',verify_best(rows+edited))

if __name__=='__main__':main()
