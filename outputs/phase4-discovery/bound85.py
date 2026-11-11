"""Prove incidence-85 branches by independent component-polynomial envelopes."""
from pathlib import Path
import sys,json
from collections import Counter
from itertools import product
from functools import lru_cache
from math import comb
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent/'incidence-ledger'))
from incidence_run import shapes85,code,ex,CAP,D,RECORD,multiply
WIDTH=81
MASK=(1<<WIDTH)-1

@lru_cache(None)
def packed_factor(n,cap):
    return sum(comb(n,j)<<(WIDTH*j) for j in range(min(n,cap)+1))

def unpack(p):
    return tuple((p>>(WIDTH*j))&MASK for j in range(1+(p.bit_length()-1)//WIDTH))

@lru_cache(None)
def packed_tail(n,total,lo=2):
    if n==0:return (1,) if total==0 else ()
    if lo>10 or not n*lo<=total<=10*n:return ()
    values=[]
    p=1
    factor=packed_factor(lo,CAP[lo])
    for count in range(min(n,total//lo)+1):
        values.extend(p*x for x in packed_tail(n-count,total-count*lo,lo+1))
        p*=factor
    return tuple(values)

@lru_cache(None)
def tail(n,total,independent):
    if not independent:return ex.envelope(n,total)
    values=packed_tail(n,total)
    return tuple(min((p>>(WIDTH*j))&MASK for p in values) for j in range(21))

def packed_profiles(g):
    n=1+max(map(max,g))
    degree=[sum(i in edge for edge in g) for i in range(n)]
    hits=[tuple(sum(i in edge for j,edge in enumerate(g) if mask>>j&1) for i in range(n))
          for mask in range(1<<len(g))]
    for sizes in product(*(range(max(2,d),11) for d in degree)):
        value=0
        for mask,row in enumerate(hits):
            p=1<<(WIDTH*mask.bit_count())
            for s,d,h in zip(sizes,degree,row):
                p*=packed_factor(s-d,CAP[s]-h)
                if not p:break
            value+=p
        yield sum(sizes),unpack(value)

@lru_cache(None)
def profile_envelope(g,independent):
    profiles=packed_profiles(g) if independent else ex.local_profiles(g)
    out={}
    for total,poly in profiles:
        padded=poly+(0,)*(21-len(poly))
        if total in out:out[total]=tuple(map(min,zip(out[total],padded)))
        else:out[total]=padded
    return tuple(sorted(out.items()))

def groups(shape):
    return tuple(sorted(code(g) for g in ex.components_of(shape)))

def bound(shape,independent):
    components=groups(shape)
    n=1+max(map(max,shape))
    best=D
    count=0
    envelopes={0:(1,)+(0,)*20}
    for g in components:
        nxt={}
        for s,p in envelopes.items():
            for t,q in profile_envelope(g,independent):
                if s+t>85-2*(20-n):continue
                if independent:
                    packed=lambda xs:sum(v<<(WIDTH*j) for j,v in enumerate(xs))
                    f=unpack(packed(p)*packed(q))[:21]
                else:f=multiply(p,q)
                f=f+(0,)*(21-len(f))
                if s+t in nxt:f=tuple(map(min,zip(nxt[s+t],f)))
                nxt[s+t]=f
        envelopes=nxt
    for s,law in envelopes.items():
        rem=85-s
        if not 2*(20-n)<=rem<=10*(20-n):continue
        t=tail(20-n,rem,independent)
        value=sum(v*t[20-j] for j,v in enumerate(law))
        best=min(best,value)
        count+=1
    assert count
    return best,count

def save(name,obj):
    p=OUT/name
    temp=p.with_suffix('.tmp')
    temp.write_text(json.dumps(obj,indent=2)+'\n')
    temp.replace(p)

def main(width):
    original=json.loads((OUT.parent/'incidence-ledger'/'ledger.json').read_text())
    shape_rows={tuple(map(tuple,r['shape'])):r for r in original['geometry85']}
    assert set(shapes85())==set(shape_rows)
    file=OUT/'certificates85.json'
    rows=json.loads(file.read_text()) if file.exists() else []
    seen={tuple(map(tuple,r['shape'])) for r in rows}
    targets=sorted(shape_rows,key=lambda s:(max(1+max(map(max,g)) for g in groups(s)),s))
    for shape in targets:
        if shape in seen or shape_rows[shape]['status']=='certified-no-improvement':continue
        largest=max(1+max(map(max,g)) for g in groups(shape))
        if largest>width:continue
        lower,count=bound(shape,False)
        audit=bound(shape,True)
        assert audit==(lower,count)
        rows.append(dict(shape=shape,largest_marked_component=largest,combined_marked_totals=count,
                         lower=lower,status='certified' if lower>=RECORD else 'unresolved-envelope',
                         proof='coefficientwise minimum at fixed component and combined incidence totals; exact packed-integer replay'))
        save('certificates85.json',rows)
        if len(rows)%10==0:print(len(rows),Counter(r['status'] for r in rows),flush=True)
    records={tuple(map(tuple,r['shape'])):r for r in rows}
    ledger=[]
    for shape in targets:
        old=shape_rows[shape]
        row=records.get(shape)
        state=('inherited-certified' if old['status']=='certified-no-improvement' else
               row['status'] if row else 'unresolved-unvisited')
        ledger.append(dict(shape=shape,status=state,certificate=row,prior_status=old['status']))
    save('coverage85.json',ledger)
    print('coverage',Counter(r['status'] for r in ledger),flush=True)

if __name__=='__main__':main(int(sys.argv[1]))
