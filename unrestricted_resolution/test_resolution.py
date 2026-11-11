import unittest,sys,json,random
from pathlib import Path
from math import comb
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'spot_strategy_framework'))
from spot_strategy.model import Strategy,Paytable
from spot_strategy.canonical import canonical as oldcanonical
from .zero import frontier,deletion,Budget,Limit
from .incidence import canonical
from .overlap import witness,verify
from .partition_solver import solve,replay
TABLE=Paytable(ROOT/'outputs/keno-expanded-paytables.json')
class Tests(unittest.TestCase):
 def test_all_spot_thresholds(self):
  for s in range(2,11):
   strategy=Strategy((tuple(range(1,s+1)),)*20);a,_=frontier(strategy,TABLE);b,_=deletion(strategy,TABLE);self.assertEqual(a,b)
   expected=sum(comb(s,h)*comb(80-s,20-h) for h in range(TABLE.first_positive(s)));self.assertEqual(a[20],expected)
 def test_exhaustive_draw_oracle(self):
  # All pairs of cards from a fixed four-number universe, all supports and repeats.
  from itertools import combinations,combinations_with_replacement
  for cards in combinations_with_replacement(list(combinations(range(1,5),2)),2):
   strategy=Strategy(cards);a,_=frontier(strategy,TABLE);b,_=deletion(strategy,TABLE);oracle=[0]*21
   for mask in range(16):
    chosen={v for v in range(1,5) if mask>>(v-1)&1}
    if all(TABLE[len(c)][len(chosen&set(c))]==0 for c in cards):
     for k in range(len(chosen),21):oracle[k]+=comb(76,k-len(chosen))
   self.assertEqual(tuple(oracle),a);self.assertEqual(a,b)
 def test_relabeling_and_payout_preservation(self):
  rng=random.Random(1129)
  for _ in range(12):
   strategy=Strategy(tuple(tuple(sorted(rng.sample(range(1,11),rng.randint(2,5)))) for i in range(5)));labels=list(range(1,81));rng.shuffle(labels);cards=[tuple(labels[v-1] for v in c) for c in strategy.cards];rng.shuffle(cards);other=Strategy(tuple(cards))
   self.assertEqual(canonical(strategy)['id'],canonical(other)['id']);self.assertEqual(oldcanonical(strategy)[0],oldcanonical(other)[0]);self.assertEqual(frontier(strategy,TABLE)[0],deletion(other,TABLE)[0])
   from spot_strategy.engine import ExactEngine
   from spot_strategy.model import Limits
   import tempfile
   with tempfile.TemporaryDirectory() as directory:
    engine=ExactEngine(TABLE,Path(directory));self.assertEqual(engine.primary(strategy,Limits()).gross,engine.primary(other,Limits()).gross)
 def test_ir_exact_classes(self):
  from itertools import combinations,combinations_with_replacement
  groups={};oldgroups={}
  for cards in combinations_with_replacement(list(combinations(range(1,5),2)),2):
   s=Strategy(cards);groups.setdefault(canonical(s)['id'],[]).append(s);oldgroups.setdefault(oldcanonical(s)[0],[]).append(s)
  self.assertEqual(len(groups),3);self.assertEqual(len(oldgroups),3);self.assertEqual(sorted(map(len,groups.values())),sorted(map(len,oldgroups.values())))
 def test_large_chain_symmetry(self):
  s=Strategy(tuple(tuple(range(3*i+1,3*i+8)) for i in range(20)));t=Strategy(tuple(tuple(81-v for v in c) for c in reversed(s.cards)));self.assertEqual(canonical(s)['id'],canonical(t)['id'])
 def test_limits_do_not_issue_proof(self):
  with self.assertRaises(Limit):canonical(Strategy(((1,2),(2,3),(3,4),(1,4))),1)
  with self.assertRaises(Limit):frontier(Strategy(((1,2),(3,4))),TABLE,Budget(states=1))
 def test_overlap_witnesses(self):
  for s in range(2,11):
   for t in range(s,11):
    for n in range(min(s,t)+1):self.assertTrue(verify(witness(s,t,n,TABLE),TABLE))
 def test_finite_solver_certificate(self):
  cards=[tuple(range(4*i+1,4*i+5)) for i in range(18)]+[(1,2,3,4,73,74,75),(1,2,3,4,76,77,78)];s=Strategy(tuple(cards));result=solve(s,TABLE);self.assertTrue(replay(s,TABLE,result)['passed']);self.assertLessEqual(result['minimum_edges'],120)
if __name__=='__main__':unittest.main()
