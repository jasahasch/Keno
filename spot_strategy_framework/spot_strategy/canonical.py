"""Exact component incidence canonicalization, with a safe literal fallback."""
from itertools import product
from math import factorial
from hashlib import sha256
import json
from .model import Strategy

def components(strategy):
    pending=list(strategy.cards);out=[]
    while pending:
        group=[pending.pop()];vertices=set(group[0])
        while True:
            take=[c for c in pending if vertices.intersection(c)]
            if not take:break
            pending=[c for c in pending if not vertices.intersection(c)];group.extend(take)
            for c in take:vertices.update(c)
        out.append(tuple(group))
    return out

def multiset_permutations(items):
    from collections import Counter
    counts=Counter(items);keys=sorted(counts);n=len(items)
    def rec(prefix):
        if len(prefix)==n:yield tuple(prefix);return
        for k in keys:
            if counts[k]:
                counts[k]-=1;prefix.append(k);yield from rec(prefix);prefix.pop();counts[k]+=1
    yield from rec([])

def canonical(strategy,max_permutations=100000):
    encodings=[];work=0
    for group in components(strategy):
        bysize={s:[c for c in group if len(c)==s] for s in sorted(set(map(len,group)))}
        count=1
        for cards in bysize.values():
            from collections import Counter
            count*=factorial(len(cards))//__import__('functools').reduce(lambda a,b:a*factorial(b),Counter(cards).values(),1)
        work+=count
        if work>max_permutations:
            data=['literal-card-label-sensitive',sorted(strategy.cards)]
            encoded=json.dumps(data,separators=(',',':'));return sha256(encoded.encode()).hexdigest(),'literal-safe-fallback',encoded
        best=None;vertices=set(v for c in group for v in c)
        for chunks in product(*(tuple(multiset_permutations(cards)) for cards in bysize.values())):
            order=tuple(c for chunk in chunks for c in chunk);regions={}
            for v in vertices:
                mask=sum(1<<i for i,c in enumerate(order) if v in c);regions[mask]=regions.get(mask,0)+1
            code=(tuple(map(len,order)),tuple(sorted(regions.items())))
            if best is None or code<best:best=code
        encodings.append(best)
    encoded=json.dumps(['exact-incidence-components',sorted(encodings)],separators=(',',':'))
    return sha256(encoded.encode()).hexdigest(),'exact-number-and-card-relabeling',encoded
