// Two independent exact algorithms for disjoint-quartet / outside-core layouts.
#include <bits/stdc++.h>
using namespace std;using U=uint64_t;using W=__uint128_t;
int T[11][11];U C(int n,int k){if(k<0||k>n)return 0;W w=1;for(int i=1;i<=k;i++)w=w*(n-i+1)/i;return U(w);}
struct Key{int k,g,p,j;bool operator<(const Key&o)const{return tie(k,g,p,j)<tie(o.k,o.g,o.p,o.j);}};
struct Laws{map<int,U>gross,paid,jack;};
void printmap(const map<int,U>&x){cout<<'{';bool first=true;for(auto[k,w]:x)if(w){if(!first)cout<<',';first=false;cout<<'"'<<k<<"\":\""<<w<<'"';}cout<<'}';}
int main(int argc,char**argv){try{if(argc!=2)throw runtime_error("Specify subset or regions");string mode=argv[1];for(int s=2;s<=10;s++)for(int h=0;h<=s;h++)if(!(cin>>T[s][h]))throw runtime_error("Missing paytable");int n,m;if(!(cin>>n>>m)||n+m<2||n+m>20)throw runtime_error("Invalid card counts");int ext=80-4*n;if(ext<0||ext>28)throw runtime_error("Outside core exceeds native resource support");vector<int>sizes(m),membership(ext);for(int j=0;j<m;j++){cin>>sizes[j];if(sizes[j]<2||sizes[j]>10)throw runtime_error("Invalid spots");set<int>seen;for(int a=0;a<sizes[j];a++){int v;cin>>v;if(v<1||v>ext||!seen.insert(v).second)throw runtime_error("Invalid outside number");membership[v-1]|=1<<j;}}
 int cap=0;for(int h=1;h<=4;h++)cap=max(cap,20*T[4][h]/h);vector<vector<U>>qg(21,vector<U>(cap+1)),qp(21,vector<U>(n+1));qg[0][0]=qp[0][0]=1;
 if(mode=="subset"){
  for(int card=0;card<n;card++){vector<vector<U>>ng(21,vector<U>(cap+1)),np(21,vector<U>(n+1));for(int k=0;k<=20;k++){for(int g=0;g<=cap;g++)if(qg[k][g])for(int h=0;h<=4&&k+h<=20;h++)if(g+T[4][h]<=cap)ng[k+h][g+T[4][h]]+=U(W(qg[k][g])*C(4,h));for(int p=0;p<=card;p++)if(qp[k][p])for(int h=0;h<=4&&k+h<=20;h++)np[k+h][p+(T[4][h]>0)]+=U(W(qp[k][p])*C(4,h));}qg.swap(ng);qp.swap(np);}
 }else if(mode=="regions"){
  for(auto&v:qg)fill(v.begin(),v.end(),0);for(auto&v:qp)fill(v.begin(),v.end(),0);U fact[21];fact[0]=1;for(int i=1;i<=20;i++)fact[i]=fact[i-1]*i;
  // Explicit histogram enumeration keeps subset weights and factorial division exact.
  for(int a4=0;a4<=n&&4*a4<=20;a4++)for(int a3=0;a3+a4<=n&&4*a4+3*a3<=20;a3++)for(int a2=0;a2+a3+a4<=n&&4*a4+3*a3+2*a2<=20;a2++)for(int a1=0;a1+a2+a3+a4<=n&&4*a4+3*a3+2*a2+a1<=20;a1++){int a0=n-a1-a2-a3-a4;int counts[]={a0,a1,a2,a3,a4};W divisor=1,w;for(int a:counts)divisor*=fact[a];w=fact[n]/divisor;for(int h=0;h<=4;h++)for(int j=0;j<counts[h];j++)w*=C(4,h);int k=a1+2*a2+3*a3+4*a4,g=0,p=0;for(int h=0;h<=4;h++){g+=counts[h]*T[4][h];p+=counts[h]*(T[4][h]>0);}qg[k][g]+=U(w);qp[k][p]+=U(w);}
 }else throw runtime_error("Unknown algorithm");
 map<Key,U>hist;vector<int>hits(m);
 if(mode=="subset"){
  hist[{0,0,0,0}]=1;int k=0,g=0,p=0,jp=0;for(unsigned step=1;step<(1u<<ext);step++){unsigned gray=step^(step>>1);int bit=__builtin_ctz(step),dir=(gray>>bit&1)?1:-1;k+=dir;int owners=membership[bit];while(owners){int j=__builtin_ctz((unsigned)owners);owners&=owners-1;int old=T[sizes[j]][hits[j]];p-=old>0;jp-=old==10000;hits[j]+=dir;int now=T[sizes[j]][hits[j]];p+=now>0;jp+=now==10000;g+=now-old;}if(k<=20)hist[{k,g,p,jp}]++;}
 }else{
  map<int,int>counts;for(int color:membership)counts[color]++;vector<pair<int,int>>regions(counts.begin(),counts.end());function<void(int,int,U)>walk=[&](int i,int k,U ways){if(i==(int)regions.size()){int g=0,p=0,jp=0;for(int j=0;j<m;j++){int pay=T[sizes[j]][hits[j]];g+=pay;p+=pay>0;jp+=pay==10000;}hist[{k,g,p,jp}]+=ways;return;}auto[color,count]=regions[i];for(int caught=0;caught<=count&&k+caught<=20;caught++){for(int j=0;j<m;j++)if(color>>j&1)hits[j]+=caught;walk(i+1,k+caught,U(W(ways)*C(count,caught)));for(int j=0;j<m;j++)if(color>>j&1)hits[j]-=caught;}};walk(0,0,1);
 }
 Laws laws;
 if(mode=="subset"){
  for(auto[key,w]:hist){int k=20-key.k;for(int g=0;g<=cap;g++)if(qg[k][g])laws.gross[g+key.g]+=U(W(w)*qg[k][g]);for(int p=0;p<=n;p++)if(qp[k][p])laws.paid[p+key.p]+=U(W(w)*qp[k][p]);laws.jack[key.j]+=U(W(w)*C(4*n,k));}
 }else{
  for(const auto&entry:hist){const Key&h=entry.first;U w=entry.second;int remaining=20-h.k;U mass=0;for(int paid=0;paid<=n;paid++)if(qp[remaining][paid]){U count=U(W(w)*qp[remaining][paid]);laws.paid[paid+h.p]+=count;mass+=count;}laws.jack[h.j]+=mass;for(int value=0;value<=cap;value++)if(qg[remaining][value])laws.gross[value+h.g]+=U(W(w)*qg[remaining][value]);}
 }
 for(auto*law:{&laws.gross,&laws.paid,&laws.jack}){U total=0;for(auto[k,w]:*law)total+=w;if(total!=C(80,20))throw runtime_error("Incomplete outcome mass");}
 cout<<"{\"denominator\":\""<<C(80,20)<<"\",\"gross\":";printmap(laws.gross);cout<<",\"paying\":";printmap(laws.paid);cout<<",\"jackpots\":";printmap(laws.jack);cout<<",\"method\":\"native-"<<mode<<"-v1\"}\n";
 }catch(const exception&e){cerr<<e.what()<<'\n';return 2;}}
