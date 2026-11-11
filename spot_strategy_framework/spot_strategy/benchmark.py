"""Repeatable exact-engine benchmark; run with python -m spot_strategy.benchmark."""
import argparse,json,time,statistics,tempfile
from pathlib import Path
from .model import Paytable,Strategy,Limits,MachineProfile
from .engine import ExactEngine
from .history import references

def main():
    p=argparse.ArgumentParser();p.add_argument('--project-root',default=str(Path(__file__).resolve().parents[2]));p.add_argument('--out',required=True);a=p.parse_args();root=Path(a.project_root)
    rows=[];table=Paytable(root/'outputs/keno-expanded-paytables.json')
    with tempfile.TemporaryDirectory(prefix='keno-framework-benchmark-') as temp:
        engine=ExactEngine(table,Path(temp));limits=Limits(max_operations=30000000)
        for ref in references(root):
            if ref['label'] not in ('absolute-record-preserved','new-0'):continue
            s=Strategy.from_data(ref['cards']);times=[]
            for _ in range(3):
                start=time.perf_counter();counts=engine.primary(s,limits);times.append(time.perf_counter()-start)
            start=time.perf_counter();metrics,verification=engine.verify(s,counts,limits,MachineProfile().denominations);verify_seconds=time.perf_counter()-start
            expected={str(k):str(v) for k,v in ref['expected_gross_counts'].items() if int(v)}
            if counts.to_dict()['gross']!=expected:raise ValueError('Benchmark historical payout law differs.')
            rows.append({'case':ref['label'],'method':counts.method,'primary_trials_seconds':times,'primary_median_seconds':statistics.median(times),'independent_verification_seconds':verify_seconds,'gross_bins':len(counts.gross),'frequency':metrics['frequency'],'verification':verification,'scope':'Full gross, paying-card and jackpot marginals; legacy timing computed gross only.'})
    Path(a.out).write_text(json.dumps(rows,indent=2)+'\n')
if __name__=='__main__':main()
