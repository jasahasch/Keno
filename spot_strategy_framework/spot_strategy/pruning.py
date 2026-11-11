"""Constructive, independently checkable graph bounds. Never a universal spot optimum."""
from fractions import Fraction as F
from itertools import combinations,product
from math import factorial,ceil
from .model import DENOMINATOR

def groups_for(card,table):
    count=table.first_positive(len(card))-1;a,b=divmod(len(card),count);sizes=[a+1]*b+[a]*(count-b);offset=0;groups=[]
    for size in sizes:groups.append(tuple(card[offset:offset+size]));offset+=size
    return groups

def construct(strategy,table):
    groups=[groups_for(c,table) for c in strategy.cards];eligible=[i for i,c in enumerate(strategy.cards) if 10000 in table[len(c)]];kind='balanced-card-partitions'
    if len(eligible) in (4,6,7) and all(len(strategy.cards[i])==8 for i in eligible):
        cards=[set(strategy.cards[i]) for i in eligible];membership={v:sum(v in c for c in cards) for v in set().union(*cards)}
        if all(n==2 for n in membership.values()):
            intersections=[[sorted(a&b) if i!=j else [] for j,b in enumerate(cards)] for i,a in enumerate(cards)];m=len(cards);proposed=[]
            if m==4:
                columns=list(map(len,intersections[0][1:]));best=None
                for x in product(range(4),repeat=3):
                    if sum(x)!=3:continue
                    for y in product(range(4),repeat=3):
                        if sum(y)!=3:continue
                        z=tuple(columns[j]-x[j]-y[j] for j in range(3))
                        if min(z)<0 or sum(z)!=2:continue
                        value=sum(v*(v-1)//2 for row in (x,y,z) for v in row)
                        if best is None or value>best[0]:best=(value,(x,y,z))
                if best:
                    proposed=[[[] for _ in range(3)] for _ in range(4)];matrix=best[1]
                    for u,v,col in [(0,1,0),(0,2,1),(0,3,2),(1,2,2),(1,3,1),(2,3,0)]:
                        ids=intersections[u][v];offset=0
                        for row in range(3):chunk=ids[offset:offset+matrix[row][col]];offset+=matrix[row][col];proposed[u][row]+=chunk;proposed[v][row]+=chunk
            elif all(len(intersections[i][j]) in (1,2) for i in range(m) for j in range(i)):
                for shared in intersections:
                    pairs=[x for x in shared if len(x)==2];singles=[x[0] for x in shared if len(x)==1]
                    if m==6 and len(pairs)==3 and len(singles)==2:proposed.append([pairs[0]+singles[:1],pairs[1]+singles[1:],pairs[2]])
                    elif m==7 and len(pairs)==2 and len(singles)==4:proposed.append([pairs[0]+singles[:1],pairs[1]+singles[1:2],singles[2:]])
            if len(proposed)==m:
                candidate=list(groups)
                for i,g in zip(eligible,proposed):candidate[i]=g
                if edge_count(candidate)<=edge_count(groups):groups=candidate;kind='shared-eligible-pair-partitions'
    K=edge_count(groups)
    if K<=128:
        lower=F(80**20,factorial(20))
        for i in range(1,20):lower*=1-F(i*(K+40),3200)
        zero=ceil(lower);upper=F(DENOMINATOR-zero,DENOMINATOR)
    else:lower=F(0);zero=0;upper=F(1)
    return {'kind':kind,'groups':[[list(g) for g in gs] for gs in groups],'graph_edges':K,'zero_lower_rational':str(lower),'zero_lower_integer':str(zero),'frequency_upper':str(upper),'theorem':'accepted-clique-convex-bound','paytable_sha256':table.sha256,'scope':'This concrete portfolio; no independence or fresh-number assumption.'}
def edge_count(groups):return len({tuple(sorted(e)) for gs in groups for g in gs for e in combinations(g,2)})

def verify_certificate(strategy,table,certificate):
    gs=certificate['groups']
    if len(gs)!=len(strategy.cards) or certificate['paytable_sha256']!=table.sha256:raise ValueError('Certificate provenance mismatch.')
    for card,parts in zip(strategy.cards,gs):
        if sorted(v for g in parts for v in g)!=list(card):raise ValueError('Groups do not partition their card.')
        # Complete local pointwise payout implication, independent of the constructor.
        for selected in range(1<<len(card)):
            picked={card[j] for j in range(len(card)) if selected>>j&1}
            if table[len(card)][len(picked)]>0 and not any(len(picked.intersection(g))>=2 for g in parts):raise ValueError('Invalid graph payout majorant.')
    edges=set()
    for parts in gs:
        for part in parts:
            for i,u in enumerate(part):
                for v in part[:i]:edges.add(tuple(sorted((u,v))))
    K=len(edges)
    if K!=certificate['graph_edges']:raise ValueError('Graph edge mismatch.')
    if K<=128:
        numerator=80
        for i in range(1,20):numerator*=3200-i*(K+40)
        denominator=40**19*factorial(20);lo=F(numerator,denominator);integer=(numerator+denominator-1)//denominator
    else:lo=F(0);integer=0
    if lo!=F(certificate['zero_lower_rational']) or integer!=int(certificate['zero_lower_integer']) or F(certificate['frequency_upper'])!=F(DENOMINATOR-integer,DENOMINATOR):raise ValueError('Rational bound verification failed.')
    return True

def prune_reason(config,certificate,incumbent=None):
    upper=F(certificate['frequency_upper'])
    if config.objective=='jackpot' and upper<F(config.minimum_frequency):return 'Certified payout-frequency upper bound is below the requested constraint.'
    if config.improve_record and config.objective=='frequency' and incumbent is not None and upper<=F(incumbent):return 'Certified upper bound cannot strictly improve this frequency record.'
    return None
