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

const original=[3.2925321835765495,7.710415239527519,4.9728393917692095,0.19866045614116043,0.2,1.1612999744014958,0.1,-0.07166805730766193,0.41265202900072084,3,1.0478321048888952,0.23307993256083764,2.832626864998555,0.8444199980677036,0.2283853694542783,3,0.7280647299889128,0,2.4043472366409904,0.45881436009337023,0.07513789471447903,1.8922245565753293,0.2538784376717406,0,1.077,0.168];
const defs=[
 ["nominal",a=>{}],
 ["extra_PCB_C_minus_1pct",a=>{a[4]-=.002}],
 ["extra_PCB_C_plus_1pct",a=>{a[4]+=.002}],
 ["PCB_Cf0_minus_1pct",a=>{a[3]*=.99}],
 ["PCB_Cf0_plus_1pct",a=>{a[3]*=1.01}],
 ["GJM_Cp_minus_1pct",a=>{a[5]*=.99}],
 ["GJM_Cp_plus_1pct",a=>{a[5]*=1.01}],
 ["k_L0_Ls_minus_0p01",a=>{a[6]-=.01}],
 ["k_Ls_L1_minus_0p01",a=>{a[7]-=.01}],
 ["k_Ls_L1_plus_0p01",a=>{a[7]+=.01}],
 ["all_Cv_minus_1pct",a=>{for(let i=8;i<26;i++)a[i]*=.99}],
 ["all_Cv_plus_1pct",a=>{for(let i=8;i<26;i++)a[i]=Math.min(3,a[i]*1.01]}]
];
let out=[];for(let [key,apply]of defs){let xx=original.slice();apply(xx);let g=prepare(101,xx),by=cases.map((_,ci)=>evaluate(xx.slice(8+ci*3,11+ci*3),g[ci]));let res={scenario:key,worst_IL_dB:Math.max(...by.map(r=>r.worst)),min_H2_dB:Math.min(...by.map(r=>r.h2)),min_H3_dB:Math.min(...by.map(r=>r.h3)),passes_finite30:Math.min(...by.map(r=>r.h2),...by.map(r=>r.h3))>=30,by_setting:Object.fromEntries(cases.map((s,i)=>[s,by[i]]))};out.push(res);}
const output={experiment_id:"EXP-045",phase:"Phase 2",constraint_id:"RF-T005",candidate:dir+"/margin_0p03_hybrid_candidate_20261017.json",status:"in_chat_JS_executed_model_original_main_S2P",grid:"28 disjoint segments x 101 points each scenario",method:"one-at-a-time fixed or tunable perturbation, no Cv retuning; exact fixed original RF-F003 S2Ps; 12 scenarios including nominal",physical_policy:"plus-1pct of PCB 0.2pF pattern may exceed nominal design cap limit and is exclusively a tolerance sensitivity test; no modified nominal circuit proposed",pcb_same_terminals_note:"extra 0.2pF PCB C (1,2) and Cf1 0.2pF PCB C (1,2) have same Q40, so changing the contribution by 0.002pF is electrically identical to varying either single PCB C by 1 percent",results:out,limits:["Not a worst-case manufacturing tolerance box or statistical yield; only twelve separate one-factor stresses.","28x101 per stress, not an independent 28x1001 MNA of perturbed settings.","No physical PCB EM or device Q(f)/SRF validation.","Phase3 not approved."]};
let saved=await tools.mcp__GitHub__create_file({repository_full_name:repo,path:dir+"/margin_0p03_101point_tolerance_20261017.json",branch:branch,message:"EXP-045: preserve 12-case 28x101 original-S2P tolerance sensitivity for independently MNA-verified control",content:JSON.stringify(output,null,2)+"\n"});text({saved:saved.result,results:out.map(({scenario,worst_IL_dB,min_H2_dB,min_H3_dB,passes_finite30})=>({scenario,worst_IL_dB,min_H2_dB,min_H3_dB,passes_finite30}))});
