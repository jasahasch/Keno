from .probability import region_evaluate,subset_evaluate
from .native_backend import NativeBackend,outside_layout
from .metrics import analyze,verify_moments
from .model import ResourceLimit
class ExactEngine:
    def __init__(self,paytable,cache):self.table=paytable;self.native=NativeBackend(cache)
    def primary(self,strategy,limits):
        try:return region_evaluate(strategy,self.table,limits)
        except ResourceLimit:
            if outside_layout(strategy) is None:raise
            return self.native.evaluate(strategy,self.table,limits,'regions')
    def independent(self,strategy,limits):
        try:return subset_evaluate(strategy,self.table,limits)
        except ResourceLimit:
            if outside_layout(strategy) is None:raise
            return self.native.evaluate(strategy,self.table,limits,'subset')
    def verify(self,strategy,primary,limits,denominations):
        second=self.independent(strategy,limits)
        for name in ('gross','paying','jackpots'):
            if getattr(primary,name)!=getattr(second,name):raise ValueError('Independent '+name+' distribution mismatch.')
        from .archive import digest
        first=primary.to_dict();other=second.to_dict();first.pop('method');other.pop('method')
        metrics=analyze(strategy,primary,denominations);moments=verify_moments(strategy,primary,metrics,self.table)
        return metrics,{'passed':True,'primary_law_sha256':digest(first),'independent_law_sha256':digest(other),'primary_method':primary.method,'independent_method':second.method,'full_gross_match':True,'full_paying_count_match':True,'full_jackpot_count_match':True,**moments}
