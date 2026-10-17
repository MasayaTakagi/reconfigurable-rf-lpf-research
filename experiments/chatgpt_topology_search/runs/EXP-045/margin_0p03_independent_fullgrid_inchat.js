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

const cand={"vector":[3.2925321835765495,7.710415239527519,4.9728393917692095,0.19866045614116043,0.2,1.1612999744014958,0.1,-0.07166805730766193,0.41265202900072084,3,1.0478321048888952,0.23307993256083764,2.832626864998555,0.8444199980677036,0.2283853694542783,3,0.7280647299889128,0,2.4043472366409904,0.45881436009337023,0.07513789471447903,1.8922245565753293,0.2538784376717406,0,1.077,0.168],"expected":{"regions":28,"samples_per_region":1001,"worst_IL_dB":0.8955739167911139,"min_H2_dB":30.03001865117057,"min_H3_dB":30.030621824491885,"by_setting":{"B71":{"worst":0.8492522519123955,"h2":30.04998037945169,"h3":30.049775765227537},"B12":{"worst":0.8364961366632416,"h2":30.071720282374237,"h3":30.05012780019601},"B28":{"worst":0.8953859072038799,"h2":30.03826452796524,"h3":30.030621824491885},"B13+B14":{"worst":0.8083213742766324,"h2":30.077325408160345,"h3":31.017811085283547},"B26":{"worst":0.8794835603645661,"h2":30.049967887442147,"h3":32.72252348674811},"B8":{"worst":0.8955739167911139,"h2":30.03001865117057,"h3":38.58872197435332}}}};const fixed=cand.vector,grid=prepare(1001),q=[40,40,80,40,35,35,35],ccEdges=fixedCedges.concat(vedges);
const nport=[0,2],ninner=[1,3],Zzero=()=>C();
function independ(p,cv){
 let om=p.om,YC=Array.from({length:4},()=>Array.from({length:4},Zzero));
 let cap=[fixed[3],fixed[4],fixed[5],.2,...cv];
 for(let i=0;i<7;i++)stamp(YC,ccEdges[i],cy(cap[i],q[i],om));
 let L=fixed.slice(0,3),z=Array.from({length:3},(_,j)=>Array.from({length:3},(_,i)=>C(j===i?om*1e-9*L[i]/25:0,j===i?om*1e-9*L[i]:0)));
 z[0][2][1]=z[2][0][1]=om*1e-9*fixed[6]*Math.sqrt(L[0]*L[2]);
 z[1][2][1]=z[2][1][1]=om*1e-9*fixed[7]*Math.sqrt(L[1]*L[2]);
 let block=Array.from({length:5},(_,i)=>Array.from({length:5},(_,j)=>i<2?(j<2?YC[ninner[i]][ninner[j]]:C(B[ninner[i]][j-2])):(j<2?C(B[ninner[j]][i-2]):K(z[i-2][j-2],-1))));
 let rhs=Array.from({length:5},(_,i)=>Array.from({length:2},(_,j)=>i<2?K(YC[ninner[i]][nport[j]],-1):C(-B[nport[j]][i-2])));
 let sol=solve(block,rhs);
 let y=Array.from({length:2},(_,i)=>Array.from({length:2},(_,j)=>{let z=YC[nport[i]][nport[j]];for(let k=0;k<2;k++)z=A(z,M(YC[nport[i]][ninner[k]],sol[k][j]));for(let l=0;l<3;l++)z=A(z,K(sol[2+l][j],B[nport[i]][l]));return z;}));
 let[a,b,c,d]=[y[0][0],y[0][1],y[1][0],y[1][1]],det=S(M(a,d),M(b,c));
 let m=[[D(K(d,-1),c),D(C(-1),c)],[D(K(det,-1),c),D(K(a,-1),c)]],v=[A(M(m[0][0],p.right[0]),M(m[0][1],p.right[1])),A(M(m[1][0],p.right[0]),M(m[1][1],p.right[1]))],den=A(M(p.left[0],v[0]),M(p.left[1],v[1]));
 let H11=y[0][0][0],H22=y[1][1][0],H12=K(A(y[0][1],[y[1][0][0],-y[1][0][1]]),.5),eigMin=(H11+H22-Math.sqrt((H11-H22)**2+4*n2(H12)))/2;
 return {il:-10*Math.log10(12000/n2(den)),eigMin,reciprocity:Math.sqrt(n2(S(y[0][1],y[1][0])))};
}
let maxDiff=0,minEig=Infinity,maxReciprocity=0,countI=0,by=[];
for(let ci=0;ci<6;ci++){
 const cv=fixed.slice(8+3*ci,11+3*ci),res={worst:-99,h2:100,h3:100};
 for(const p of grid[ci]){let z=independ(p,cv),nom=ilAt(p,cv);maxDiff=Math.max(maxDiff,Math.abs(z.il-nom));minEig=Math.min(minEig,z.eigMin);maxReciprocity=Math.max(maxReciprocity,z.reciprocity);countI++;if(p.role==="pass")res.worst=Math.max(res.worst,z.il);else if(p.region==="H2")res.h2=Math.min(res.h2,z.il);else res.h3=Math.min(res.h3,z.il);}
 by.push({setting:cases[ci],...res});
}
let summary={worst_IL_dB:Math.max(...by.map(r=>r.worst)),min_H2_dB:Math.min(...by.map(r=>r.h2)),min_H3_dB:Math.min(...by.map(r=>r.h3))};
for(const k of ["worst_IL_dB","min_H2_dB","min_H3_dB"]){if(Math.abs(summary[k]-cand.expected[k])>1e-8)throw Error("independent failed "+k+" "+summary[k]+" vs "+cand.expected[k]);}
if(maxDiff>=1e-8||minEig< -1e-10||maxReciprocity>1e-8)throw Error("independent mismatch/passivity");
const output={experiment_id:"EXP-045",phase:"Phase 2",constraint_id:"RF-T005",status:"executed_in_chat_JS_independent_full_28x1001",candidate:dir+"/margin_0p03_hybrid_candidate_20261017.json",method:"5x5 independent coupled-inductor branch-current MNA with two forced port voltage excitations, external fixed original S2P cascade; check against separate reduced nodal-Y",grid_points:countI,full_dense_grid:true,summary,by_setting:by,max_IL_difference_dB:maxDiff,min_port_admittance_passivity_eigen_S:minEig,max_port_Y_reciprocity_residual_S:maxReciprocity,source_original_fixed_S2P:paths,source_s2p_sha256:["ad266111ba1dc2b92f235d39f4a647ff271050bc11941c217661dd299ee59945","b3cfc861bc0c8221f49328598c9d7d0766a6e94e42e990b6a50f6c90bf9a84da"],limitations:["Independent numerical formulation but same circuit constants and same sampled S2P grids; not external hardware or measured validation.","Mathematical continuous interval extreme remains unproved; discrete 28x1001 only.","Code Mode executed; no WSL2/Actions run.","No tolerance simulation and no Q(f)/SRF/EM.","Phase3 not authorized."]};
let saved=await tools.mcp__GitHub__create_file({repository_full_name:repo,path:dir+"/margin_0p03_independent_fullgrid_20261017.json",branch:br,message:"EXP-045: save independent MNA 28x1001 full-grid PASS for margin candidate",content:JSON.stringify(output,null,2)+"\n"});text({saved:saved.result,summary,maxDiff,minEig,maxReciprocity,grid_points:countI,by});
