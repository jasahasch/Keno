"""Read-only structural and required separate arithmetic audit of Scenario 1 delta."""
import argparse,json,time,signal
from math import isfinite
from collections import Counter
from hashlib import sha256
from pathlib import Path
import incidence86_scenario1 as run
import incidence86_grouped_strict as strict

def main():
    assert __debug__
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=Path, default=run.OUT,
                        help='directory containing the ledger, journal, arithmetic records and key lists')
    parser.add_argument('--replay-seconds', type=float, default=150)
    args = parser.parse_args()
    if not isfinite(args.replay_seconds) or args.replay_seconds <= 0:
        parser.error('--replay-seconds must be finite and positive')
    start = time.monotonic()
    out = args.evidence_dir
    report = json.loads((out/'ledger.json').read_text())
    live,priority,secondary=run.load(); old=dict(live)
    assert report['before']==dict(Counter(r['status'] for r in live.values()))
    for f,h in {**report['source_hashes'],**report['tool_hashes']}.items():
        assert sha256((run.base.ROOT/f).read_bytes()).hexdigest()==h
    attempts=report['attempts'];seen=[run.key(a) for a in attempts]
    assert len(seen)==len(set(seen))
    assert seen[:7]==priority
    assert seen[7:]==secondary[:len(seen)-7]
    assert [json.loads(line) for line in (out/'attempts.txt').read_text().splitlines()]==attempts
    arithmetic=json.loads((out/'arithmetic-replay.json').read_text())
    replay={run.key(a):a for a in arithmetic};assert len(replay)==len(arithmetic)
    assert set(replay)=={run.key(a) for a in attempts if a['stage']=='finished'}
    for a in attempts:
        k=run.key(a);assert live[k]['status']==a['baseline_status']=='open-resource-limit'
        assert a['previous_stopping_stage']==live[k]['stage']
        assert 0<a['budget_seconds']<=(45 if a['priority_group']==1 else 1.5)
        if a['stage']=='finished':
            r=replay[k]
            assert r['ordinary_lower']==r['packed_lower']==a['lower']
            assert r['ordinary_totals']==r['packed_totals']==a['combined_totals']>0
            assert a['status']==('certified-no-improvement' if a['lower']>=run.base.b.RECORD else 'open-envelope')
        else:assert a['status']=='open-resource-limit'
        live[k]=dict(live[k],**a)
    assert report['after']==dict(Counter(r['status'] for r in live.values()))
    assert sum(report['after'].values())==725
    assert all(live[k]==v for k,v in old.items() if v['status']=='certified-no-improvement')
    keys=json.loads((out/'keys.json').read_text())
    assert keys['attempted']==[a['shape'] for a in attempts]
    assert keys['newly_certified']==[a['shape'] for a in attempts if a['status']=='certified-no-improvement']
    assert keys['still_open']==json.loads(json.dumps(sorted(k for k,r in live.items() if r['status'].startswith('open-'))))
    assert keys['unattempted']==report['unattempted']==json.loads(json.dumps([k for k in priority+secondary if k not in seen]))
    assert report['priority_active_seconds']<350
    assert report['elapsed_seconds']<551
    def expired(*args):raise TimeoutError('separate audit replay cap')
    signal.signal(signal.SIGALRM,expired);deadline=time.monotonic()+args.replay_seconds
    run.grouped=strict
    separate=[]
    for a in attempts:
        if a['status']!='certified-no-improvement':continue
        remaining=deadline-time.monotonic()
        if remaining<=0:break
        signal.setitimer(signal.ITIMER_REAL,remaining)
        try:
            ordinary=run.bound(run.key(a),False,a['priority_group']==1)
            packed=run.bound(run.key(a),True,a['priority_group']==1)
            assert ordinary==packed==(a['lower'],a['combined_totals'])
            separate.append(dict(shape=a['shape'],lower=ordinary[0],combined_totals=ordinary[1]))
        except TimeoutError:break
        finally:signal.setitimer(signal.ITIMER_REAL,0)
    accepted=[a for a in attempts if a['status']=='certified-no-improvement']
    return dict(structural_checks='passed',before=report['before'],after=report['after'],
                attempted=len(attempts),newly_certified=len(accepted),unattempted=len(report['unattempted']),
                arithmetic_records=len(arithmetic),separate_replay=separate,
                separate_replay_complete=len(separate)==len(accepted),elapsed_seconds=time.monotonic()-start)
if __name__ == '__main__':
    audit = main()
    print(json.dumps(audit, indent=2))
    if not audit['separate_replay_complete']:
        raise SystemExit('Arithmetic replay incomplete')
