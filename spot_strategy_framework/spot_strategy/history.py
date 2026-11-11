"""Read-only checkpoint adapters. References are not silently trusted as new evaluations."""
from pathlib import Path
from hashlib import sha256
from fractions import Fraction as F
import json
from .model import Strategy,Limits,ResourceLimit

def references(project):
    project=Path(project);out=[]
    datasets=[('outputs/payout-jackpot-frontier/exact-results.json',['absolute-record-preserved','pair-1','blocks-28']),('outputs/jackpot-recovery-next/new-exact-results.json',['new-0','new-11','recovery-2'])]
    for path,labels in datasets:
        file=project/path
        if not file.exists():continue
        data=json.loads(file.read_text());source_hash=sha256(file.read_bytes()).hexdigest()
        for label in labels:
            r=next(v for v in data if v['label']==label);audit='outputs/jackpot-recovery-next/full-independent-audit.json' if path.startswith('outputs/jackpot-recovery-next') else 'outputs/payout-jackpot-frontier/full-independent-audit.json';a=project/audit
            evidence=bool(a.exists() and json.loads(a.read_text()).get('passed'))
            out.append({'label':label,'source':path,'source_sha256':source_hash,'audit_source':audit,'audit_sha256':sha256(a.read_bytes()).hexdigest() if a.exists() else None,'repository_evidence_status':'source-verification-evidence-present' if evidence else 'unconfirmed-source-claim','cards':r['cards'],'expected_gross_counts':r['gross_counts'],'expected_frequency':r['frequency'],'expected_jackpot':r['jackpot_any'],'expected_profitability':r['strict_profit']})
    path='outputs/single-draw-80-target/exact-results.json';file=project/path
    if file.exists():
        for r in json.loads(file.read_text())['results']:
            if r['id'] in ('searched-best-15','searched-best-20'):
                out.append({'label':r['id'],'source':path,'source_sha256':sha256(file.read_bytes()).hexdigest(),'repository_evidence_status':'historical-verified-profitability-reference','cards':r['cards'],'expected_frequency':r['metrics']['any_payout_fraction'],'expected_profitability':r['metrics']['profit_fraction']})
    return out

def import_history(research,reproduce=False,include_expensive=False):
    report=[]
    for ref in references(research.project):
        research.archive.history(ref);entry={'label':ref['label'],'source_status':ref['repository_evidence_status'],'framework_status':'reference-only'}
        if reproduce and (ref['label']!='recovery-2' or include_expensive):
            try:
                limit=Limits(max_operations=30000000,native_max_choices=(268435456 if include_expensive else 16777216),native_timeout_seconds=180)
                result,reused=research.evaluate(Strategy.from_data(ref['cards']),limit)
                m=result['metrics']
                for field,key in [('expected_frequency','frequency'),('expected_jackpot','jackpot'),('expected_profitability','profitability')]:
                    if field in ref and F(ref[field])!=F(m[key]):raise ValueError('Historical '+field+' regression: '+ref['label'])
                if 'expected_gross_counts' in ref and result['counts']['gross']!={str(k):str(v) for k,v in ref['expected_gross_counts'].items() if int(v)}:raise ValueError('Historical full payout law differs: '+ref['label'])
                research.promote(result);entry.update(framework_status='independently-reproduced',strategy_id=result['strategy_id'],evaluation_key=result['evaluation_key'],reused=reused)
            except ResourceLimit as e:entry.update(framework_status='deferred-resource-limit',reason=str(e))
        report.append(entry)
    return report
