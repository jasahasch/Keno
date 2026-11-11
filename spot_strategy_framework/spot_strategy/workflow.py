from pathlib import Path
from fractions import Fraction as F
import json,time,sys,sqlite3
from collections import Counter
from .model import Paytable,Strategy,ResearchConfig,Limits,ResourceLimit,MachineProfile,DrawModel
from .archive import Archive,digest,revision
from .canonical import canonical
from .engine import ExactEngine
from .probability import Counts
from .pruning import construct,verify_certificate,prune_reason

class Research:
    def __init__(self,project_root,archive):
        self.project=Path(project_root);self.table=Paytable(self.project/'outputs/keno-expanded-paytables.json');self.archive=Archive(archive);self.engine=ExactEngine(self.table,self.archive.root/'cache');self.source_revision=self.archive.snapshot_source()
    def close(self):self.archive.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def evaluate(self,strategy,limits=None,denominations=None,after_primary=None):
        limits=limits or Limits();limits.validate();denominations=MachineProfile().denominations  # Always archive all four monetary scales.
        sid,scope,encoding=canonical(strategy,limits.canonical_permutations);key=digest([sid,self.table.sha256,self.source_revision])
        old=self.archive.accepted(key)
        if old:return old,True
        payload={'cards':strategy.assignments(),'canonical_scope':scope,'canonical_encoding':encoding};self.archive.stage(key,sid,payload);job=self.archive.job(key)
        # Preserve the first physical representative when an isomorphic layout resumes it.
        stored=Strategy.from_data(json.loads(job['payload'])['cards']);strategy=stored
        try:
            primary=Counts.from_dict(json.loads(job['primary_data'])) if job['primary_data'] else self.engine.primary(strategy,limits)
            self.archive.primary_done(key,primary.to_dict())
            if after_primary:after_primary()
            metrics,verification=self.engine.verify(strategy,primary,limits,denominations)
            result={'schema_version':1,'strategy_id':sid,'evaluation_key':key,'strategy':{'cards':[list(c) for c in strategy.cards],'A_T':strategy.assignments(),'active_cards':len(strategy.cards),'selected_union':sorted(strategy.support),'spot_counts':list(map(len,strategy.cards)),'canonical_scope':scope},'overlap_structure':{'pair_intersections':[[len(set(a)&set(b)) for b in strategy.cards] for a in strategy.cards],'membership_regions':[{'cards':list(mask),'numbers':count} for mask,count in sorted(Counter(tuple(i for i,c in enumerate(strategy.cards) if v in c) for v in strategy.support).items())]},'runtime':{'python':sys.version,'sqlite':sqlite3.sqlite_version},'draw_model':DrawModel().__dict__,'machine_profile':MachineProfile().__dict__,'paytable_sha256':self.table.sha256,'source_revision':self.source_revision,'counts':primary.to_dict(),'metrics':metrics,'verification':verification,'limitations':['Marginal gross/paying/jackpot distributions are provided; their mutual independence is never asserted.','Verified candidate, not a global-optimality certificate.']}
            return self.archive.accept(key,result),False
        except ResourceLimit as e:self.archive.defer(key,e);raise
    def promote(self,result):
        metrics=result['metrics'];key=result['evaluation_key'];n=len(result['strategy']['cards'])
        for scope in ('global',json.dumps({'cards':n},sort_keys=True)):
            for track in ('frequency','profitability','recovery','expected_return','volatility','paying_cards'):
                self.archive.promote(track,scope,metrics[track],key)
            if F(metrics['jackpot'])>0:self.archive.promote('jackpot_frequency',scope,metrics['frequency'],key)
        if F(metrics['jackpot'])>0:
            for threshold in ('99.99','99.999','99.9998','99.9999'):
                f=str(F(threshold)/100)
                if F(metrics['frequency'])>=F(f):self.archive.promote('jackpot',json.dumps({'minimum_frequency':f},sort_keys=True),metrics['jackpot'],key)
    def run(self,config=None,run_id=None,after_primary=None):
        from .generate import candidates
        if run_id is None:
            config.validate();run_id=self.archive.new_run(config)
        saved=self.archive.run(run_id);config=ResearchConfig.from_dict(json.loads(saved['config']))
        if saved['revision']!=self.source_revision:raise ValueError('Source revision changed; fork a new run rather than mixing an interrupted evaluation.')
        counters=json.loads(saved['counters']);start=saved['next_index'];deadline=time.monotonic()+config.limits.max_seconds
        self.archive.checkpoint(run_id,start,'running',counters)
        try:
            for index,strategy in candidates(config,start):
                if time.monotonic()>=deadline:self.archive.checkpoint(run_id,index,'paused',counters);return self.archive.run(run_id)
                sid,_,_=canonical(strategy,config.limits.canonical_permutations);counters['attempted']+=1
                cert=construct(strategy,self.table);verify_certificate(strategy,self.table,cert)
                incumbent=None
                if config.improve_record and config.objective=='frequency':
                    results=self.archive.results();eligible=[]
                    for r in results:
                        if config.record_scope=='per_card_count' and len(r['strategy']['cards'])!=len(strategy.cards):continue
                        if config.require_jackpot and F(r['metrics']['jackpot'])==0:continue
                        eligible.append(F(r['metrics']['frequency']))
                    incumbent=max(eligible) if eligible else None
                why=prune_reason(config,cert,incumbent)
                if why:
                    counters['pruned']+=1;self.archive.event(run_id,index,sid,'pruned',{'reason':why,'certificate':cert})
                else:
                    try:
                        result,reused=self.evaluate(strategy,config.limits,config.denominations,after_primary)
                        counters['duplicates' if reused else 'verified']+=1;self.promote(result);self.archive.event(run_id,index,sid,'reused' if reused else 'verified',{'evaluation_key':result['evaluation_key']})
                    except ResourceLimit as e:
                        counters['deferred']+=1;self.archive.event(run_id,index,sid,'deferred',{'reason':str(e)})
                self.archive.checkpoint(run_id,index+1,'running',counters)
            self.archive.checkpoint(run_id,config.max_candidates,'complete-configured-scope',counters)
        except BaseException:
            saved=self.archive.run(run_id);self.archive.checkpoint(run_id,saved['next_index'],'paused',counters);raise
        return self.archive.run(run_id)
