from pathlib import Path
from hashlib import sha256
from collections import Counter
import subprocess,json,math,uuid
from .model import ResourceLimit
from .probability import Counts

def outside_layout(strategy):
    """Recognize a disjoint quartet backbone, without assuming arbitrary layouts have one."""
    cards=strategy.cards;backbone=[i for i,c in enumerate(cards) if len(c)==4 and all(i==j or not set(c).intersection(d) for j,d in enumerate(cards))]
    n=len(backbone)
    if 80-4*n>28:return None
    used=set(v for i in backbone for v in cards[i]);extras=tuple(c for i,c in enumerate(cards) if i not in backbone)
    vertices=sorted(set(range(1,81))-used);lookup={v:i+1 for i,v in enumerate(vertices)}
    return n,tuple(tuple(lookup[v] for v in c) for c in extras)

class NativeBackend:
    def __init__(self,cache):self.cache=Path(cache);self.cache.mkdir(parents=True,exist_ok=True)
    def binary(self):
        source=Path(__file__).parent/'native/outside.cpp';digest=sha256(source.read_bytes()+b'-O3-std=c++17').hexdigest();dest=self.cache/('outside-'+digest)
        if not dest.exists():
            temp=dest.with_name(dest.name+'.'+uuid.uuid4().hex+'.tmp')
            try:p=subprocess.run(['g++','-O3','-std=c++17',str(source),'-o',str(temp)],capture_output=True,text=True,timeout=90)
            except (OSError,subprocess.TimeoutExpired) as e:raise ResourceLimit('Native compiler unavailable or timed out.') from e
            if p.returncode:raise ResourceLimit('Native compiler unavailable or failed: '+p.stderr[:500])
            temp.replace(dest)
        return dest
    def evaluate(self,strategy,table,limits,mode):
        layout=outside_layout(strategy)
        if layout is None:raise ResourceLimit('Layout is outside the native structured-backend scope.')
        n,extras=layout;ext=80-4*n
        if mode=='subset':work=1<<ext
        else:
            regions=Counter(tuple(j for j,c in enumerate(extras) if v in c) for v in range(1,ext+1));work=math.prod(x+1 for x in regions.values())
        if work>limits.native_max_choices:raise ResourceLimit(f'Native {mode} work estimate {work} exceeds limit {limits.native_max_choices}.')
        data=' '.join(str(p) for s in range(2,11) for p in table[s])+'\n'+f'{n} {len(extras)} '+' '.join(str(len(c))+' '+' '.join(map(str,c)) for c in extras)+'\n'
        try:p=subprocess.run([str(self.binary()),mode],input=data,capture_output=True,text=True,timeout=limits.native_timeout_seconds)
        except subprocess.TimeoutExpired as e:raise ResourceLimit('Native evaluator deadline reached.') from e
        if p.returncode:raise ResourceLimit('Native evaluator failed: '+p.stderr[:500])
        return Counts.from_dict(json.loads(p.stdout))
