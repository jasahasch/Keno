"""Exact reusable component polynomials for the continuation evaluator."""
from collections import Counter
from functools import lru_cache
from math import comb
from types import SimpleNamespace
from spot_strategy.canonical import components
from unrestricted_resolution.zero import multiply

@lru_cache(maxsize=8192)
def local(cards, caps):
    n=1+max(v for c in cards for v in c)
    masks=[sum(1<<v for v in c) for c in cards]
    counts=Counter()
    for bits in range(1<<n):
        if all((bits&m).bit_count()<=cap for m,cap in zip(masks,caps)):
            counts[bits.bit_count()]+=1
    return tuple(counts[i] for i in range(max(counts)+1))

def evaluate(w,cards,states,seconds):
    groups=[]
    support=0
    for group in components(SimpleNamespace(cards=cards)):
        labels={v:i for i,v in enumerate(sorted(set().union(*map(set,group))))}
        n=len(labels)
        if n>12:return None
        normalized=tuple(sorted(tuple(labels[v] for v in c) for c in group))
        caps=tuple(w.TABLE.first_positive(len(c))-1 for c in normalized)
        if any(not all((p>0)==(h>cap) for h,p in enumerate(w.TABLE[len(c)]))
               for c,cap in zip(normalized,caps)):
            raise ValueError('Payout threshold mismatch.')
        groups.append((normalized,caps,n))
        support+=n
    budget=w.Budget(states,seconds)
    polynomial=(1,)
    old=local.cache_info()
    for group,caps,n in groups:
        budget.tick(1<<n)
        polynomial=multiply(polynomial,local(group,caps))
    outside=80-support
    polynomial=multiply(polynomial,tuple(comb(outside,k) for k in range(min(20,outside)+1)))
    hits=local.cache_info().hits-old.hits
    return polynomial+(0,)*(21-len(polynomial)),dict(method='cached-component-subsets',cache_hits=hits,components=len(groups))
