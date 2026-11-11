"""Bounded Issue 14 run; new evidence only, fresh per-case arithmetic processes."""
import json, os, signal, subprocess, sys, time
from pathlib import Path
from hashlib import sha256
from collections import Counter
import incidence86 as base
ROOT=base.ROOT
OUT=ROOT/'docs/incidence86-issue14-evidence'
JOURNAL_NAME='attempts.txt'
PRIORITY=((0,1),(0,1),(0,2),(1,3),(2,3),(4,5))
FILES=['docs/incidence86-coverage.json','docs/incidence86-continuation.json','docs/incidence86-priority.json','docs/incidence86-post-pr9-evidence/ledger.json','docs/incidence86-scenario1-evidence/ledger.json']
def key(a):return tuple(map(tuple,a['shape']))
def save(name,data):
 p=OUT/name
 with p.open('w') as f:json.dump(data,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def worker():
 k=tuple(map(tuple,json.loads(sys.argv[2])));budget=float(sys.argv[3]);r={'shape':k,'stage':'ordinary','status':'open-resource-limit'}
 def stop(*a):raise TimeoutError()
 signal.signal(signal.SIGALRM,stop);signal.setitimer(signal.ITIMER_REAL,budget);start=time.monotonic()
 try:
  ordinary=base.bound(k,False,False);r['ordinary']=ordinary;r['stage']='packed-replay'
  packed=base.bound(k,True,False);r['packed']=packed
  assert ordinary==packed
  r.update(stage='finished',status='candidate-exclusion' if ordinary[0]>=base.b.RECORD else 'open-envelope')
 except TimeoutError:r['timeout_stage']=r['stage']
 finally:signal.setitimer(signal.ITIMER_REAL,0)
 r['elapsed_seconds']=time.monotonic()-start;print(json.dumps(r),flush=True)
def main():
 start=time.monotonic();OUT.mkdir(exist_ok=False)
 baseline={str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts and OUT not in p.parents}
 save('preservation-baseline.json',baseline)
 data=[json.loads((ROOT/f).read_text()) for f in FILES];hashes={f:sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
 live={key(r):r for r in data[0]['geometries_ledger']};reconciliation=[]
 for i,d in enumerate(data[1:],1):
  before=dict(Counter(r['status'] for r in live.values()));seen=set()
  for a in d['attempts']:
   k=key(a);assert k not in seen;seen.add(k);assert live[k]['status']==a['baseline_status'];assert a['baseline_status'].startswith('open-');live[k]=dict(live[k],**a)
  for field,path in [('baseline_sha256',FILES[0]),('continuation_sha256',FILES[1]),('priority_sha256',FILES[2])]:
   if field in d:assert d[field]==hashes[path]
  for f,h in d.get('source_hashes',{}).items():assert sha256((ROOT/f).read_bytes()).hexdigest()==h
  reconciliation.append(dict(source=FILES[i],sha256=hashes[FILES[i]],before=before,after=dict(Counter(r['status'] for r in live.values())),attempts=len(seen)))
 before=dict(Counter(r['status'] for r in live.values()));assert before=={'certified-no-improvement':575,'open-resource-limit':150}
 keys=json.loads((ROOT/'docs/incidence86-scenario1-evidence/keys.json').read_text());opened={k for k,r in live.items() if r['status'].startswith('open-')};assert opened=={tuple(map(tuple,k)) for k in keys['still_open']};assert PRIORITY in opened
 table=sha256((ROOT/'outputs/keno-expanded-paytables.json').read_bytes()).hexdigest();assert table=='d12c1a7588b93d8e2fff3061d4c89b8b3a7c9fd6d9b386460952f2b05fe8cbe1'
 save('reconciliation.json',reconciliation)
 ordered=[PRIORITY]+sorted(opened-{PRIORITY},key=lambda k:(live[k]['stage']!='packed-replay',live[k]['largest_component'],max(live[k]['component_cycle_ranks']),k))
 attempts=[];audits=[]
 def compute(k,budget):
  p=subprocess.run([sys.executable,__file__,'worker',json.dumps(k),str(budget)],capture_output=True,text=True,timeout=budget+3,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
  assert p.returncode==0,(p.returncode,p.stderr)
  return json.loads(p.stdout)
 for index,k in enumerate(ordered):
  if time.monotonic()-start>=480:break
  budget=30 if index==0 else 1.5
  r=compute(k,budget);r.update(baseline_status=live[k]['status'],previous_stopping_stage=live[k]['stage'],budget_seconds=budget,method='full-component-profile-envelope')
  # Persist the priority reproduction before its fresh-process replay or other keys.
  with (OUT/JOURNAL_NAME).open('a') as f:f.write(json.dumps(r)+'\n');f.flush();os.fsync(f.fileno())
  if index==0 or r['status']=='candidate-exclusion':
   audit=compute(k,30 if index==0 else 10);audits.append(audit);save('replay-audit.json',audits)
   if r['stage']==audit['stage']=='finished':
    assert r['ordinary']==r['packed']==audit['ordinary']==audit['packed']
    r['status']='certified-no-improvement' if r['ordinary'][0]>=base.b.RECORD else 'open-envelope'
   else:r['status']='open-resource-limit'
  attempts.append(r);live[k]=dict(live[k],**r);save('attempts.json',attempts)
  print(index+1,r['stage'],r['status'],flush=True)
  if index==0:save('priority-result.json',dict(reproduction=r,replay=audits[0],expected=[8237478838272,45],matches_expected=r.get('ordinary')==[8237478838272,45] and r['status']=='certified-no-improvement'))
 after=dict(Counter(r['status'] for r in live.values()));assert sum(after.values())==725
 attempted={key(a) for a in attempts}
 save('keys.json',dict(attempted=[key(a) for a in attempts],newly_certified=[key(a) for a in attempts if a['status']=='certified-no-improvement'],still_open=sorted(k for k,r in live.items() if r['status'].startswith('open-')),unattempted=[k for k in ordered if k not in attempted]))
 save('ledger.json',dict(source_commit_attested='6dc6ac5a7d60db0aa9948f1b3cc99b03d66052c0',supervisor_attestation=dict(hostname='SynFart',issue=14,digest='c7547512fbfb7e4f41faf326c6a9881bad0b17a3a8d1b81ba6a624ac2615f9f2',approval_comment=6806837001,mode='codex'),source_hashes=hashes,tool_hashes={str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest() for p in list((ROOT/'tools').glob('*.py'))+list((ROOT/'outputs/phase4-discovery').glob('*.py'))},python=sys.version,paytable_sha256=table,before=before,after=after,attempts=attempts,budgets=dict(outer=900,initial_computation_cap=600,local_pass_cap=480,priority=30,secondary=1.5,secondary_replay=10),elapsed_seconds=time.monotonic()-start))
 save('preservation.json',dict(checked=len(baseline),unchanged=all((ROOT/p).is_file() and sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in baseline.items()),trusted_host_check='required after isolation; unavailable inside namespace'))
if __name__=='__main__':
 assert __debug__
 if len(sys.argv)>1:worker()
 else:main()
