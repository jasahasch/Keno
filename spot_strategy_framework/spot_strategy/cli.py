import argparse,json,sys,csv
from pathlib import Path
from fractions import Fraction as F
from .model import ResearchConfig,Strategy,Limits,OBJECTIVES,ConfigurationError,ResourceLimit
from .workflow import Research
from .ranking import rank,pareto
from .generate import candidates
from .canonical import canonical
from .history import import_history
from .archive import atomic_json

def parser():
    p=argparse.ArgumentParser(description='Exact Scenario 1 Spot Strategy Research Framework')
    p.add_argument('--project-root',default=str(Path(__file__).resolve().parents[2]));p.add_argument('--archive',default='outputs/spot-strategy-framework/archive');sub=p.add_subparsers(dest='command',required=True)
    for name in ('validate','generate','run'):
        s=sub.add_parser(name);s.add_argument('--config');s.add_argument('--cards',default='20');s.add_argument('--spots',default='2-10');s.add_argument('--spot-counts');s.add_argument('--family',default='mixed');s.add_argument('--objective',choices=OBJECTIVES,default='frequency');s.add_argument('--minimum-frequency',default='0',help='Fraction such as 999998/1000000 (not percent).');s.add_argument('--require-jackpot',action='store_true');s.add_argument('--seed',type=int,default=20261109);s.add_argument('--limit',type=int,default=20);s.add_argument('--pool-size',type=int,default=80);s.add_argument('--improve-record',action='store_true');s.add_argument('--out')
    s=sub.add_parser('evaluate');s.add_argument('layout');s.add_argument('--max-operations',type=int,default=5000000);s.add_argument('--max-component-choices',type=int,default=200000);s.add_argument('--native-max-choices',type=int,default=16777216);s.add_argument('--seconds',type=float,default=90);s.add_argument('--full',action='store_true')
    s=sub.add_parser('resume');s.add_argument('run_id')
    s=sub.add_parser('rank');s.add_argument('--objective',choices=OBJECTIVES,default='frequency');s.add_argument('--minimum-frequency',default='0');s.add_argument('--require-jackpot',action='store_true');s.add_argument('--cards',type=int);s.add_argument('--limit',type=int,default=10)
    s=sub.add_parser('pareto');s.add_argument('--axes',default='frequency,jackpot');s.add_argument('--out')
    s=sub.add_parser('show');s.add_argument('strategy_id');s.add_argument('--full',action='store_true')
    s=sub.add_parser('export');s.add_argument('--format',choices=['json','csv'],default='json');s.add_argument('--out',required=True)
    s=sub.add_parser('history');s.add_argument('--reproduce',action='store_true');s.add_argument('--include-expensive',action='store_true')
    sub.add_parser('audit');sub.add_parser('records');sub.add_parser('list')
    return p

def config_args(a):
    if a.config:return ResearchConfig.from_dict(json.loads(Path(a.config).read_text()))
    spots=a.spots.split('-');return ResearchConfig(active_cards=[int(v) for v in a.cards.split(',')],spot_counts=[int(v) for v in a.spot_counts.split(',')] if a.spot_counts else None,spot_min=int(spots[0]),spot_max=int(spots[-1]),family=a.family,objective=a.objective,minimum_frequency=a.minimum_frequency,require_jackpot=a.require_jackpot,seed=a.seed,max_candidates=a.limit,pool_size=a.pool_size,improve_record=a.improve_record).validate()
def brief(r):return {'strategy_id':r['strategy_id'],'status':'verified','active_cards':r['strategy']['active_cards'],'metrics':r['metrics'],'verification':r['verification']}
def main(argv=None):
    a=parser().parse_args(argv)
    try:
        if a.command in ('validate','generate','run'):config=config_args(a)
        if a.command=='validate':print(json.dumps({'valid':True,'configuration':config.to_dict()},indent=2));return 0
        if a.command=='generate':
            data=[{'index':i,'strategy_id':canonical(s,config.limits.canonical_permutations)[0],'cards':s.assignments(),'status':'experimental-not-evaluated'} for i,s in candidates(config)]
            if a.out:atomic_json(a.out,data)
            else:print(json.dumps(data,indent=2))
            return 0
        with Research(a.project_root,a.archive) as service:
            if a.command=='evaluate':
                s=Strategy.from_data(json.loads(Path(a.layout).read_text()));limits=Limits(max_operations=a.max_operations,max_component_choices=a.max_component_choices,native_max_choices=a.native_max_choices,max_seconds=a.seconds,native_timeout_seconds=a.seconds);r,reused=service.evaluate(s,limits);service.promote(r);data=r if a.full else dict(brief(r),reused=reused)
            elif a.command=='run':data=service.run(config)
            elif a.command=='resume':data=service.run(run_id=a.run_id)
            elif a.command=='history':data=import_history(service,a.reproduce,a.include_expensive)
            elif a.command=='audit':data=service.archive.audit()
            elif a.command=='records':data=service.archive.records()
            elif a.command=='show':
                matches=[r for r in service.archive.results() if r['strategy_id'].startswith(a.strategy_id)]
                if len(matches)!=1:raise ValueError('Strategy identifier is missing or ambiguous.')
                data=matches[0] if a.full else dict(brief(matches[0]),A_T=matches[0]['strategy']['A_T'])
            elif a.command=='rank':
                records=service.archive.results();records=[r for r in records if not a.cards or r['strategy']['active_cards']==a.cards];data=[brief(r) for r in rank(records,a.objective,a.minimum_frequency,a.require_jackpot)[:a.limit]]
            elif a.command=='pareto':
                records=pareto(service.archive.results(),tuple(a.axes.split(',')));data=[brief(r) for r in records]
                if a.out:atomic_json(a.out,data)
            elif a.command=='list':data=[brief(r) for r in service.archive.results()]
            elif a.command=='export':
                records=service.archive.results();path=Path(a.out);path.parent.mkdir(parents=True,exist_ok=True)
                if a.format=='json':atomic_json(path,records)
                else:
                    with path.open('w',newline='') as f:
                        w=csv.writer(f);w.writerow(['strategy_id','active_cards',*OBJECTIVES])
                        for r in records:w.writerow([r['strategy_id'],r['strategy']['active_cards'],*(r['metrics'][k] for k in OBJECTIVES)])
                data={'exported':len(records),'path':str(path),'format':a.format}
            print(json.dumps(data,indent=2));return 0
    except (ValueError,ResourceLimit,OSError) as e:print(json.dumps({'status':'not-verified','error':str(e)}),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
