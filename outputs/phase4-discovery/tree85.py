"""Certified coefficient floors on six-card shared-number incidence trees."""
import bound85 as b
from functools import lru_cache
from itertools import product
from math import comb
import json

def trim(p):
    return tuple(p[:21])+(0,)*max(0,21-len(p))

def floor(d,k,p):
    p=trim(p)
    d[k]=tuple(map(min,zip(d[k],p))) if k in d else p

def convolution(a,c,packed):
    if not packed:return b.multiply(a,c)
    pack=lambda p:sum(v<<(b.WIDTH*i) for i,v in enumerate(p))
    return b.unpack(pack(a)*pack(c))[:21]

def messages(shape,packed):
    n=1+max(map(max,shape))
    slots=[tuple(j for j,edge in enumerate(shape) if i in edge) for i in range(n)]
    assert sum(map(len,slots))==n+len(shape)-1
    assert len(b.groups(shape))==1

    @lru_cache(None)
    def shared(j,parent):
        children=[card(i,j) for i in shape[j] if i!=parent]
        result=[{},{}]
        for selected in (0,1):
            d={0:(1,)}
            for _,child in enumerate(children):
                new={}
                for s,p in d.items():
                    for t,q in child[selected].items():
                        floor(new,s+t,convolution(p,q,packed))
                d=new
            result[selected]=d
        assert set(result[0])==set(result[1])
        return {t:(result[0][t],result[1][t]) for t in result[0]}

    @lru_cache(None)
    def card(i,parent):
        children=[shared(j,i) for j in slots[i] if j!=parent]
        result=[{},{}]
        for size in range(max(2,len(slots[i])),11):
            private=size-len(slots[i])
            for blocks in product(*(d.items() for d in children)):
                total=size+sum(t for t,_ in blocks)
                for inherited in (0,1):
                    if parent==-1 and inherited:continue
                    answer=[0]*21
                    for selected in product((0,1),repeat=len(blocks)):
                        hits=sum(selected)
                        cap=b.CAP[size]-inherited-hits
                        if cap<0:continue
                        p=(0,)*hits+tuple(comb(private,k) for k in range(min(private,cap)+1))
                        for bit,(_,q) in zip(selected,blocks):p=convolution(p,q[bit],packed)
                        for j,v in enumerate(p):answer[j]+=v
                    floor(result[inherited],total,answer)
        return result
    return card(min(range(n),key=lambda i:len(slots[i])),-1)[0]

def value(shape,packed):
    minimum=b.D
    n=1+max(map(max,shape))
    for s,p in messages(shape,packed).items():
        if not 2*(20-n)<=85-s<=10*(20-n):continue
        tail=b.tail(20-n,85-s,packed)
        minimum=min(minimum,sum(v*tail[20-k] for k,v in enumerate(p)))
    return minimum

def main():
    file=b.OUT/'tree-certificates85.json'
    rows=json.loads(file.read_text()) if file.exists() else []
    seen={tuple(map(tuple,r['shape'])) for r in rows}
    for shape in b.shapes85():
        if shape in seen or 1+max(map(max,shape))!=6 or len(b.groups(shape))!=1:continue
        x=value(shape,False)
        assert x==value(shape,True)
        rows.append(dict(shape=shape,lower=x,status='certified' if x>=b.RECORD else 'unresolved-tree-envelope',
                         proof='tree messages conditional on parent shared-number selection; audited exact packed arithmetic'))
        b.save(file.name,rows)
        print(len(rows),x,flush=True)

if __name__=='__main__':main()
