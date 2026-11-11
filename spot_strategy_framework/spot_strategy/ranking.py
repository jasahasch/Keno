from fractions import Fraction as F
from .model import OBJECTIVES

def eligible(records,objective,minimum_frequency='0',require_jackpot=False):
    for r in records:
        m=r['metrics']
        if F(m['frequency'])<F(minimum_frequency):continue
        if (require_jackpot or objective=='jackpot') and F(m['jackpot'])==0:continue
        yield r

def rank(records,objective='frequency',minimum_frequency='0',require_jackpot=False):
    if objective not in OBJECTIVES:raise ValueError('Unknown ranking objective.')
    sign=1 if objective=='volatility' else -1
    return sorted(eligible(records,objective,minimum_frequency,require_jackpot),key=lambda r:(sign*F(r['metrics'][objective]),r['strategy_id']))

def pareto(records,axes=('frequency','jackpot')):
    if any(a not in OBJECTIVES for a in axes):raise ValueError('Unknown Pareto axis.')
    def val(r,a):return (-1 if a=='volatility' else 1)*F(r['metrics'][a])
    out=[]
    for r in records:
        if not any(all(val(other,a)>=val(r,a) for a in axes) and any(val(other,a)>val(r,a) for a in axes) for other in records):out.append(r)
    return sorted(out,key=lambda r:r['strategy_id'])
