"""Finite exact partition solver: optimize a graph certificate, never the portfolio objective."""
from itertools import combinations,product
from .overlap import sizes

def partitions(card,capacities):
 card=tuple(sorted(card));seen=set()
 def rec(remaining,j,groups):
  if j==len(capacities):
   code=tuple(sorted(groups))
   if code not in seen:seen.add(code);yield code
   return
  size=capacities[j]
  for chunk in combinations(remaining,size):
   chosen=set(chunk);yield from rec(tuple(x for x in remaining if x not in chosen),j+1,groups+(chunk,))
 return list(rec(card,0,()))
def edges(groups):return frozenset((u,v) for g in groups for u,v in combinations(sorted(g),2))
def solve(strategy,table,indices=(18,19),max_nodes=100000):
 groups=[]
 for card in strategy.cards:
  start=0;local=[]
  for size in sizes(len(card),table):local.append(tuple(card[start:start+size]));start+=size
  groups.append(tuple(local))
 options=[partitions(strategy.cards[i],sizes(len(strategy.cards[i]),table)) for i in indices];base=edges([g for i,gs in enumerate(groups) if i not in indices for g in gs]);best=edges([g for gs in groups for g in gs]);best_groups=groups[:];nodes=leaves=pruned=0;complete=True
 def walk(level,current,chosen):
  nonlocal best,best_groups,nodes,leaves,pruned,complete
  nodes+=1
  if nodes>max_nodes:complete=False;return
  if len(current)>=len(best):
   remaining=1
   for opt in options[level:]:remaining*=len(opt)
   pruned+=remaining;return
  if level==len(indices):
   leaves+=1;best=current;best_groups=groups[:]
   for index,gs in zip(indices,chosen):best_groups[index]=gs
   return
  for gs in options[level]:
   if not complete:return
   walk(level+1,current|edges(gs),chosen+[gs])
 walk(0,base,[])
 return {'indices':list(indices),'options_per_card':list(map(len,options)),'nodes':nodes,'evaluated_leaves':leaves,'pruned_leaves':pruned,'complete_partition_scope':complete,'minimum_edges':len(best),'groups':best_groups,'scope':'Only balanced graph partitions of the specified fixed cards; no claim of global layout optimization.'}
def replay(strategy,table,result):
 opts=[partitions(strategy.cards[i],sizes(len(strategy.cards[i]),table)) for i in result['indices']];fixed=[g for i,gs in enumerate(result['groups']) if i not in result['indices'] for g in gs];best=None;count=0
 for choices in product(*opts):
  value=len(edges(fixed+[g for gs in choices for g in gs]));best=value if best is None else min(best,value);count+=1
 assert result['complete_partition_scope'] and best==result['minimum_edges']
 assert count==result['evaluated_leaves']+result['pruned_leaves']
 return {'passed':True,'exhaustive_partition_combinations':count,'minimum_edges':best}
