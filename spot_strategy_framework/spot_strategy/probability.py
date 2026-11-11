"""Exact marginal laws under the common fixed twenty-of-eighty draw."""
from dataclasses import dataclass
from collections import Counter,defaultdict
from math import prod
import time
from .model import choose,DENOMINATOR,ResourceLimit
from .canonical import components
@dataclass
class Counts:
    gross:dict
    paying:dict
    jackpots:dict
    method:str
    def validate(self):
        for values in (self.gross,self.paying,self.jackpots):
            if any(type(k) is not int or k<0 or type(v) is not int or v<0 for k,v in values.items()):raise ValueError('Invalid outcome count.')
            if sum(values.values())!=DENOMINATOR:raise ValueError('Outcome counts do not cover the complete draw space.')
        return self
    def to_dict(self):return {'denominator':str(DENOMINATOR),'gross':{str(k):str(v) for k,v in sorted(self.gross.items()) if v},'paying':{str(k):str(v) for k,v in sorted(self.paying.items()) if v},'jackpots':{str(k):str(v) for k,v in sorted(self.jackpots.items()) if v},'method':self.method}
    @classmethod
    def from_dict(cls,d):
        if int(d['denominator'])!=DENOMINATOR:raise ValueError('Wrong draw model.')
        return cls(*({int(k):int(v) for k,v in d[n].items()} for n in ('gross','paying','jackpots')),d['method']).validate()
class Budget:
    def __init__(self,limits):self.limits=limits;self.work=0;self.start=time.monotonic()
    def tick(self,n=1):
        self.work+=n
        if self.work>self.limits.max_operations:raise ResourceLimit('Exact operation budget exhausted.')
        if self.work%1024< n and time.monotonic()-self.start>self.limits.max_seconds:raise ResourceLimit('Exact evaluator deadline reached.')
    def states(self,n):
        if n>self.limits.max_global_states:raise ResourceLimit('Exact state-space limit reached.')

def region_component(cards,table,budget):
    vertices=set(v for c in cards for v in c);regions=Counter(tuple(j for j,c in enumerate(cards) if v in c) for v in vertices)
    if prod(n+1 for n in regions.values())>budget.limits.max_component_choices:raise ResourceLimit('Membership-region component budget exceeded.')
    entries=list(regions.items());hits=[0]*len(cards);local=defaultdict(int)
    def rec(i,k,w):
        budget.tick()
        if i==len(entries):
            gross=sum(table[len(c)][h] for c,h in zip(cards,hits));paid=sum(table[len(c)][h]>0 for c,h in zip(cards,hits));jp=sum(table[len(c)][h]==10000 for c,h in zip(cards,hits));local[k,gross,paid,jp]+=w;return
        owners,n=entries[i]
        for caught in range(min(n,20-k)+1):
            for j in owners:hits[j]+=caught
            rec(i+1,k+caught,w*choose(n,caught))
            for j in owners:hits[j]-=caught
    rec(0,0,1);return len(vertices),local

def subset_component(cards,table,budget):
    """Independent direct number-subset enumeration; no binomial region weights."""
    vertices=sorted(set(v for c in cards for v in c));m=len(vertices)
    if (1<<m)>budget.limits.max_component_choices:raise ResourceLimit('Independent number-subset component budget exceeded.')
    masks=[sum(1<<j for j,v in enumerate(vertices) if v in c) for c in cards];local=defaultdict(int)
    for selected in range(1<<m):
        budget.tick();k=selected.bit_count()
        if k>20:continue
        hits=[(selected&mask).bit_count() for mask in masks]
        gross=sum(table[len(c)][h] for c,h in zip(cards,hits));paid=sum(table[len(c)][h]>0 for c,h in zip(cards,hits));jp=sum(table[len(c)][h]==10000 for c,h in zip(cards,hits));local[k,gross,paid,jp]+=1
    return m,local

def region_evaluate(strategy,table,limits):
    budget=Budget(limits);dps=[{(0,0):1} for _ in range(3)];used=0
    for cards in components(strategy):
        n,local=region_component(cards,table,budget);used+=n
        for channel in range(3):
            factor=defaultdict(int)
            for outcome,w in local.items():factor[outcome[0],outcome[channel+1]]+=w
            nxt=defaultdict(int)
            for (k,g),a in dps[channel].items():
                for (h,p),b in factor.items():
                    budget.tick()
                    if k+h<=20:nxt[k+h,g+p]+=a*b
                    if budget.work%1024==0:budget.states(len(nxt))
            budget.states(len(nxt));dps[channel]=nxt
    laws=[]
    for dp in dps:
        law=defaultdict(int)
        for (k,p),w in dp.items():law[p]+=w*choose(80-used,20-k)
        laws.append({k:v for k,v in law.items() if v})
    return Counts(*laws,'python-membership-regions-v1').validate()

def subset_evaluate(strategy,table,limits):
    budget=Budget(limits);factors=[];used=0
    for cards in components(strategy):
        n,local=subset_component(cards,table,budget);used+=n;factors.append(local)
    laws=[]
    # Separate independent reduction order (largest components first).
    factors.sort(key=len,reverse=True)
    for field in (1,2,3):
        dp={(0,0):1}
        for local in factors:
            factor=Counter()
            for entry,w in local.items():factor[entry[0],entry[field]]+=w
            updated=Counter()
            for (caught,value),count in dp.items():
                for (take,add),ways in factor.items():
                    budget.tick()
                    if caught+take<=20:updated[caught+take,value+add]+=count*ways
                    if budget.work%1024==0:budget.states(len(updated))
            budget.states(len(updated));dp=updated
        final=Counter()
        for (caught,value),ways in dp.items():final[value]+=ways*choose(80-used,20-caught)
        laws.append({k:v for k,v in final.items() if v})
    return Counts(*laws,'python-direct-subsets-v1').validate()
