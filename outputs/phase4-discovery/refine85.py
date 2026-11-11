"""Tighten the sole residual geometry below the known 85-incidence witness."""
import bound85 as b
shape=((0,1),(1,4),(1,4),(2,4),(3,4))
a=b.bound(shape,False)
assert b.bound(shape,True)==a and a[0]>=5325759447040
b.save('min85-refinement.json',dict(shape=shape,lower=a[0],combined_marked_totals=a[1],independently_replayed=True))
