"""Strict attachment-preserving priority replay; flushed independent arithmetic evidence."""
import json,os,time,signal
import incidence86_scenario1 as run
import incidence86_grouped_strict as strict
from incidence86_post_pr9 import write_evidence

def main():
    start=time.monotonic();deadline=start+180
    _,priority,_=run.load();records=[]
    def expired(*args):raise TimeoutError('strict priority replay cap')
    signal.signal(signal.SIGALRM,expired)
    for k in priority:
        tick=time.monotonic();budget=min(45,deadline-tick)
        r=dict(shape=k,method='structurally-grouped-conditional-tree-cycle',budget_seconds=budget,status='open-resource-limit',stage='ordinary')
        if budget>0:
            signal.setitimer(signal.ITIMER_REAL,budget)
            old=run.base.cycle85.envelope
            try:
                run.base.cycle85.envelope=strict.envelope
                ordinary=run.base.bound(k,False,True)
                r['stage']='packed-replay'
                packed=run.base.bound(k,True,True)
                assert ordinary==packed
                r.update(stage='finished',ordinary_lower=ordinary[0],packed_lower=packed[0],
                         ordinary_totals=ordinary[1],packed_totals=packed[1],
                         status='certified-no-improvement' if ordinary[0]>=run.base.b.RECORD else 'open-envelope')
            except TimeoutError:pass
            finally:
                signal.setitimer(signal.ITIMER_REAL,0);run.base.cycle85.envelope=old
        r['elapsed_seconds']=time.monotonic()-tick
        records.append(r)
        write_evidence(run.OUT/'strict-arithmetic-replay.json',json.dumps(records,indent=2)+'\n')
        print(json.dumps(r),flush=True)
    print(json.dumps(dict(elapsed_seconds=time.monotonic()-start)))
if __name__=='__main__':main()
