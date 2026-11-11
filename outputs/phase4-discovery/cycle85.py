"""Use tree messages after conditioning one incidence of a unicyclic component."""
import bound85 as b
from tree85 import floor,convolution
from functools import lru_cache
from itertools import product
from math import comb
import json

@lru_cache(None)
def envelope(shape,packed):
    n=1+max(map(max,shape))
    original=[tuple(j for j,e in enumerate(shape) if i in e) for i in range(n)]
    def connected(edges):
        cards={0}
        while True:
            new=cards.union(*(set(e) for e in edges if cards.intersection(e)))
            if new==cards:return len(cards)==n
            cards=new
    excess=sum(map(len,shape))-n-len(shape)+1
    assert excess in (0,1) and connected(shape)
    if excess:
        edge=None
        for j,e in enumerate(shape):
            for i in e:
                altered=shape[:j]+(tuple(v for v in e if v!=i),)+shape[j+1:]
                if connected(altered):
                    edge=(i,j)
                    break
            if edge:break
        assert edge
    else:
        altered=shape
        edge=(-1,-1)
    cut_card,cut_ball=edge
    slots=[tuple(j for j,e in enumerate(altered) if i in e) for i in range(n)]
    assert sum(map(len,slots))==n+len(shape)-1

    def fixed(bit):
        @lru_cache(None)
        def shared(j,parent):
            children=[card(i,j) for i in altered[j] if i!=parent]
            out=[{},{}]
            for selected in (0,1):
                d={0:(1,)}
                for c in children:
                    nxt={}
                    for s,p in d.items():
                        for t,q in c[selected].items():
                            floor(nxt,s+t,convolution(p,q,packed))
                    d=nxt
                out[selected]=d
            assert set(out[0])==set(out[1])
            return {s:(out[0][s],out[1][s]) for s in out[0]}

        @lru_cache(None)
        def card(i,parent):
            ids=[j for j in slots[i] if j!=parent]
            children=[shared(j,i) for j in ids]
            out=[{},{}]
            for size in range(max(2,len(original[i])),11):
                private=size-len(original[i])
                for blocks in product(*(d.items() for d in children)):
                    total=size+sum(t for t,_ in blocks)
                    for inherited in (0,1):
                        if parent==-1 and inherited:continue
                        vals=[0]*21
                        for selected in product(*[(bit,) if j==cut_ball else (0,1) for j in ids]):
                            hits=sum(selected)
                            cap=b.CAP[size]-inherited-hits-(bit if i==cut_card else 0)
                            if cap<0:continue
                            p=(0,)*hits+tuple(comb(private,k) for k in range(min(cap,private)+1))
                            for chosen,(_,q) in zip(selected,blocks):p=convolution(p,q[chosen],packed)
                            for j,v in enumerate(p):vals[j]+=v
                        floor(out[inherited],total,vals)
            return out
        return card(min(range(n),key=lambda i:len(slots[i])),-1)[0]
    no=fixed(0)
    if not excess:return tuple(sorted(no.items()))
    yes=fixed(1)
    assert set(no)==set(yes)
    return tuple((s,tuple(a+c for a,c in zip(p,yes[s]))) for s,p in sorted(no.items()))

def main():
    path=b.OUT/'cycle-certificates85.json'
    rows=json.loads(path.read_text()) if path.exists() else []
    seen={tuple(map(tuple,r['shape'])) for r in rows}
    old=b.profile_envelope
    def new(g,packed):
        return envelope(g,packed) if 1+max(map(max,g))==5 else old(g,packed)
    b.profile_envelope=new
    for shape in b.shapes85():
        if shape in seen or max(1+max(map(max,g)) for g in b.groups(shape))!=5:continue
        a=b.bound(shape,False)
        assert a==b.bound(shape,True)
        rows.append(dict(shape=shape,lower=a[0],status='certified' if a[0]>=b.RECORD else 'unresolved-cycle-envelope',
                         proof='incidence-tree messages, conditioning on a cycle number where needed, packed replay'))
        b.save(path.name,rows)
        print(len(rows),a[0],flush=True)

if __name__=='__main__':main()
