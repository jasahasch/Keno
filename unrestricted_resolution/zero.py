"""Two exact zero-payout polynomial algorithms. Coefficient 20 includes all 80 numbers."""
from collections import Counter,defaultdict
from functools import lru_cache
from math import comb
import time

class Limit(RuntimeError):pass
class Budget:
 def __init__(self,states=1000000,seconds=30):self.states=states;self.end=time.monotonic()+seconds;self.work=0;self.peak=0
 def tick(self,n=1):
  self.work+=n
  if self.work>self.states or time.monotonic()>self.end:raise Limit('State/time budget exceeded; no accepted result.')
 def observe(self,n):
  self.peak=max(self.peak,n)
  if n>self.states:raise Limit('Frontier budget exceeded; no accepted result.')
def caps(strategy,table):
 out={}
 for card in strategy.cards:
  values=table[len(card)];r=next(i for i,p in enumerate(values) if p)
  if any(p<=0 for p in values[r:]):raise ValueError('Zero-hit threshold reduction is not valid for this paytable.')
  out[frozenset(card)]=r-1
 return sorted(out.items(),key=lambda x:(len(x[0]),sorted(x[0])))
def multiply(a,b):
 out=[0]*min(21,len(a)+len(b)-1)
 for i,x in enumerate(a):
  for j,y in enumerate(b[:21-i]):
   if i+j<len(out):out[i+j]+=x*y
 return tuple(out)
def frontier(strategy,table,budget=None):
 """Eliminate membership regions, forgetting a card immediately at its last region."""
 b=budget or Budget();constraints=caps(strategy,table);regions=Counter(tuple(i for i,(c,_) in enumerate(constraints) if v in c) for v in range(1,81));remaining=set(regions);order=[];active=set()
 # Deterministic low-frontier ordering; label-independent signatures resolve useful ties.
 while remaining:
  def score(mask):
   after=active|set(mask);after={i for i in after if any(i in r for r in remaining if r!=mask)}
   return (len(after),len(active|set(mask)),mask)
  mask=min(remaining,key=score);order.append((mask,regions[mask]));remaining.remove(mask);active|=set(mask);active={i for i in active if any(i in r for r in remaining)}
 last={i:max(j for j,(mask,n) in enumerate(order) if i in mask) for i in range(len(constraints))};active=();dp={(0,()):1}
 for step,(mask,n) in enumerate(order):
  union=tuple(sorted(set(active)|set(mask)));nextactive=tuple(i for i in union if last[i]>step);positions={i:p for p,i in enumerate(active)};nextdp=defaultdict(int)
  for (k,state),w in dp.items():
   b.tick();hits={i:(state[positions[i]] if i in positions else 0) for i in union}
   maximum=min([n,20-k]+[constraints[i][1]-hits[i] for i in mask])
   for chosen in range(maximum+1):
    new=tuple(hits[i]+(chosen if i in mask else 0) for i in nextactive);nextdp[k+chosen,new]+=w*comb(n,chosen)
  dp=nextdp;active=nextactive;b.observe(len(dp))
 poly=tuple(dp.get((k,()),0) for k in range(21));return poly,{'method':'membership-frontier','work':b.work,'peak_states':b.peak,'regions':len(order)}
def deletion(strategy,table,budget=None,variable_order="max-degree"):
 """Deletion/contraction with residual-constraint reduction and component factorization."""
 b=budget or Budget();initial=tuple((sum(1<<(v-1) for v in c),q) for c,q in caps(strategy,table))
 def normal(items):
  d={}
  for m,q in items:
   if q<0:return None
   if m.bit_count()>q:d[m]=min(q,d.get(m,q))
  # A subset constraint with no greater capacity makes the subset redundant.
  return tuple(sorted((m,q) for m,q in d.items() if not any(m!=z and m&z==m and q>=r for z,r in d.items())))
 @lru_cache(None)
 def visit(vertices,items):
  b.tick();items=normal(items)
  if items is None:return (0,)
  used=0
  for m,q in items:used|=m
  free=(vertices&~used).bit_count()
  if free:
   return multiply(tuple(comb(free,k) for k in range(min(20,free)+1)),visit(used,items))
  if not vertices:return (1,)
  # Factor disconnected constraints before selecting a deletion variable.
  pending=list(items);parts=[]
  while pending:
   chosen=[pending.pop()];component=chosen[0][0]
   while True:
    connected=[x for x in pending if x[0]&component]
    if not connected:break
    pending=[x for x in pending if not x[0]&component];chosen.extend(connected)
    for m,q in connected:component|=m
   parts.append((component,tuple(chosen)))
  if len(parts)>1:
   result=(1,)
   for mask,part in parts:result=multiply(result,visit(mask,part))
   return result
  degree=Counter()
  for m,q in items:
   while m:
    bit=m&-m;degree[bit]+=1;m-=bit
  bit=min(degree) if variable_order=="ascending" else max(degree,key=lambda z:(degree[z],z));rest=vertices^bit
  no=visit(rest,tuple((m&~bit,q) for m,q in items));yes=visit(rest,tuple((m&~bit,q-(1 if m&bit else 0)) for m,q in items));out=[0]*min(21,max(len(no),len(yes)+1))
  for k,x in enumerate(no):out[k]+=x
  for k,x in enumerate(yes[:20]):out[k+1]+=x
  return tuple(out)
 poly=visit((1<<80)-1,initial);b.observe(visit.cache_info().currsize)
 return tuple(poly)+(0,)*(21-len(poly)),{'method':'deletion-contraction-components','variable_order':variable_order,'work':b.work,'cache_states':visit.cache_info().currsize}
