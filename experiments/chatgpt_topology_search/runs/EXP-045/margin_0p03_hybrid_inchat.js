/* EXP-045 Phase2 RF-T005: executed only when evaluated via Code Mode.
  Original immutable S2Ps from GitHub, 6 cases, 28 independent rows,
  existing T3L circuit, third fixed PCB C, fixed L,C,k, per-case 3 IC C.
  A target of 30.5 or 31 dB is an optimization search target, not a
  change to the formal/trial approved constraint.
*/
const repo="MasayaTakagi/reconfigurable-rf-lpf-research",branch="exp-045-rft005-3l-t-loss";
const dir="experiments/chatgpt_topology_search/runs/EXP-045";
const paths=["data/parasitics/circuit1_ant_coupler_0_6ghz.s2p","data/parasitics/circuit2_poc_through_0_6ghz.s2p"];
const ranges=[[617,960],[1326,1830],[1989,2745]];
const jobs=paths.flatMap((path,k)=>ranges.map(([lo,hi])=>({path,k,lo,hi})));
const [rr,br,checkpoint]=await Promise.all([
  Promise.all(jobs.map(j=>tools.mcp__GitHub__fetch_file({repository_full_name:repo,path:j.path,ref:"main",start_line:j.lo+4,end_line:j.hi+4}))),
  tools.mcp__GitHub__fetch_file({repository_full_name:repo,path:"data/bands.csv",ref:"main"}),
  tools.mcp__GitHub__fetch_file({repository_full_name:repo,path:dir+"/checkpoints/t3l_extra_pcb_out_0p2_prelim.json",ref:branch})
]);
const tabs=[new Map(),new Map()];
for(let i=0;i<jobs.length;i++)for(const line of rr[i].result.content.trim().split(/\n/)){const z=line.trim().split(/\s+/).map(Number);if(!Number.isFinite(z[0]))throw Error("bad S2P");tabs[jobs[i].k].set(z[0]/1e6,z);}
const bands=br.result.content.trim().split(/\n/).slice(1).map(s=>{let a=s.split(",");return {band:a[0],region:a[1],role:a[2],lo:+a[3],hi:+a[4]};});
const cases=["B71","B12","B28","B13+B14","B26","B8"], xbase=JSON.parse(checkpoint.result.content).vector;
const C=(r=0,i=0)=>[r,i],A=(a,b)=>[a[0]+b[0],a[1]+b[1]],S=(a,b)=>[a[0]-b[0],a[1]-b[1]],M=(a,b)=>[a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0]],K=(a,k)=>[a[0]*k,a[1]*k],n2=a=>a[0]*a[0]+a[1]*a[1],D=(a,b)=>{let n=n2(b);if(n<1e-38)throw Error("singular");return [(a[0]*b[0]+a[1]*b[1])/n,(a[1]*b[0]-a[0]*b[1])/n];};
function solve(X,Y){let n=X.length,m=Y[0].length,Z=X.map((r,i)=>r.map(z=>z.slice()).concat(Y[i].map(z=>z.slice())));for(let k=0;k<n;k++){let p=k;for(let j=k+1;j<n;j++)if(n2(Z[j][k])>n2(Z[p][k]))p=j;[Z[k],Z[p]]=[Z[p],Z[k]];if(n2(Z[k][k])<1e-28)throw Error("singular L");const inv=Z[k][k];for(let j=k;j<n+m;j++)Z[k][j]=D(Z[k][j],inv);for(let i=0;i<n;i++)if(i!==k){let v=Z[i][k];for(let j=k;j<n+m;j++)Z[i][j]=S(Z[i][j],M(v,Z[k][j]));}}return Z.map(r=>r.slice(n));}
function sp(f,k){let a=tabs[k].get(Math.floor(f)),b=tabs[k].get(Math.ceil(f));if(!a||!b)throw Error("missing "+k+" "+f);let h=f-Math.floor(f);return a.map((v,i)=>i===0?f*1e6:v+h*(b[i]-v));}
function sabcd(z){let one=C(1),a=C(z[1],z[2]),b=C(z[3],z[4]),c=C(z[5],z[6]),d=C(z[7],z[8]),det=M(b,c),den=K(b,2);return [[D(A(M(A(one,a),S(one,d)),det),den),K(D(S(M(A(one,a),A(one,d)),det),den),50)],[K(D(S(M(S(one,a),S(one,d)),det),den),.02),D(A(M(S(one,a),A(one,d)),det),den)]];}
const ledges=[[0,1],[1,2],[1,3]],B=Array.from({length:4},()=>[0,0,0]);for(let j=0;j<3;j++){let[u,v]=ledges[j];B[u][j]++;B[v][j]--;}
function constantMatrix(xx){let l=xx.slice(0,3),h=Array.from({length:3},(_,j)=>Array.from({length:3},(_,i)=>C(j===i?l[i]/25:0,j===i?l[i]:0)));h[0][2][1]=h[2][0][1]=xx[6]*Math.sqrt(l[0]*l[2]);h[1][2][1]=h[2][1][1]=xx[7]*Math.sqrt(l[1]*l[2]);let inv=solve(h,Array.from({length:3},(_,i)=>Array.from({length:3},(_,j)=>C(i===j?1:0))));return Array.from({length:4},(_,i)=>Array.from({length:4},(_,j)=>{let z=C();for(let a=0;a<3;a++)for(let b=0;b<3;b++)if(B[i][a]&&B[j][b])z=A(z,K(inv[a][b],B[i][a]*B[j][b]));return z;}));}
const fixedCedges=[[0,1],[1,2],[3,-1],[1,2]],vedges=[[3,-1],[0,1],[1,2]];
function stamp(y,edge,amp){let [u,v]=edge;y[u][u]=A(y[u][u],amp);if(v>=0){y[v][v]=A(y[v][v],amp);y[u][v]=S(y[u][v],amp);y[v][u]=S(y[v][u],amp);}}
function cy(cap,q,om){let fac=om*cap*1e-12/(1+1/(q*q));return C(fac/q,fac);}
const Mbase=constantMatrix(xbase);
function prep(n,xx=xbase){let minv=xx===xbase?Mbase:constantMatrix(xx),out=Array.from({length:6},()=>[]);for(const r of bands){let ci=cases.indexOf(r.band);for(let j=0;j<n;j++){let f=r.lo+(r.hi-r.lo)*j/(n-1),om=2e6*Math.PI*f;let y=minv.map(row=>row.map(z=>K(z,1/(om*1e-9))));for(let k=0;k<4;k++)stamp(y,fixedCedges[k],cy(k===3?.2:xx[3+k],k===2?80:40,om));let pre=sabcd(sp(f,0)),post=sabcd(sp(f,1));let left=[A(pre[0][0],K(pre[1][0],50)),A(pre[0][1],K(pre[1][1],50))],zl=C(60,-40),right=[A(M(post[0][0],zl),post[0][1]),A(M(post[1][0],zl),post[1][1])];out[ci].push({f,om,role:r.role,y,left,right});}}return out;}
function ilAt(p,cv){let y=p.y.map(row=>row.map(z=>z.slice()));for(let j=0;j<3;j++)stamp(y,vedges[j],cy(cv[j],35,p.om));let ii=[1,3],pp=[0,2],aa=y[1][1],bb=y[1][3],cc=y[3][1],dd=y[3][3],det=S(M(aa,dd),M(bb,cc));let v=C(),YY=[[],[]];for(let a=0;a<2;a++)for(let b=0;b<2;b++){let u=pp[a],w=pp[b],vec=[y[1][w],y[3][w]],inv0=D(S(M(dd,vec[0]),M(bb,vec[1])),det),inv1=D(S(M(aa,vec[1]),M(cc,vec[0])),det);YY[a][b]=S(y[u][w],A(M(y[u][1],inv0),M(y[u][3],inv1)));}
let[a,b,c,d]=[YY[0][0],YY[0][1],YY[1][0],YY[1][1]],det2=S(M(a,d),M(b,c));let L=[[D(K(d,-1),c),D(C(-1),c)],[D(K(det2,-1),c),D(K(a,-1),c)]];let vr=[A(M(L[0][0],p.right[0]),M(L[0][1],p.right[1])),A(M(L[1][0],p.right[0]),M(L[1][1],p.right[1]))],den=A(M(p.left[0],vr[0]),M(p.left[1],vr[1]));return -10*Math.log10(12000/n2(den));}
let count=0;
function evaluate(cv,ps){count++;let r={worst:-99,h2:100,h3:100};for(const p of ps){let il=ilAt(p,cv);if(p.role==="pass")r.worst=Math.max(r.worst,il);else if(p.role==="stop"&&p.f>0){if(p.region==="H2")r.h2=Math.min(r.h2,il);else r.h3=Math.min(r.h3,il);}}return r;}
/* Regions need disambiguation, cached grid attaches region. */
function prepare(n,xx=xbase){let g=prep(n,xx);for(let ci=0;ci<6;ci++){let idx=0;for(const b of bands.filter(b=>b.band===cases[ci]))for(let j=0;j<n;j++)g[ci][idx++].region=b.region;}return g;}
const clamp=v=>Math.max(0,Math.min(3,v));
function NM(seed,grid,target,limit=135){let ndim=3,evalv=v=>{let a=v.map(clamp),r=evaluate(a,grid);let d2=Math.max(0,target-r.h2),d3=Math.max(0,target-r.h3);return {x:a,r,s:r.worst+4*(d2*d2+d3*d3)}};let V=[seed.slice(),...Array.from({length:3},(_,i)=>seed.map((x,j)=>clamp(x+(i===j?.12:0))))],F=V.map(evalv),nc=4;while(nc<limit){let order=[0,1,2,3].sort((i,j)=>F[i].s-F[j].s);V=order.map(i=>V[i]);F=order.map(i=>F[i]);let center=[0,1,2].map(j=>(V[0][j]+V[1][j]+V[2][j])/3);let move=(factor,z)=>center.map((v,j)=>clamp(v+factor*(v-z[j])));let ref=evalv(move(1,V[3]));nc++;if(ref.s<F[0].s){let exp=evalv(move(2,V[3]));nc++;if(exp.s<ref.s){V[3]=exp.x;F[3]=exp;}else{V[3]=ref.x;F[3]=ref;}}else if(ref.s<F[2].s){V[3]=ref.x;F[3]=ref;}else{let cn=evalv(move(ref.s<F[3].s?.5:-.5,V[3]));nc++;if(cn.s<Math.min(ref.s,F[3].s)){V[3]=cn.x;F[3]=cn;}else for(let i=1;i<4;i++){V[i]=V[i].map((v,j)=>clamp((v+V[0][j])/2));F[i]=evalv(V[i]);nc++;}}if(nc>50&&Math.max(...F.map(v=>v.s))-Math.min(...F.map(v=>v.s))<1e-11)break;}return F.sort((a,b)=>a.s-b.s)[0];}

const seedCV=[[0.41265202900072084,3,1.0478321048888952],[0.23307993256083764,2.832626864998555,0.8444199980677036],[0.2283853694542783,3,0.7280647299889128],[0,2.4043472366409904,0.45881436009337023],[0.07513789471447903,1.8922245565753293,0.2538784376717406],[0,1.4569504587824467,0.2809348430730578]],target=30.03;
const gB8=prepare(31)[5];let best=null,countValid=0,maxH2=-Infinity;
for(let cv0 of [0,.0005,.001])for(let t1=0;t1<=55;t1++)for(let t2=0;t2<=35;t2++){
 let cv=[cv0,1.030+t1*.001, .160+t2*.001],r=evaluate(cv,gB8);
 maxH2=Math.max(maxH2,r.h2);
 if(r.h2>=target&&r.h3>=target){countValid++;if(best===null||r.worst<best.metrics.worst)best={cv,metrics:r};}
}
if(!best)throw Error("no feasible B8 refinement");
let candidateCV=seedCV.map(z=>z.slice());candidateCV[5]=best.cv;
let g=prepare(1001);let final=cases.map((_,ci)=>evaluate(candidateCV[ci],g[ci]));
let vector=xbase.slice(0,8).concat(candidateCV.flat());
const ret={experiment_id:"EXP-045",constraint_id:"RF-T005",phase:"Phase 2",status:"executed_in_chat_JS_original_S2P",objective:"local Pareto improvement in mandatory H2/H3 headroom versus baseline at low incremental IL",topology:"fixed L/C/k of extra PCB Q40 0.2pF T3L; 3 Q35 variable branches 6 settings",method:"B8 3x56x36 local deterministic Cv lattice around EXP-045 original, feasibility min H2/H3 >=30.03 on 31-point screen; other five settings from 30.05-target local search, final original S2P 28x1001 all 6 settings",B8_screen:{total:3*56*36,feasible_count:countValid,maxH2_dB:maxH2,selected:best},target_margin_dB:target,vector_order:"L0,L1,Ls,Cf0,Cf1,Cp,k0s,ks1; Cv0/Cv1/Cv2 by B71,B12,B28,B13+B14,B26,B8",vector,variable_C_by_setting:Object.fromEntries(cases.map((k,i)=>[k,candidateCV[i]])),full_grid:{regions:28,samples_per_region:1001,worst_IL_dB:Math.max(...final.map(r=>r.worst)),min_H2_dB:Math.min(...final.map(r=>r.h2)),min_H3_dB:Math.min(...final.map(r=>r.h3)),by_setting:Object.fromEntries(cases.map((k,i)=>[k,final[i]]))},baseline:{worst_IL_db:0.8951800090647889,min_H2_dB:30.00800000006535,min_H3_dB:30.008000001829046},evaluation_count:count,validation:{reduced_nodalY_external_S2P_28x1001:"executed",independent_MNA:"not_run_on_retuned_vector",continuous_grid_extrema:"not_run",hardware:"not_run"},limitations:["B8 lattice is a limited local scan, not a topology/global proof.","All results computed on exact precomputed circuit-model S2Ps from GitHub main, not measured data.","No tolerance margin demonstration across RF bands; 0.03dB remains very small.","No separate independent branch-current MNA for combined candidate; must verify before promotion.","Phase 3 remains stopped."]};
let saved=await tools.mcp__GitHub__create_file({repository_full_name:repo,path:dir+"/margin_0p03_hybrid_candidate_20261017.json",branch,message:"EXP-045: record 30.03dB-headroom hybrid retuned control with original dense S2P checks",content:JSON.stringify(ret,null,2)+"\n"});text({saved:saved.result,count,validB8:countValid,B8:best,performance:ret.full_grid,cv:candidateCV});