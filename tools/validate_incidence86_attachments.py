"""Validate that numerical branch grouping respects full rooted attachments.

Loads an instrumented in-memory copy; never changes the execution tool.
"""
from pathlib import Path
import incidence86_scenario1 as run

def instrumented():
    source=(run.base.ROOT/'tools/incidence86_grouped.py').read_text()
    marker='            signatures = Counter('
    insertion='''            def structure_ball(j,parent):
                return tuple(sorted(structure_card(v,j) for v in altered[j] if v!=parent))
            def structure_card(v,parent):
                return (len(original[v]), v==cut_card,
                        tuple(sorted((j==cut_ball,structure_ball(j,v)) for j in slots[v] if j!=parent)))
            constraints={}
            for j,d in zip(ids,children):
                interface=(tuple(d.items()),j==cut_ball)
                structural=(j==cut_ball,structure_ball(j,i))
                if interface in constraints:
                    assert constraints[interface]==structural, 'unequal full attachment constraints'
                constraints[interface]=structural
'''
    assert source.count(marker)==1
    source=source.replace(marker,insertion+marker)
    namespace={'__name__':'attachment_validation'}
    exec(compile(source,'<attachment-validator>','exec'),namespace)
    return namespace['envelope']

if __name__=='__main__':
    import json,time
    live,priority,_=run.load();start=time.monotonic()
    envelope=instrumented();results=[]
    for k in priority:
        for g in run.base.b.groups(k):
            ordinary=envelope(g,False);packed=envelope(g,True)
            assert ordinary==packed
        results.append(dict(shape=k,full_attachment_constraints='matched'))
        print(json.dumps(results[-1]),flush=True)
    print(json.dumps(dict(validated=len(results),elapsed_seconds=time.monotonic()-start)))
