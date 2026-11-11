from random import Random
from hashlib import sha256
from itertools import combinations,combinations_with_replacement,islice
from .model import Strategy,ConfigurationError

def candidates(config,start=0):
    """Index-seeded generation avoids mutable RNG state in a resumed run."""
    config.validate()
    if config.family=='exhaustive':
        if len(config.active_cards)!=1:raise ConfigurationError('Exhaustive scopes use one card count.')
        n=config.active_cards[0];sizes=sorted(set(config.spot_counts or range(config.spot_min,config.spot_max+1)))
        from math import comb
        if sum(comb(config.pool_size,s) for s in sizes if s<=config.pool_size)>10000:raise ConfigurationError('Exhaustive card pool exceeds 10000 options; narrow the scope.')
        options=[c for s in sizes for c in combinations(range(1,config.pool_size+1),s)]
        if len(options)>10000:raise ConfigurationError('Exhaustive card pool exceeds 10000 options; narrow the scope.')
        it=combinations_with_replacement(options,n)
        for i,cards in enumerate(islice(it,start,config.max_candidates),start):
            if config.spot_counts and sorted(map(len,cards))!=sorted(config.spot_counts):continue
            strategy=Strategy(tuple(cards))
            if config.require_jackpot and not any(len(c)>=8 for c in strategy.cards):continue
            yield i,strategy
        return
    for index in range(start,config.max_candidates):
        rng=Random(int.from_bytes(sha256(f'{config.seed}:{index}'.encode()).digest()[:16],'big'));n=config.active_cards[index%len(config.active_cards)]
        spots=list(config.spot_counts) if config.spot_counts else [rng.randint(config.spot_min,config.spot_max) for _ in range(n)]
        family=config.family
        if family=='balanced' and config.spot_counts is None:spots=[config.spot_min+i%(config.spot_max-config.spot_min+1) for i in range(n)]
        if family in ('frequency','recovery') and config.spot_counts is None:spots=[4 if config.spot_min<=4<=config.spot_max else config.spot_min]*n
        if family=='jackpot' and config.spot_counts is None:spots=[4 if config.spot_min<=4<=config.spot_max else config.spot_min]*(n-1)+[rng.choice([s for s in range(config.spot_min,config.spot_max+1) if s>=8])]
        if family=='disjoint' and config.spot_counts is None:
            spots=[];left=80;remaining=n
            if config.require_jackpot:
                jackpot=rng.randint(max(8,config.spot_min),min(config.spot_max,80-(n-1)*config.spot_min));left-=jackpot;remaining-=1
            for i in range(remaining):
                size=rng.randint(config.spot_min,min(config.spot_max,left-(remaining-i-1)*config.spot_min));spots.append(size);left-=size
            if config.require_jackpot:spots.append(jackpot)
        if config.require_jackpot and not any(s>=8 for s in spots):
            if config.spot_counts:raise ConfigurationError('Exact composition has no jackpot-eligible card.')
            spots[-1]=rng.randint(max(8,config.spot_min),config.spot_max)
        if family=='identical':
            if len(set(spots))!=1:
                if config.spot_counts:raise ConfigurationError('Identical cards require equal spot sizes.')
                spots=[max(8,spots[0]) if config.require_jackpot else spots[0]]*n
            c=tuple(rng.sample(range(1,81),spots[0]));cards=[c]*n
        elif family=='repeated_pairs':
            if config.spot_counts and any(s!=2 for s in spots):raise ConfigurationError('Repeated pairs require two-spots.')
            if not config.spot_min<=2<=config.spot_max:raise ConfigurationError('Two-spots are not permitted.')
            cards=[(2*(i//2)+1,2*(i//2)+2) for i in range(n)]
        elif family in ('disjoint','balanced','frequency','recovery'):
            if family=='disjoint' and sum(spots)>80:raise ConfigurationError('Disjoint selections exceed eighty numbers.')
            pool=list(range(1,81));rng.shuffle(pool);offset=0;cards=[]
            for s in spots:cards.append(tuple(pool[(offset+j)%80] for j in range(s)));offset+=s
        elif family=='rotating':
            pool=list(range(1,max(max(spots),min(80,config.pool_size))+1));rng.shuffle(pool);cards=[tuple(pool[(i+j)%len(pool)] for j in range(s)) for i,s in enumerate(spots)]
        elif family=='mutations' and config.seed_cards:
            seed=Strategy.from_data(config.seed_cards)
            if len(seed.cards)!=n:raise ConfigurationError('Mutation seed has the wrong card count.')
            cards=list(seed.cards)
            for _ in range(1+rng.randrange(min(n,4))):
                i=rng.randrange(n);s=spots[i] if config.spot_counts else len(cards[i]);c=list(cards[i]);c=c[:s]
                while len(c)<s:
                    v=rng.randint(1,80)
                    if v not in c:c.append(v)
                pos=rng.randrange(s);choices=[v for v in range(1,81) if v not in c];c[pos]=rng.choice(choices);cards[i]=tuple(c)
        else:
            pool=rng.sample(range(1,81),max(max(spots),config.pool_size));cards=[tuple(rng.sample(pool,s)) for s in spots]
        strategy=Strategy(tuple(cards))
        if config.require_jackpot and not any(len(c)>=8 for c in strategy.cards):raise ConfigurationError('Generator could not honor jackpot eligibility.')
        yield index,strategy
