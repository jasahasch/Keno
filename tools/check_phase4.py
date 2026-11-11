"""Read-only check of the Phase 4 geometry partition and stored certificate links."""
import json
from itertools import combinations
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'outputs/phase4-discovery')]
import bound85 as b
from multi_keno.platform import legacy_adapter

def alternative():
    # Build all memberships from integer partitions of five, independently of the 84-to-85 lift.
    complete=set()
    for parts in b.ex.partitions(5):
        level={()}
        for degree_excess in parts:
            next_level=set()
            for shape in level:
                slots=1+max(map(max,shape),default=-1)
                for n in range(min(slots,degree_excess+1)+1):
                    for existing in combinations(range(slots),n):
                        edge=existing+tuple(range(slots,slots+degree_excess+1-n))
                        next_level.add(b.code(shape+(edge,)))
            level=next_level
        complete.update(level)
    return complete

def main():
    proof=json.loads((b.OUT/'coverage-final.json').read_text())
    actual={tuple(map(tuple,row['shape'])):row for row in proof['geometries']}
    assert len(actual)==len(proof['geometries'])==167
    assert set(actual)==set(b.shapes85())==alternative()
    old={tuple(map(tuple,r['shape'])):r['lower'] for r in json.loads(
        (b.OUT.parent/'incidence-ledger/audit85.json').read_text())}
    for shape,row in actual.items():
        if shape in old:assert row['status']=='inherited-certified'
        else:assert row['status']=='newly-certified' and row['evidence']
        bounds=[old.get(shape,0)]
        for evidence in row['evidence']:
            name=evidence['file']
            assert Path(name).name==name
            content=json.loads((b.OUT/name).read_text())
            assert {k:v for k,v in evidence.items() if k!='file'} in (
                content if isinstance(content,list) else [content])
            bounds.append(evidence['lower'])
        assert row['lower']==max(bounds)>=4**20
    w=legacy_adapter()
    witness=((1,2,3,4,5,6),(1,2,3,4,5,7,8))+tuple(tuple(range(i,i+4)) for i in range(9,81,4))
    st=SimpleNamespace(cards=witness)
    a=w.legacy.deletion(st,w.TABLE)[0]
    c=w.legacy.frontier(st,w.TABLE)[0]
    assert a==c and a[20]==min(row['lower'] for row in actual.values())==5325759447040
    print(json.dumps(dict(geometries=167,inherited=len(old),new=167-len(old),
                          minimum_zero=a[20],independent_witness=True,
                          scope='geometry and certificate-link reconciliation; arithmetic replay documented separately'),indent=2))

if __name__=='__main__':main()
