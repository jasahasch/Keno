"""Direct strict-grouping entry point for future fresh disposable runs."""
import argparse
import json, os, signal, time
from pathlib import Path
from collections import Counter
from hashlib import sha256
import incidence86 as base
import incidence86_grouped_strict as grouped
from incidence86_post_pr9 import write_evidence

OUT=base.ROOT/'docs/incidence86-scenario1-evidence'
FILES=['docs/incidence86-coverage.json','docs/incidence86-continuation.json',
       'docs/incidence86-priority.json','docs/incidence86-post-pr9-evidence/ledger.json']
def key(r): return tuple(map(tuple,r['shape']))
def load():
    data=[json.loads((base.ROOT/f).read_text()) for f in FILES]
    live={key(r):r for r in data[0]['geometries_ledger']}
    assert len(live)==725
    for d in data[1:]:
        assert len({key(a) for a in d['attempts']})==len(d['attempts'])
        for a in d['attempts']:
            k=key(a)
            assert live[k]['status']==a['baseline_status'] and a['baseline_status'].startswith('open-')
            live[k]=dict(live[k],**a)
    assert Counter(r['status'] for r in live.values())=={'certified-no-improvement':568,'open-resource-limit':157}
    assert data[1]['baseline_sha256']==sha256((base.ROOT/FILES[0]).read_bytes()).hexdigest()
    for index,field in [(1,'continuation_sha256'),(2,'priority_sha256')]:
        assert data[3][field]==sha256((base.ROOT/FILES[index]).read_bytes()).hexdigest()
    keys=json.loads((base.ROOT/'docs/incidence86-post-pr9-evidence/keys.json').read_text())
    priority=sorted(tuple(map(tuple,k)) for k in keys['deferred_priority'])
    remaining={k for k,r in live.items() if r['status'].startswith('open-')}
    assert remaining=={tuple(map(tuple,k)) for k in keys['still_open']}
    assert len(priority)==7 and set(priority)<=remaining
    secondary=sorted(remaining-set(priority),key=lambda k:(live[k]['stage']!='packed-replay',live[k]['largest_component'],max(live[k]['component_cycle_ranks']),k))
    assert len(secondary)==150
    return live,priority,secondary

def bound(k,packed,new):
    old=base.cycle85.envelope
    try:
        if new: base.cycle85.envelope=grouped.envelope
        return base.bound(k,packed,max(sum(map(len,g))-(1+max(map(max,g)))-len(g)+1 for g in base.b.groups(k))<=1)
    finally: base.cycle85.envelope=old

def main():
    assert __debug__
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=OUT,
                        help='new evidence directory directly under the worktree docs directory')
    output = parser.parse_args().output_dir.absolute()
    if output.parent.resolve() != OUT.parent.resolve() or output.name.startswith('.'):
        parser.error('--output-dir must be a new directory directly under docs/')
    started=time.monotonic(); deadline=started+400
    live,priority,secondary=load(); original=dict(live)
    try:
        output.mkdir(exist_ok=False)
    except FileExistsError:
        parser.error('--output-dir already exists; select a new directory')
    attempts=[]; replays=[]
    def expired(*args):raise TimeoutError('per-key computational cap')
    signal.signal(signal.SIGALRM,expired)
    signal.setitimer(signal.ITIMER_REAL,30)
    try:
        archived=json.loads((base.b.OUT/'coverage-final.json').read_text())
        source={key(r) for r in archived['geometries']}
        assert len(source)==167 and source==set(base.b.shapes85())
        assert base.lift(source)==base.partition_enumeration()==set(live)
    finally: signal.setitimer(signal.ITIMER_REAL,0)
    table=sha256((base.ROOT/'outputs/keno-expanded-paytables.json').read_bytes()).hexdigest()
    assert table=='d12c1a7588b93d8e2fff3061d4c89b8b3a7c9fd6d9b386460952f2b05fe8cbe1'
    phase_deadline=min(deadline,time.monotonic()+315)
    for group,targets in [(1,priority),(2,secondary)]:
        for k in targets:
            remaining=(phase_deadline if group==1 else deadline)-time.monotonic()
            if remaining<=0:break
            budget=min(45 if group==1 else 1.5,remaining)
            a=dict(shape=k,priority_group=group,baseline_status=live[k]['status'],
                   previous_stopping_stage=live[k]['stage'],budget_seconds=budget,
                   method='structurally-grouped-conditional-tree-cycle' if group==1 else 'legacy-conditional-or-full-profiles',
                   status='open-resource-limit',stage='ordinary')
            tick=time.monotonic(); signal.setitimer(signal.ITIMER_REAL,budget)
            try:
                ordinary=bound(k,False,group==1)
                a['stage']='packed-replay'
                packed=bound(k,True,group==1)
                assert ordinary==packed
                a.update(lower=ordinary[0],combined_totals=ordinary[1],stage='finished',
                         status='certified-no-improvement' if ordinary[0]>=base.b.RECORD else 'open-envelope')
                replays.append(dict(shape=k,ordinary_lower=ordinary[0],ordinary_totals=ordinary[1],
                                    packed_lower=packed[0],packed_totals=packed[1],carry_width=base.b.WIDTH))
            except TimeoutError:pass
            finally:signal.setitimer(signal.ITIMER_REAL,0)
            a['elapsed_seconds']=time.monotonic()-tick
            attempts.append(a);live[k]=dict(live[k],**a)
            with (output/'attempts.txt').open('a') as stream:
                stream.write(json.dumps(a)+'\n');stream.flush();os.fsync(stream.fileno())
            write_evidence(output/'arithmetic-replay.json',json.dumps(replays,indent=2)+'\n')
            print(len(attempts),group,a['stage'],a['status'],flush=True)
    attempted={key(a) for a in attempts}
    after=dict(Counter(r['status'] for r in live.values()))
    elapsed=time.monotonic()-started
    report=dict(source_commit_attested='90bcc1206db5a4ae77d75a4a013277fa910543e8',
        supervisor_attestation=dict(hostname='SynFart',issue=12,digest='08413633fb2a01415425e1e16577765dd88f39444009b2d0829bcd0344198966',approval_comment=6805876841,mode='codex'),
        source_hashes={f:sha256((base.ROOT/f).read_bytes()).hexdigest() for f in FILES},
        tool_hashes={f:sha256((base.ROOT/f).read_bytes()).hexdigest() for f in ['tools/incidence86_run_strict.py','tools/incidence86_grouped_strict.py','tools/incidence86.py']},
        paytable_sha256=table,before=dict(Counter(r['status'] for r in original.values())),after=after,
        budgets=dict(outer_seconds=900,computational_cap_seconds=400,priority_cap_seconds=315,priority_key_seconds=45,secondary_key_seconds=1.5),
        priority_active_seconds=sum(a['elapsed_seconds'] for a in attempts if a['priority_group']==1),
        elapsed_seconds=elapsed,throughput=len(attempts)/elapsed,attempts=attempts,
        unattempted=[k for k in priority+secondary if k not in attempted],census_keys=725,enumeration_agreement=True)
    assert sum(after.values())==725
    write_evidence(output/'ledger.json',json.dumps(report,indent=2)+'\n')
    keys=dict(attempted=[key(a) for a in attempts],newly_certified=[key(a) for a in attempts if a['status']=='certified-no-improvement'],
              still_open=sorted(k for k,r in live.items() if r['status'].startswith('open-')),unattempted=report['unattempted'],
              priority=priority)
    write_evidence(output/'keys.json',json.dumps(keys,indent=2)+'\n')
    print(json.dumps(dict(after=after,elapsed=elapsed,attempted=len(attempts))))
if __name__=='__main__':main()
