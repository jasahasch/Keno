from fractions import Fraction as F
from math import sqrt
from .model import DENOMINATOR,choose

def analyze(strategy,counts,denominations=('0.05','0.10','0.25','1.00')):
    counts.validate();D=DENOMINATOR;n=len(strategy.cards);g=counts.gross;ratio=lambda x:str(F(x,D))
    mean=F(sum(v*w for v,w in g.items()),D);var=F(sum(v*v*w for v,w in g.items()),D)-mean**2
    m={'frequency':ratio(D-g.get(0,0)),'zero_payout':ratio(g.get(0,0)),'recovery':ratio(sum(w for v,w in g.items() if v>=n)),'profitability':ratio(sum(w for v,w in g.items() if v>n)),'break_even':ratio(g.get(n,0)),'jackpot':ratio(D-counts.jackpots.get(0,0)),'multiple_jackpots':ratio(sum(w for k,w in counts.jackpots.items() if k>=2)),'mean_gross_credits':str(mean),'mean_net_credits':str(mean-n),'expected_return':str(mean/n),'volatility':str(var),'paying_cards':str(F(sum(v*w for v,w in counts.paying.items()),D)),'expected_shortfall_credits':str(F(sum((n-v)*w for v,w in g.items() if v<n),D)),'maximum_gross_credits':max(g),'money':[]}
    for text in denominations:
        d=F(text);m['money'].append({'denomination':str(d),'wager':str(n*d),'expected_gross':str(mean*d),'expected_net':str((mean-n)*d),'variance':str(var*d*d),'standard_deviation_display':sqrt(float(var))*float(d),'maximum_gross':str(max(g)*d),'gross_exceeds':{str(x):ratio(sum(w for v,w in g.items() if v*d>x)) for x in (100,500,1000)}})
    return m

def verify_moments(strategy,counts,metrics,table):
    """Independent marginal and two-card hypergeometric checks."""
    D=DENOMINATOR;cards=list(map(set,strategy.cards));cache={}
    mean=sum(sum(table[len(c)][h]*choose(len(c),h)*choose(80-len(c),20-h) for h in range(len(c)+1)) for c in cards)
    paying=sum(sum(choose(len(c),h)*choose(80-len(c),20-h) for h in range(len(c)+1) if table[len(c)][h]>0) for c in cards)
    diagonal=sum(sum(table[len(c)][h]**2*choose(len(c),h)*choose(80-len(c),20-h) for h in range(len(c)+1)) for c in cards)
    pairs=0
    for i,c in enumerate(cards):
        for other in cards[:i]:
            s,t,r=len(c),len(other),len(c&other);key=(s,t,r)
            if key not in cache:
                cache[key]=sum(choose(r,a)*choose(s-r,b)*choose(t-r,d)*choose(80-s-t+r,20-a-b-d)*table[s][a+b]*table[t][a+d] for a in range(r+1) for b in range(s-r+1) for d in range(t-r+1))
            pairs+=cache[key]
    if F(metrics['mean_gross_credits'])!=F(mean,D) or F(metrics['paying_cards'])!=F(paying,D):raise ValueError('Independent marginal moment mismatch.')
    if F(metrics['volatility'])!=F(diagonal+2*pairs,D)-F(mean,D)**2:raise ValueError('Independent overlap variance mismatch.')
    # Independently distinguish inclusive and strict thresholds.
    recovered=sum(w for v,w in counts.gross.items() if not v<len(cards));profitable=sum(w for v,w in counts.gross.items() if v-len(cards)>0)
    if F(metrics['recovery'])!=F(recovered,D) or F(metrics['profitability'])!=F(profitable,D):raise ValueError('Wager threshold mismatch.')
    return {'marginals':True,'overlap_variance':True,'strict_and_inclusive_thresholds':True}
