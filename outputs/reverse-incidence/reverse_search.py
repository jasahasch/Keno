"""Reverse coverage counting and outcome-guided coordinated changes."""
from pathlib import Path
import sys
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent/'incidence-ledger'))
from incidence_run import CAP,D,RECORD,Strategy,Budget,Limit,TABLE,canonical,comb,verify,Counter,Random,json
from unrestricted_resolution.zero import frontier,deletion
from spot_strategy.canonical import components
from types import SimpleNamespace
from collections import defaultdict
from itertools import combinations_with_replacement
from functools import lru_cache

def save(name,data):
    path=OUT/name
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data,indent=2)+'\n')
    tmp.replace(path)

@lru_cache(None)
def mask(card):
    return sum(1<<(v-1) for v in card)

def count(cards,method=deletion):
    # The union represents simultaneous zero constraints, not a playable card count.
    constraints=SimpleNamespace(cards=tuple(sorted(set(cards))))
    return method(constraints,TABLE,Budget(32000,1))[0][20]

def change(old,new,initial=None):
    before=count(old) if initial is None else initial
    after=count(new)
    joint=count(old+new)
    assert 0<=joint<=min(before,after)
    return dict(before=before,after=after,shared_zero=joint,gain=before-joint,
                loss=after-joint,net=before-after)

def record():
    return tuple(tuple(range(v,v+4)) for v in range(1,81,4))

def one_slot():
    # Fix A through S. Their 19 untouched quartets are interchangeable.
    old=record()
    rows=[]
    for size in range(2,11):
        for free in range(min(4,size)+1):
            for occ in combinations_with_replacement(range(5),19):
                if sum(occ)+free!=size:continue
                card=tuple(v for block,n in zip(old[:19],occ) for v in block[:n])+old[-1][:free]
                c=CAP[size]
                def direct(free_cap):
                    # For each untouched quartet, select zero or one ball.
                    dp={(0,0):1}
                    for a in occ:
                        q=defaultdict(int)
                        for (k,h),w in dp.items():
                            q[k,h]+=w
                            q[k+1,h]+=w*(4-a)
                            q[k+1,h+1]+=w*a
                        dp=q
                    return sum(w*comb(free,i)*comb(4-free,j)
                               for (k,h),w in dp.items()
                               for i in range(free+1) for j in range(5-free)
                               if k+i+j==20 and i+j<=free_cap and h+i<=c)
                new=old[:-1]+(card,)
                after=direct(4)
                joint=direct(1)
                assert after==count(new) and joint==count(old+new,frontier)
                rows.append(dict(card=card,size=size,free=free,occupancy=occ,before=RECORD,
                                 after=after,shared_zero=joint,gain=RECORD-joint,
                                 loss=after-joint,net=RECORD-after))
    save('single-slot-certificate.json',rows)
    print('single-slot',len(rows),min(r['after'] for r in rows),flush=True)

def sampler(cards,rng):
    """Uniform draw from the set where every unchanged card pays zero."""
    groups=components(SimpleNamespace(cards=cards))
    support=set(v for c in cards for v in c)
    options=[]
    for group in groups:
        numbers=sorted(set(v for c in group for v in c))
        if len(numbers)>16:raise Limit('Witness component exceeds 16 numbers.')
        masks=[sum(1<<numbers.index(v) for v in c) for c in group]
        by_hits=defaultdict(list)
        for bits in range(1<<len(numbers)):
            if any((bits&m).bit_count()>CAP[len(c)] for c,m in zip(group,masks)):continue
            by_hits[bits.bit_count()].append(sum(1<<(v-1) for i,v in enumerate(numbers) if bits>>i&1))
        options.append(dict(by_hits))
    unused=sorted(set(range(1,81))-support)
    suffix=[None]*(len(options)+1)
    suffix[-1]=[comb(len(unused),k) if k<=len(unused) else 0 for k in range(21)]
    for i in range(len(options)-1,-1,-1):
        suffix[i]=[sum(len(v)*suffix[i+1][k-j] for j,v in options[i].items() if j<=k)
                   for k in range(21)]
    assert suffix[0][20]>0
    def sample():
        left=20
        draw=0
        for i,group in enumerate(options):
            r=rng.randrange(suffix[i][left])
            for k,choices in group.items():
                if k>left:continue
                weight=len(choices)*suffix[i+1][left-k]
                if r<weight:
                    draw|=rng.choice(choices)
                    left-=k
                    break
                r-=weight
        draw|=mask(tuple(rng.sample(unused,left)))
        assert draw.bit_count()==20
        return draw
    return sample

def proposals():
    rng=Random(380717)
    prior=set()
    sources=[
        ('any-payout-expansion','search.json'),('any-payout-expansion-2','unique-search.json'),
        ('any-payout-expansion-3','search.json'),('any-payout-expansion-3','core-search.json'),
        ('incidence-ledger','candidates.json'),
    ]
    for directory,file in sources:
        for row in json.loads((OUT.parent/directory/file).read_text()):
            try:prior.add(canonical(Strategy(tuple(map(tuple,row['cards']))),200)['encoding'])
            except Limit:pass
    for directory,file in [('any-payout-expansion-3','witness84.json')]:
        st=Strategy.from_data(json.loads((OUT.parent/directory/file).read_text()))
        prior.add(canonical(st)['encoding'])
    seeds={'benchmark':record()}
    for folder,file,keys in [
        ('any-payout-expansion-2','unique-leaders.json',['two-card-core','hub']),
        ('incidence-ledger','boundary-leader.json',['three-or-four-marked','parallel-pair']),
        ('any-payout-expansion-3','core-leaders.json',['4','5','6','7']),
        ('incidence-ledger','leaders.json',['high-order']),
    ]:
        data=json.loads((OUT.parent/folder/file).read_text())
        for key in keys:seeds[key]=Strategy.from_data(data[key]).cards
    for old in seeds.values():prior.add(canonical(Strategy(old))['encoding'])
    rows=[]
    contexts=[]
    tally=Counter()
    for seed,old in seeds.items():
        try:base=count(old)
        except Limit:
            contexts.append(dict(seed=seed,status='source-count-deferred'))
            continue
        popularity=Counter(v for c in old for v in c)
        active=sorted(range(20),key=lambda i:-sum(popularity[v]-1 for v in old[i]))
        for size in (2,3,4,6):
            for trial in range(6):
                indices=tuple(sorted(active[:size] if trial==0 else rng.sample(range(20),size)))
                outside=tuple(c for i,c in enumerate(old) if i not in indices)
                try:draw=sampler(outside,rng)
                except Limit:
                    contexts.append(dict(seed=seed,slots=indices,status='witness-deferred'))
                    continue
                examples=[draw() for _ in range(160)]
                old_changed=[old[i] for i in indices]
                def hit(card,example):
                    return (mask(card)&example).bit_count()>CAP[len(card)]
                zeros=[i for i,e in enumerate(examples) if not any(hit(c,e) for c in old_changed)]
                wins=set(range(len(examples)))-set(zeros)
                # Reverse proposal: sample a paying subset of an uncovered draw.
                # Uniform legal selections are also offered at every changed slot.
                options=[]
                for _ in range(180):
                    spots=rng.randint(2,10)
                    if zeros and rng.randrange(4):
                        e=examples[rng.choice(zeros)]
                        numbers=[i for i in range(1,81) if e>>(i-1)&1]
                        include=rng.randint(CAP[spots]+1,spots)
                        selected=rng.sample(numbers,include)+rng.sample([i for i in range(1,81) if i not in numbers],spots-include)
                    else:selected=rng.sample(range(1,81),spots)
                    card=tuple(sorted(selected))
                    coverage=sum(1<<i for i,e in enumerate(examples) if hit(card,e))
                    options.append((card,coverage))
                for card in old_changed:
                    options.append((card,sum(1<<i for i,e in enumerate(examples) if hit(card,e))))
                # Bounded beam over OR masks, keeping coordinated alternatives.
                beam=[((),0)]
                for _ in indices:
                    merged={}
                    for cards,cover in beam:
                        for c,p in options:
                            key=tuple(sorted(cards+(c,)))
                            merged[key]=cover|p
                    beam=sorted(merged.items(),key=lambda kv:(-kv[1].bit_count(),kv[0]))[:9]
                bundles=[(cs,coverage,'targeted') for cs,coverage in beam[:6]]
                for _ in range(2):
                    cs=tuple(tuple(sorted(rng.sample(range(1,81),rng.randint(2,10)))) for _ in indices)
                    coverage=sum(1<<i for i,e in enumerate(examples) if any(hit(c,e) for c in cs))
                    bundles.append((cs,coverage,'unrestricted-control'))
                for changed,coverage,mode in bundles:
                    new=outside+changed
                    r=dict(seed=seed,changed_slots=indices,removed=old_changed,added=changed,
                           cards=new,mode=mode,sampled_gain=sum(bool(coverage>>i&1) for i in zeros),
                           sampled_loss=sum(not(coverage>>i&1) for i in wins))
                    try:code=canonical(Strategy(new),500)['encoding']
                    except Limit:
                        r['status']='canonical-deferred'
                        rows.append(r)
                        continue
                    if code in prior:
                        tally['relabeling_skipped']+=1
                        continue
                    prior.add(code)
                    try:
                        r.update(change(old,new,base))
                        r['status']='exact'
                    except Limit:r['status']='count-deferred'
                    rows.append(r)
                contexts.append(dict(seed=seed,slots=indices,status='sampled',witnesses=len(examples),
                                     sampled_old_zero=len(zeros),pool=len(options),bundles=len(bundles)))
        save('contexts.json',contexts)
        save('candidates.json',rows)
        print(seed,len(rows),sum(r['status']=='exact' for r in rows),flush=True)
    save('coverage.json',tally)
    leaders={}
    exact=sorted((r for r in rows if r['status']=='exact'),key=lambda r:r['after'])
    for r in exact+sorted(exact,key=lambda r:-r['net']):
        keys=[r['mode'],'best'] if r['mode'] not in leaders else ['best']
        if r['net']==max((x['net'] for x in exact),default=0):keys.append('greatest-net-gain')
        if r['after']<RECORD:keys.append(str(r['cards']))
        if all(k in leaders for k in keys):continue
        try:
            v=verify(Strategy(r['cards']),r['after'])
            old=seeds[r['seed']]
            assert count(old,frontier)==r['before'] and count(old+r['cards'],frontier)==r['shared_zero']
        except Limit:continue
        for k in keys:leaders.setdefault(k,dict(r,verified=v))
    save('leaders.json',leaders)

if __name__=='__main__':
    for command in sys.argv[1:]:globals()[command]()
