"""Universal conditional exclusions from explicitly aligned two-card partitions."""
from math import comb

def sizes(s,table):
 n=table.first_positive(s)-1;a,b=divmod(s,n);return [a+1]*b+[a]*(n-b)
def witness(s,t,shared,table):
 a=sizes(s,table);b=sizes(t,table);rows=a[:];cols=b[:];matrix=[[0]*len(b) for _ in a];left=shared
 while left:
  i,j=max(((i,j) for i in range(len(a)) for j in range(len(b))),key=lambda ij:(min(rows[ij[0]],cols[ij[1]],left),-ij[0],-ij[1]))
  take=min(rows[i],cols[j],left)
  if not take:raise ValueError('Insufficient partition capacity.')
  matrix[i][j]+=take;rows[i]-=take;cols[j]-=take;left-=take
 return {'spots':[s,t],'intersection':shared,'row_sizes':a,'column_sizes':b,'matrix':matrix,'guaranteed_edge_saving':sum(comb(x,2) for row in matrix for x in row),'claim':'Constructive saving, not claimed to be the maximum.'}
def verify(w,table):
 s,t=w['spots'];a,b=w['row_sizes'],w['column_sizes'];matrix=w['matrix']
 assert a==sizes(s,table) and b==sizes(t,table)
 assert len(matrix)==len(a) and all(len(row)==len(b) for row in matrix)
 assert all(type(x) is int and x>=0 for row in matrix for x in row)
 assert all(sum(row)<=size for row,size in zip(matrix,a))
 assert all(sum(matrix[i][j] for i in range(len(a)))<=size for j,size in enumerate(b))
 assert sum(map(sum,matrix))==w['intersection']
 # Independently materialize both card partitions and count repeated actual edges.
 groups_a=[[] for _ in a];groups_b=[[] for _ in b];v=1
 for i,row in enumerate(matrix):
  for j,n in enumerate(row):
   chunk=list(range(v,v+n));v+=n;groups_a[i]+=chunk;groups_b[j]+=chunk
 for groups,capacities in ((groups_a,a),(groups_b,b)):
  for group,size in zip(groups,capacities):
   extra=size-len(group);group+=list(range(v,v+extra));v+=extra
 def edges(groups):return {tuple(sorted((u,v))) for g in groups for u in g for v in g if u<v}
 savings=len(edges(groups_a)&edges(groups_b));assert savings==w['guaranteed_edge_saving']
 for groups,spot in ((groups_a,s),(groups_b,t)):
  card=sum(groups,[])
  for mask in range(1<<spot):
   if table[spot][mask.bit_count()]>0:
    picked={v for i,v in enumerate(card) if mask>>i&1};assert any(len(picked&set(g))>=2 for g in groups)
 return True
