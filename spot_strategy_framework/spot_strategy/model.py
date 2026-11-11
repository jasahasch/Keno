from dataclasses import dataclass,asdict,field
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
import json,math
PAYTABLE_SHA256='d12c1a7588b93d8e2fff3061d4c89b8b3a7c9fd6d9b386460952f2b05fe8cbe1'
OBJECTIVES=('frequency','jackpot','recovery','profitability','expected_return','volatility','paying_cards')
class ConfigurationError(ValueError):pass
class ResourceLimit(RuntimeError):pass
@dataclass(frozen=True)
class MachineProfile:
    min_cards:int=2
    max_cards:int=20
    min_spots:int=2
    max_spots:int=10
    denominations:tuple=('0.05','0.10','0.25','1.00')
    provenance:str='User-authorized machine profile; not manufacturer certification.'
@dataclass(frozen=True)
class DrawModel:
    universe:int=80
    drawn:int=20
    uniform_without_replacement:bool=True
    additive_per_card_payouts:bool=True
    linear_denomination_scaling:bool=True
@dataclass(frozen=True)
class Strategy:
    cards:tuple
    def __post_init__(self):
        if not 2<=len(self.cards)<=20:raise ConfigurationError('Use 2–20 active cards.')
        normalized=[]
        for card in self.cards:
            if not isinstance(card,(tuple,list)) or not 2<=len(card)<=10:raise ConfigurationError('Use 2–10 spots per card.')
            if any(type(v) is not int or not 1<=v<=80 for v in card):raise ConfigurationError('Numbers must be integers from 1–80.')
            if len(set(card))!=len(card):raise ConfigurationError('A card cannot select a number twice.')
            normalized.append(tuple(sorted(card)))
        object.__setattr__(self,'cards',tuple(normalized))
    @property
    def support(self):return frozenset(v for c in self.cards for v in c)
    def assignments(self):return {chr(65+i):(list(self.cards[i]) if i<len(self.cards) else None) for i in range(20)}
    @classmethod
    def from_data(cls,data):
        cards=data.get('cards',data) if isinstance(data,dict) else data
        if isinstance(cards,dict):cards=[cards[k] for k in sorted(cards) if cards[k] is not None]
        return cls(tuple(tuple(c) for c in cards))
@dataclass
class Limits:
    max_component_choices:int=200000
    max_global_states:int=200000
    max_operations:int=5000000
    max_seconds:float=60.0
    native_max_choices:int=16777216
    native_timeout_seconds:float=90.0
    canonical_permutations:int=100000
    def validate(self):
        if any(v<=0 for v in asdict(self).values()):raise ConfigurationError('Resource limits must be positive.')
@dataclass
class ResearchConfig:
    active_cards:list=field(default_factory=lambda:[20])
    spot_counts:list|None=None
    spot_min:int=2
    spot_max:int=10
    family:str='mixed'
    objective:str='frequency'
    require_jackpot:bool=False
    minimum_frequency:str='0'
    denominations:list=field(default_factory=lambda:['0.05','0.10','0.25','1.00'])
    seed:int=20261109
    max_candidates:int=20
    pool_size:int=80
    improve_record:bool=False
    record_scope:str='per_card_count'
    seed_cards:list|None=None
    limits:Limits=field(default_factory=Limits)
    def validate(self):
        if not self.active_cards or any(type(n) is not int or not 2<=n<=20 for n in self.active_cards):raise ConfigurationError('Active-card counts must be 2–20.')
        if not 2<=self.spot_min<=self.spot_max<=10:raise ConfigurationError('Spot range must be within 2–10.')
        if self.spot_counts is not None:
            if len(self.active_cards)!=1 or len(self.spot_counts)!=self.active_cards[0] or any(type(s) is not int or not 2<=s<=10 for s in self.spot_counts):raise ConfigurationError('Exact spot list must match the single active-card count.')
        if self.objective not in OBJECTIVES:raise ConfigurationError('Unknown objective.')
        if self.family not in ('identical','disjoint','repeated_pairs','rotating','balanced','mixed','jackpot','frequency','recovery','mutations','exhaustive'):raise ConfigurationError('Unknown generator family.')
        if self.objective=='jackpot':self.require_jackpot=True
        if self.require_jackpot and (max(self.spot_counts) if self.spot_counts else self.spot_max)<8:raise ConfigurationError('Jackpot eligibility requires a permitted 8–10 spot card.')
        if not 0<=Fraction(self.minimum_frequency)<=1:raise ConfigurationError('Frequency requirement must be a fraction between zero and one.')
        if any(Fraction(x) not in map(Fraction,MachineProfile().denominations) for x in self.denominations):raise ConfigurationError('Unsupported denomination.')
        if self.max_candidates<1 or not 2<=self.pool_size<=80:raise ConfigurationError('Invalid candidate or number-pool limit.')
        if self.record_scope not in ('per_card_count','global'):raise ConfigurationError('Record scope must be per_card_count or global.')
        if self.seed_cards is not None:Strategy.from_data(self.seed_cards)
        if self.family=='identical' and self.spot_counts and len(set(self.spot_counts))!=1:raise ConfigurationError('Identical cards require equal exact spots.')
        if self.family=='jackpot' and (max(self.spot_counts) if self.spot_counts else self.spot_max)<8:raise ConfigurationError('Jackpot generator needs 8-10 spots.')
        if self.family=='repeated_pairs' and (self.require_jackpot or not self.spot_min<=2<=self.spot_max or (self.spot_counts and any(v!=2 for v in self.spot_counts))):raise ConfigurationError('Repeated-pair settings must permit two-spots and no jackpot requirement.')
        if self.family=='disjoint':
            for n in self.active_cards:
                minimum=sum(self.spot_counts) if self.spot_counts else n*self.spot_min+(max(0,8-self.spot_min) if self.require_jackpot else 0)
                if minimum>80:raise ConfigurationError('No disjoint portfolio satisfies these spot/card constraints.')
        if self.family in ('mixed','rotating','exhaustive') and self.pool_size<(max(self.spot_counts) if self.spot_counts else self.spot_max):raise ConfigurationError('Number pool is smaller than a permitted spot size; narrow the spot range.')
        if self.seed_cards is not None and self.spot_counts and list(map(len,Strategy.from_data(self.seed_cards).cards))!=self.spot_counts:raise ConfigurationError('Mutation seed differs from the exact spot list.')
        self.limits.validate();return self
    def to_dict(self):return asdict(self)
    @classmethod
    def from_dict(cls,d):
        d=dict(d);d['limits']=Limits(**d.get('limits',{}))
        try:return cls(**d).validate()
        except TypeError as e:raise ConfigurationError(str(e)) from e
    @property
    def digest(self):return sha256(json.dumps(self.to_dict(),sort_keys=True).encode()).hexdigest()
class Paytable:
    def __init__(self,path):
        self.path=Path(path);raw=self.path.read_bytes();self.sha256=sha256(raw).hexdigest()
        if self.sha256!=PAYTABLE_SHA256:raise ConfigurationError('Scenario 1 paytable integrity check failed; no replacement was accepted.')
        self.table={int(s):tuple(v) for s,v in json.loads(raw)['tables'][0].items()}
        if any(len(v)!=s+1 or v[0]!=0 for s,v in self.table.items()):raise ConfigurationError('Invalid authoritative paytable.')
    def __getitem__(self,s):return self.table[s]
    def first_positive(self,s):return next(h for h,p in enumerate(self[s]) if p>0)
def choose(n,k):return math.comb(n,k) if 0<=k<=n else 0
DENOMINATOR=math.comb(80,20)
