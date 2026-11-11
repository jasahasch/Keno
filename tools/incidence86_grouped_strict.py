"""Symmetry-grouped conditional tree/cycle envelopes; no historical writes."""
import incidence86 as base
b = base.b
from tree85 import floor,convolution
from functools import lru_cache
from itertools import product, combinations_with_replacement
from collections import Counter
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
            # Identical conditional message tables AND attachment restrictions are
            # exchangeable. Keep multiplicities of every feasible child total.
            def structure_ball(j,parent):
                return tuple(sorted(structure_card(v,j) for v in altered[j] if v!=parent))
            def structure_card(v,parent):
                return (len(original[v]), v==cut_card,
                        tuple(sorted((j==cut_ball,structure_ball(j,v)) for j in slots[v] if j!=parent)))
            signatures = Counter((tuple(d.items()), j == cut_ball, structure_ball(j,i)) for j,d in zip(ids,children))
            choices = [combinations_with_replacement(table, count)
                       for (table, restricted, structural),count in signatures.items()]
            for grouped in product(*choices):
                blocks = []
                for group, ((table, restricted, structural), count) in zip(grouped, signatures.items()):
                    blocks.extend((t,q,restricted) for t,q in group)
                # Sum all physical shared-hit states before imposing the hub cap.
                # The shared number is counted here exactly once, at its parent.
                joint = {0:(1,)}
                for total,q,restricted in blocks:
                    nxt = {}
                    for hits,p in joint.items():
                        for chosen in ((bit,) if restricted else (0,1)):
                            v = convolution(p,q[chosen],packed)
                            h = hits+chosen
                            if h in nxt:
                                old=nxt[h]; width=max(len(old),len(v))
                                v=tuple((old[k] if k<len(old) else 0)+(v[k] if k<len(v) else 0) for k in range(width))
                            nxt[h]=v
                    joint=nxt
                subtotal=sum(t for t,q,r in blocks)
                for size in range(max(2,len(original[i])),11):
                    private=size-len(original[i])
                    for inherited in (0,1):
                        if parent==-1 and inherited:continue
                        vals=[0]*21
                        for hits,q in joint.items():
                            cap=b.CAP[size]-inherited-hits-(bit if i==cut_card else 0)
                            if cap<0:continue
                            p=(0,)*hits+tuple(comb(private,k) for k in range(min(cap,private)+1))
                            p=convolution(p,q,packed)
                            for j,v in enumerate(p[:21]):vals[j]+=v
                        floor(out[inherited],size+subtotal,vals)
            return out
        return card(max(range(n),key=lambda i:len(slots[i])),-1)[0]
    no=fixed(0)
    if not excess:return tuple(sorted(no.items()))
    yes=fixed(1)
    assert set(no)==set(yes)
    return tuple((s,tuple(a+c for a,c in zip(p,yes[s]))) for s,p in sorted(no.items()))
