"""Exact card individualization/refinement; refuses an uncertified ID at the budget."""
from collections import Counter
from hashlib import sha256
import json
from .zero import Limit

def canonical(strategy,max_nodes=100000):
 from spot_strategy.canonical import components
 from spot_strategy.model import Strategy
 groups=components(strategy)
 if len(groups)>1:
  codes=[];used=0
  for group in groups:
   if len(group)==1:codes.append(json.dumps(['single',len(group[0])]))
   else:
    child=canonical(Strategy(group),max_nodes-used);codes.append(child['encoding']);used+=child['nodes']
  encoded=json.dumps(['IR-components-v1',80-len(strategy.support),sorted(codes)],separators=(',',':'))
  return {'id':sha256(encoded.encode()).hexdigest(),'encoding':encoded,'nodes':used,'scope':'Exact under active-card and number permutations; no fallback IDs.'}
 cards=tuple(frozenset(c) for c in strategy.cards);vertices=sorted(strategy.support);nodes=0
 initial=tuple(tuple(i for i,c in enumerate(cards) if len(c)==s) for s in sorted(set(map(len,cards))))
 def refine(part):
  while True:
   color={i:j for j,cell in enumerate(part) for i in cell}
   vc={v:tuple(sorted(Counter(color[i] for i,c in enumerate(cards) if v in c).items())) for v in vertices}
   nxt=[]
   for cell in part:
    groups={}
    for i in cell:groups.setdefault(tuple(sorted(Counter(vc[v] for v in cards[i]).items())),[]).append(i)
    nxt.extend(tuple(groups[k]) for k in sorted(groups))
   nxt=tuple(nxt)
   if nxt==part:return part
   part=nxt
 def rec(part):
  nonlocal nodes
  nodes+=1
  if nodes>max_nodes:raise Limit('Canonical individualization budget exceeded; no exact ID issued.')
  part=refine(part);cells=[x for x in part if len(x)>1]
  if not cells:
   order=[x[0] for x in part];regions=Counter(sum(1<<j for j,i in enumerate(order) if v in cards[i]) for v in vertices)
   return tuple(len(cards[i]) for i in order),tuple(sorted(regions.items()))
  cell=min(cells,key=lambda x:(len(x),part.index(x)));pos=part.index(cell);representatives={cards[i]:i for i in cell};best=None
  for i in representatives.values():
   value=rec(part[:pos]+((i,),tuple(j for j in cell if j!=i))+part[pos+1:])
   if best is None or value<best:best=value
  return best
 code=rec(initial);encoded=json.dumps(['IR-incidence-v1',80-len(vertices),code],separators=(',',':'))
 return {'id':sha256(encoded.encode()).hexdigest(),'encoding':encoded,'nodes':nodes,'scope':'Exact under active-card and number permutations; no fallback IDs.'}
