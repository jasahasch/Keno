"""Read-only validation of Issue 14 reconciliation, ordering, persistence and replay."""
import json, sys, time
from collections import Counter
from hashlib import sha256
from pathlib import Path
import incidence86_issue14 as run

def main():
 start=time.monotonic();root=run.ROOT;out=run.OUT
 ledger=json.loads((out/'ledger.json').read_text());keys=json.loads((out/'keys.json').read_text())
 # Preserve the execution hashes and verify the reviewed packaging revisions.
 tool_hashes = dict(ledger['tool_hashes'])
 review_hashes = ledger.get('review_tool_hashes', {})
 assert set(review_hashes) <= {str(Path(f).relative_to(root)) for f in (run.__file__, __file__)}
 assert review_hashes.keys() <= tool_hashes.keys()
 tool_hashes.update(review_hashes)
 for f, h in {**ledger['source_hashes'], **tool_hashes}.items():
  assert sha256((root/f).read_bytes()).hexdigest() == h
 files=[json.loads((root/f).read_text()) for f in run.FILES]
 live={run.key(a):a for a in files[0]['geometries_ledger']}
 for d in files[1:]:
  seen=set()
  for a in d['attempts']:
   k=run.key(a);assert k not in seen;seen.add(k);assert live[k]['status']==a['baseline_status'];assert live[k]['status'].startswith('open-');live[k]=dict(live[k],**a)
 assert dict(Counter(r['status'] for r in live.values()))==ledger['before']
 opened={k for k,r in live.items() if r['status'].startswith('open-')}
 order=[run.PRIORITY]+sorted(opened-{run.PRIORITY},key=lambda k:(live[k]['stage']!='packed-replay',live[k]['largest_component'],max(live[k]['component_cycle_ranks']),k))
 attempts=ledger['attempts'];assert attempts==json.loads((out/'attempts.json').read_text())
 assert [run.key(a) for a in attempts]==order[:len(attempts)]
 journal=[json.loads(line) for line in (out/run.JOURNAL_NAME).read_text().splitlines()];assert len(journal)==len(attempts)
 audits=json.loads((out/'replay-audit.json').read_text());replay={run.key(a):a for a in audits};assert len(replay)==len(audits)
 assert run.PRIORITY in replay
 for i,(a,j) in enumerate(zip(attempts,journal)):
  k=run.key(a);assert a['baseline_status']==live[k]['status']=='open-resource-limit';assert a['previous_stopping_stage']==live[k]['stage']
  assert {f:v for f,v in a.items() if f!='status'}=={f:v for f,v in j.items() if f!='status'}
  assert a['budget_seconds']==(30 if i==0 else 1.5)
  if a['status']=='certified-no-improvement':
   r=replay[k];assert a['stage']==r['stage']=='finished';assert a['ordinary']==a['packed']==r['ordinary']==r['packed'];assert a['ordinary'][0]>=run.base.b.RECORD and a['ordinary'][1]>0
  else:assert a['status'].startswith('open-')
  live[k]=dict(live[k],**a)
 assert dict(Counter(r['status'] for r in live.values()))==ledger['after'];assert sum(ledger['after'].values())==725
 assert keys['attempted']==[a['shape'] for a in attempts]
 assert keys['newly_certified']==[a['shape'] for a in attempts if a['status']=='certified-no-improvement']
 assert keys['still_open']==json.loads(json.dumps(sorted(k for k,r in live.items() if r['status'].startswith('open-'))))
 assert keys['unattempted']==json.loads(json.dumps(order[len(attempts):]))
 priority=json.loads((out/'priority-result.json').read_text());assert priority['matches_expected'];assert attempts[0]['ordinary']==[8237478838272,45]
 archived=json.loads((run.base.b.OUT/'coverage-final.json').read_text());source={run.key(a) for a in archived['geometries']}
 assert len(source)==167 and source==set(run.base.b.shapes85())
 assert run.base.lift(source)==run.base.partition_enumeration()==set(live)
 baseline = json.loads((out/'preservation-baseline.json').read_text())
 for f, h in baseline.items():
  if f in review_hashes:
   assert h == ledger['tool_hashes'][f]
  else:
   assert (root/f).is_file() and sha256((root/f).read_bytes()).hexdigest() == h
 return dict(status='passed',census=725,before=ledger['before'],after=ledger['after'],attempted=len(attempts),unattempted=len(keys['unattempted']),separate_replays=len(audits),all_new_exclusions_separately_replayed=True,independent_geometry_generators_agree=True,preserved_files=len(baseline),elapsed_seconds=time.monotonic()-start)
if __name__=='__main__':print(json.dumps(main(),indent=2))
