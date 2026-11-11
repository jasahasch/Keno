"""Exact fixed-size draws for additive, hit-count-only payouts."""
from collections import Counter
from itertools import combinations, product
from math import comb

OBJECTIVES={'any-payout','net-profit'}

class Deferred(RuntimeError):
    """The exact evaluator reached its work budget."""

def rules(spec):
    required={'game','name','version','universe','draw','cards','sizes','duplicates',
              'overlap','wager','unit','mechanics','objectives'}
    if set(spec)!=required:raise ValueError('Unexpected or missing game-rule fields.')
    for key in ('game','name','version','unit'):
        if not isinstance(spec[key],str) or not spec[key].strip():raise ValueError(f'Invalid {key}.')
    for key in ('universe','draw','cards','wager'):
        if type(spec[key]) is not int or spec[key]<=0:raise ValueError(f'Invalid {key}.')
    if spec['draw']>spec['universe']:raise ValueError('Draw exceeds universe.')
    sizes=spec['sizes']
    if not sizes or any(type(s) is not int or not 1<=s<=spec['universe'] for s in sizes) or sizes!=sorted(set(sizes)):
        raise ValueError('Spot sizes must be sorted, distinct and legal.')
    if type(spec['duplicates']) is not bool or type(spec['overlap']) is not bool:
        raise ValueError('Duplication and overlap rules must be boolean.')
    if not spec['overlap'] and (spec['duplicates'] or spec['cards']*min(sizes)>spec['universe']):
        raise ValueError('Impossible disjoint-card rules.')
    if not spec['duplicates'] and spec['cards']>sum(comb(spec['universe'],s) for s in sizes):
        raise ValueError('Too few distinct cards.')
    if spec['mechanics']!={'draw':'uniform-without-replacement','award':'additive-hit-count','bonus':None,'multiplier':None}:
        raise ValueError('Unsupported draw, bonus, multiplier or award mechanic.')
    if not spec['objectives'] or not set(spec['objectives'])<=OBJECTIVES:
        raise ValueError('Unsupported optimization objective.')
    return spec

def paytable(spec,table):
    if set(table)!={'id','version','source','payouts','bonus'} or table['bonus'] is not None:
        raise ValueError('Unsupported or incomplete paytable definition.')
    if any(not isinstance(table[k],str) or not table[k].strip() for k in ('id','version','source')):
        raise ValueError('Paytable identifier, version and source are required.')
    if set(table['payouts'])!={str(s) for s in spec['sizes']}:
        raise ValueError('Paytable must specify every permitted card size.')
    for s in spec['sizes']:
        p=table['payouts'][str(s)]
        if len(p)!=s+1 or any(type(v) is not int or v<0 for v in p):
            raise ValueError('Specify every hit payout in nonnegative integer units.')
    return table

def pattern(spec,cards):
    if len(cards)!=spec['cards']:raise ValueError('Incorrect card count.')
    result=[]
    for c in cards:
        if len(c) not in spec['sizes'] or any(type(v) is not int or not 1<=v<=spec['universe'] for v in c) or len(set(c))!=len(c):
            raise ValueError('Illegal card.')
        result.append(tuple(sorted(c)))
    if not spec['duplicates'] and len(result)!=len(set(result)):raise ValueError('Repeated complete card.')
    if not spec['overlap'] and len(set().union(*map(set,result)))!=sum(map(len,result)):
        raise ValueError('Overlap is prohibited.')
    return tuple(result)

def identity(spec,cards):
    # Safe quotient of physical-number labels with card slots held fixed.
    return tuple(sorted(regions(cards).items()))

def regions(cards):
    return Counter(sum(1<<i for i,c in enumerate(cards) if v in c)
                   for v in set().union(*map(set,cards)))

def _region_distribution(spec,table,cards,budget):
    masks=regions(cards)
    masks[0]=spec['universe']-sum(masks.values())
    draw=spec['draw']
    owners=[(tuple(i for i in range(len(cards)) if mask>>i&1),count) for mask,count in masks.items()]
    law=Counter()
    states={(0,(0,)*len(cards)):1}
    remaining=spec['universe']
    for slots,n in owners:
        remaining-=n
        following=Counter()
        for (k,hits),ways in states.items():
            for picked in range(max(0,draw-k-remaining),min(n,draw-k)+1):
                budget-=1
                if budget<0:raise Deferred('Membership-state budget exceeded.')
                result=list(hits)
                for i in slots:result[i]+=picked
                following[k+picked,tuple(result)]+=ways*comb(n,picked)
        states=following
    for (k,hits),ways in states.items():
        assert k==draw
        law[sum(table['payouts'][str(len(c))][h] for c,h in zip(cards,hits))]+=ways
    return law

def _subset_distribution(spec,table,cards,budget):
    support=sorted(set().union(*map(set,cards)))
    outside=spec['universe']-len(support)
    draw=spec['draw']
    low=max(0,draw-outside)
    high=min(draw,len(support))
    if sum(comb(len(support),k) for k in range(low,high+1))>budget:
        raise Deferred('Literal-subset budget exceeded.')
    masks=[sum(1<<(v-1) for v in c) for c in cards]
    awards=[table['payouts'][str(len(c))] for c in cards]
    law=Counter()
    for k in range(low,high+1):
        weight=comb(outside,draw-k)
        for selected in combinations(support,k):
            mask=sum(1<<(v-1) for v in selected)
            law[sum(row[(m&mask).bit_count()] for m,row in zip(masks,awards))]+=weight
    return law

def evaluate(spec,table,cards,budget):
    if type(budget) is not int or budget<1:raise ValueError('Positive integer work budget required.')
    a=_region_distribution(spec,table,cards,budget)
    b=_subset_distribution(spec,table,cards,budget)
    if a!=b or sum(a.values())!=comb(spec['universe'],spec['draw']):
        raise ArithmeticError('Independent exact payout distributions disagree.')
    return a

def score(spec,law,objective):
    if objective not in spec['objectives']:raise ValueError('Objective is unavailable for this game.')
    threshold=0 if objective=='any-payout' else spec['cards']*spec['wager']
    return sum(n for award,n in law.items() if award>threshold)

def unrank(n,k,rank):
    if not 0<=rank<comb(n,k):raise ValueError('Combination rank outside scope.')
    result=[]
    low=0
    while k:
        left,right=low,n-k
        base=comb(n-low,k)
        while left<right:
            mid=(left+right+1)//2
            if base-comb(n-mid,k)<=rank:left=mid
            else:right=mid-1
        rank-=base-comb(n-left,k)
        result.append(left)
        low=left+1
        k-=1
    return tuple(result)

def scope(spec):
    choices=sum(comb(spec['universe'],s) for s in spec['sizes'])
    return comb(choices+spec['cards']-1 if spec['duplicates'] else choices,spec['cards'])

def candidate(spec,rank):
    counts=[comb(spec['universe'],s) for s in spec['sizes']]
    k=spec['cards']
    expanded=sum(counts)+k-1 if spec['duplicates'] else sum(counts)
    cards=[]
    for i,slot in enumerate(unrank(expanded,k,rank)):
        if spec['duplicates']:slot-=i
        for s,n in zip(spec['sizes'],counts):
            if slot<n:
                cards.append(tuple(v+1 for v in unrank(spec['universe'],s,slot)))
                break
            slot-=n
    return tuple(cards)
