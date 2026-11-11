"""Finalize provisional results only after structurally strict priority replay."""
import json
from collections import Counter
from hashlib import sha256
import incidence86_scenario1 as run
from incidence86_post_pr9 import write_evidence

def main():
    out=run.OUT;report=json.loads((out/'ledger.json').read_text())
    assert not (out/'diagnostic-ledger.json').exists(), 'already finalized'
    strict=json.loads((out/'strict-arithmetic-replay.json').read_text())
    _,priority,_=run.load();assert [run.key(r) for r in strict]==priority
    write_evidence(out/'diagnostic-ledger.json',json.dumps(report,indent=2)+'\n')
    write_evidence(out/'diagnostic-attempts.txt',(out/'attempts.txt').read_text())
    write_evidence(out/'diagnostic-arithmetic-replay.json',(out/'arithmetic-replay.json').read_text())
    ordinary_replay=json.loads((out/'arithmetic-replay.json').read_text())
    attempts=report['attempts'];assert [run.key(a) for a in attempts[:7]]==priority
    accepted=[]
    for a,r in zip(attempts[:7],strict):
        a['diagnostic_elapsed_seconds']=a['elapsed_seconds']
        a['diagnostic_status']=a['status']
        a.update(method=r['method'],status=r['status'],stage=r['stage'],elapsed_seconds=r['elapsed_seconds'],budget_seconds=r['budget_seconds'])
        a.pop('lower',None);a.pop('combined_totals',None)
        if r['stage']=='finished':
            assert r['ordinary_lower']==r['packed_lower']
            assert r['ordinary_totals']==r['packed_totals']>0
            a.update(lower=r['ordinary_lower'],combined_totals=r['ordinary_totals'])
            accepted.append(dict(shape=r['shape'],ordinary_lower=r['ordinary_lower'],packed_lower=r['packed_lower'],ordinary_totals=r['ordinary_totals'],packed_totals=r['packed_totals'],carry_width=81,method=r['method']))
    live,_,_=run.load()
    for a in attempts:live[run.key(a)]=dict(live[run.key(a)],**a)
    report['after']=dict(Counter(r['status'] for r in live.values()))
    report['priority_validation']='initial numerical-only grouping rejected; final priority status requires structurally strict replay'
    report['priority_active_seconds']=sum(a['elapsed_seconds']+a.get('diagnostic_elapsed_seconds',0) for a in attempts[:7])
    assert report['priority_active_seconds']<350
    report['tool_hashes'].update({f:sha256((run.base.ROOT/f).read_bytes()).hexdigest() for f in ['tools/incidence86_grouped_strict.py','tools/replay_incidence86_strict.py','tools/test_incidence86_grouped_strict.py']})
    replay=accepted+[r for r in ordinary_replay if run.key(r) not in set(priority)]
    write_evidence(out/'arithmetic-replay.json',json.dumps(replay,indent=2)+'\n')
    write_evidence(out/'attempts.txt',''.join(json.dumps(a)+'\n' for a in attempts))
    write_evidence(out/'ledger.json',json.dumps(report,indent=2)+'\n')
    keys=json.loads((out/'keys.json').read_text())
    keys.update(newly_certified=[a['shape'] for a in attempts if a['status']=='certified-no-improvement'],still_open=[json.loads(json.dumps(k)) for k,r in sorted(live.items()) if r['status'].startswith('open-')])
    write_evidence(out/'keys.json',json.dumps(keys,indent=2)+'\n')
    print(json.dumps(dict(after=report['after'],priority_active_seconds=report['priority_active_seconds'])))
if __name__=='__main__':main()
