/*
  EXP-046 RF-T005 Phase2 additional numerical exploration.
  Code Mode standalone entry: await (new Function("tools","text",source))(tools,text).
  Fetches original immutable S2P in 1MHz bins, performs exact complex-RI interpolation,
  nodal 5x5 -> 2-port -> mandatory external ABCD cascade. No inner port termination.
  No GH Actions or independent branch-current validation claimed by this source.
*/
const ROOT="MasayaTakagi/reconfigurable-rf-lpf-research";
const spaths=["data/parasitics/circuit1_ant_coupler_0_6ghz.s2p","data/parasitics/circuit2_poc_through_0_6ghz.s2p"];
const ranges=[[600,971],[1295,1660],[1661,1850],[1950,2300],[2301,2660],[2661,2760]];
const jobs=spaths.flatMap((path,i)=>ranges.map(([lo,hi])=>({path,i,lo,hi})));
const fs=await Promise.all(jobs.map(j=>tools.mcp__GitHub__fetch_file({repository_full_name:ROOT,path:j.path,ref:"main",start_line:j.lo+4,end_line:j.hi+4})));
let tabs=[new Map(),new Map()];
for(let k=0;k<jobs.length;k++)for(const row of fs[k].result.content.trim().split(/\n/)){let z=row.trim().split(/\s+/).map(Number);tabs[jobs[k].i].set(z[0]/1e6,z);}
const C=(r=0,i=0)=>[r,i],A=(a,b)=>[a[0]+b[0],a[1]+b[1]],S=(a,b)=>[a[0]-b[0],a[1]-b[1]],M=(a,b)=>[a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0]],n2=a=>a[0]*a[0]+a[1]*a[1],D=(a,b)=>{let d=n2(b);return [(a[0]*b[0]+a[1]*b[1])/d,(a[1]*b[0]-a[0]*b[1])/d]},K=(a,k)=>[a[0]*k,a[1]*k];
function matmul(X,Y){let R=Array.from({length:X.length},()=>Array.from({length:Y[0].length},()=>C()));for(let i=0;i<X.length;i++)for(let j=0;j<Y[0].length;j++)for(let k=0;k<Y.length;k++)R[i][j]=A(R[i][j],M(X[i][k],Y[k][j]));return R;}
function solve(X,Y){const n=X.length,m=Y[0].length,Z=X.map((row,i)=>row.map(v=>v.slice()).concat(Y[i].map(v=>v.slice())));for(let k=0;k<n;k++){let p=k;for(let j=k+1;j<n;j++)if(n2(Z[j][k])>n2(Z[p][k]))p=j;if(n2(Z[p][k])<1e-30)throw Error("singular");[Z[k],Z[p]]=[Z[p],Z[k]];let q=Z[k][k];for(let j=k;j<n+m;j++)Z[k][j]=D(Z[k][j],q);for(let i=0;i<n;i++)if(i!==k){let e=Z[i][k];for(let j=k;j<n+m;j++)Z[i][j]=S(Z[i][j],M(e,Z[k][j]));}}return Z.map(row=>row.slice(n));}
function sABCD(z){const one=C(1),a=C(z[1],z[2]),b=C(z[3],z[4]),e=C(z[5],z[6]),d=C(z[7],z[8]),det=M(b,e),den=K(b,2);return [[D(A(M(A(one,a),S(one,d)),det),den),K(D(S(M(A(one,a),A(one,d)),det),den),50)],[K(D(S(M(S(one,a),S(one,d)),det),den),.02),D(A(M(S(one,a),A(one,d)),det),den)]];}
function s4(f,pi){let lo=Math.floor(f),hi=Math.ceil(f);const u=tabs[pi].get(lo),v=tabs[pi].get(hi);if(!u||!v)throw Error("S2P grid missing "+f);return sABCD(u.map((z,j)=>j===0?f*1e6:z+(f-lo)*(v[j]-z)));}
const rows="B71,pass,663,698|B71,pass,617,652|B71,H2,1326,1396|B71,H3,1989,2094|B12,pass,699,716|B12,pass,729,746|B12,H2,1398,1432|B12,H3,2097,2148|B28,pass,703,748|B28,pass,758,803|B28,H2,1406,1496|B28,H3,2109,2244|B13+B14,pass,777,787|B13+B14,pass,788,798|B13+B14,pass,746,756|B13+B14,pass,758,768|B13+B14,H2,1554,1574|B13+B14,H2,1576,1596|B13+B14,H3,2331,2361|B13+B14,H3,2364,2394|B26,pass,814,849|B26,pass,859,894|B26,H2,1628,1698|B26,H3,2442,2547|B8,pass,880,915|B8,pass,925,960|B8,H2,1760,1830|B8,H3,2640,2745".split("|").map(x=>{const p=x.split(",");return {band:p[0],role:p[1],lo:+p[2],hi:+p[3]};});
const cases=[...new Set(rows.map(x=>x.band))],bands=Array.from({length:6},()=>[]);
function mkgrid(n){let out=Array.from({length:6},()=>[]);for(let ri=0;ri<rows.length;ri++){let z=rows[ri],ci=cases.indexOf(z.band);for(let j=0;j<n;j++){const f=z.lo+(z.hi-z.lo)*j/(n-1);out[ci].push({f,ci,role:z.role,seg:ri,pre:s4(f,0),post:s4(f,1)});}}return out;}
const g5=mkgrid(5),g31=mkgrid(31);
const Ledges=[[0,1],[1,2],[0,3],[2,4]],B=Array.from({length:5},()=>Array(4).fill(0));
for(let j=0;j<4;j++){let [u,v]=Ledges[j];B[u][j]++;B[v][j]--;}
const settings={};
const Q=[80,80,40,40,35,35,35,40];
const oldx=[4,5,12,8,0.45,0.35,0.15,0.15,0.08,0.08,-0.08,0.95,0.5,0.4,0.85,0.42,0.4,0.75,0.38,0.4,0.66,0.32,0.4,0.55,0.27,0.4,0.45,0.21,0.4];
oldx.push(.1);
const lo=[.4,.4,.4,.4,.02,.02,.02,.02,-.1,-.1,-.1,...Array(18).fill(0),.02],hi=[27,27,27,27,100,.2,100,.2,.1,.1,.1,...Array(18).fill(3),.2];
function clip(a,i){return Math.max(lo[i],Math.min(hi[i],a));}
function matrix(x,t,flip){let H=Array.from({length:4},(_,i)=>Array.from({length:4},(_,j)=>C(i===j?x[i]/25:0,i===j?x[i]:0)));const put=(a,b,k)=>{let z=k*Math.sqrt(x[a]*x[b]);H[a][b][1]+=z;H[b][a][1]+=z;};
if(flip){put(0,2,x[8]);put(2,3,(1-t)*x[9]);put(0,3,t*x[9]);put(3,1,x[10]);}else{put(2,0,x[8]);put(0,1,x[9]);put(1,3,x[10]);}
const I=Array.from({length:4},(_,i)=>Array.from({length:4},(_,j)=>C(i===j?1:0))),inv=solve(H,I);
return Array.from({length:5},(_,i)=>Array.from({length:5},(_,j)=>{let z=C();for(let a=0;a<4;a++)for(let b=0;b<4;b++)if(B[i][a]&&B[j][b])z=A(z,K(inv[a][b],B[i][a]*B[j][b]));return z;}));
}
let count=0;
function evalSet(x,t,conf,pt){count++;let coeff=matrix(x,t,conf.flip);let res={worst:-99,h2:100,h3:100,worstFreq:0},cs=conf.fixed.concat(conf.cv).concat(conf.extra||[]);
for(const p of pt){const om=2e6*Math.PI*p.f,Y=coeff.map(row=>row.map(v=>K(v,1/(om*1e-9))));const cap=[...x.slice(4,8),...x.slice(11+3*p.ci,14+3*p.ci),x[29]];
for(let i=0;i<cs.length;i++){let[u,v]=cs[i],q=Q[i],s=om*cap[i]*1e-12/(1+1/(q*q)),y=C(s/q,s);
Y[u][u]=A(Y[u][u],y);if(v>=0){Y[v][v]=A(Y[v][v],y);Y[u][v]=S(Y[u][v],y);Y[v][u]=S(Y[v][u],y);}}
let P=[0,2],I=[1,3,4];let E=I.map(i=>I.map(j=>Y[i][j])),R=I.map(i=>P.map(j=>Y[i][j])),W;try{W=solve(E,R);}catch(e){return {worst:1e4,h2:0,h3:0};}
let YY=P.map(i=>P.map((j,k)=>{let z=Y[i][j];for(let q=0;q<3;q++)z=S(z,M(Y[i][I[q]],W[q][k]));return z;}));
let [a,b,c,d]=[YY[0][0],YY[0][1],YY[1][0],YY[1][1]],det=S(M(a,d),M(b,c));if(n2(c)<1e-30)return {worst:1e4,h2:0,h3:0};
let L=[[D(K(d,-1),c),D(C(-1),c)],[D(K(det,-1),c),D(K(a,-1),c)]],T=matmul(matmul(p.pre,L),p.post),zl=C(60,-40),den=A(A(M(T[0][0],zl),T[0][1]),K(A(M(T[1][0],zl),T[1][1]),50)),il=-10*Math.log10(12000/n2(den));
if(!Number.isFinite(il))return {worst:1e4,h2:0,h3:0};
if(p.role==="pass"){if(il>res.worst){res.worst=il;res.worstFreq=p.f;}}else if(p.role==="H2")res.h2=Math.min(res.h2,il);else res.h3=Math.min(res.h3,il);}
return res;}
function score(r,target=30.03,pen=3){return r.worst+pen*(Math.max(0,target-r.h2)**2+Math.max(0,target-r.h3)**2);}
function simplex(x,indices,t,conf,pt,steps,maxcall=110,target=30.03,pen=3){
let n=indices.length,evalv=(v)=>{const tmp=x.slice();for(let j=0;j<n;j++)tmp[indices[j]]=clip(v[j],indices[j]);let R;try{R=evalSet(tmp,t,conf,pt);}catch(e){return {s:1e6,r:{worst:1e4,h2:0,h3:0}};}return {s:score(R,target,pen),r:R};};
let V=Array.from({length:n+1},(_,i)=>indices.map((j,k)=>i===k+1?clip(x[j]+steps[k],j):x[j])),F=V.map(evalv),nCalls=n+1;
while(nCalls+5<maxcall){let order=Array.from({length:n+1},(_,i)=>i).sort((i,j)=>F[i].s-F[j].s);V=order.map(i=>V[i]);F=order.map(i=>F[i]);let maxspread=Math.max(...F.map(z=>z.s))-Math.min(...F.map(z=>z.s));let center=Array(n).fill(0);for(let i=0;i<n;i++)for(let j=0;j<n;j++)center[j]+=V[i][j]/n;
let move=(a,b,r)=>a.map((v,j)=>clip(v+r*(v-b[j]),indices[j]));
let refl=move(center,V[n],1),fr=evalv(refl);nCalls++;
if(fr.s<F[0].s){let exp=move(center,V[n],2),fe=evalv(exp);nCalls++;if(fe.s<fr.s){V[n]=exp;F[n]=fe;}else{V[n]=refl;F[n]=fr;} }
else if(fr.s<F[n-1].s){V[n]=refl;F[n]=fr;}
else {let con=fr.s<F[n].s?move(center,V[n],.5):move(center,V[n],-.5),fc=evalv(con);nCalls++;
if(fc.s<Math.min(fr.s,F[n].s)){V[n]=con;F[n]=fc;}else{for(let i=1;i<=n;i++){V[i]=V[i].map((z,j)=>clip(.5*(z+V[0][j]),indices[j]));F[i]=evalv(V[i]);nCalls++;}}}
if(maxspread<1e-9 && nCalls>n*5)break;
}
const best=F.map((v,i)=>({i,s:v.s})).sort((a,b)=>a.s-b.s)[0].i;
for(let j=0;j<n;j++)x[indices[j]]=V[best][j];
return F[best].r;
}
function summary(x,t,name,grid){const conf=settings[name];let r=grid.map(pt=>evalSet(x,t,conf,pt));return {worst:Math.max(...r.map(z=>z.worst)),h2:Math.min(...r.map(z=>z.h2)),h3:Math.min(...r.map(z=>z.h3)),byBand:r.map((z,i)=>({band:cases[i],IL:+z.worst.toFixed(6),H2:+z.h2.toFixed(5),H3:+z.h3.toFixed(5)}))};}


const rr=await tools.mcp__GitHub__fetch_file({repository_full_name:ROOT,path:"experiments/chatgpt_topology_search/runs/EXP-046/gjm_series_bypass_cf3_result.json",ref:"main"});
const candidates=JSON.parse(rr.result.content).results;
const config={CF3_GJM3:[[3,-1],[4,-1],[0,2]]};
Q[3]=80;
const denseGrid=mkgrid(1001);
const threeGrid=mkgrid(3);
function eigmin(L){
 let X=L.map(row=>row.slice()),n=4;
 for(let it=0;it<120;it++){
  let p=0,q=1,t=0;
  for(let i=0;i<n;i++)for(let j=i+1;j<n;j++)if(Math.abs(X[i][j])>t){p=i;q=j;t=Math.abs(X[i][j]);}
  if(t<1e-14)break;
  const tau=(X[q][q]-X[p][p])/(2*X[p][q]),z=Math.sign(tau||1)/(Math.abs(tau)+Math.sqrt(1+tau*tau));
  const cc=1/Math.sqrt(1+z*z),ss=z*cc;
  const app=X[p][p],aqq=X[q][q],apq=X[p][q];
  X[p][p]=app-z*apq;X[q][q]=aqq+z*apq;X[p][q]=X[q][p]=0;
  for(let i=0;i<n;i++)if(i!==p&&i!==q){
    const aip=X[i][p],aiq=X[i][q];
    X[i][p]=X[p][i]=cc*aip-ss*aiq;
    X[i][q]=X[q][i]=ss*aip+cc*aiq;
  }
 }
 return Math.min(...Array.from({length:4},(_,i)=>X[i][i]));
}
function mnaProbe(x,conf,p){
 const L=x.slice(0,4),om=2e6*Math.PI*p.f,cc=conf.fixed.concat(conf.cv,conf.extra),cap=[...x.slice(4,8),...x.slice(11+3*p.ci,14+3*p.ci),x[29]],
 ind=Array.from({length:4},(_,i)=>Array.from({length:4},(_,j)=>i===j?L[i]:0));
 for(const [i,j,k] of [[2,0,x[8]],[0,1,x[9]],[1,3,x[10]]])ind[i][j]=ind[j][i]=k*Math.sqrt(L[i]*L[j]);
 const z=ind.map((row,i)=>row.map((v,j)=>C(i===j?om*L[i]*1e-9/25:0,om*v*1e-9)));
 const Y=Array.from({length:5},()=>Array.from({length:5},()=>C()));
 for(let j=0;j<cc.length;j++){
  const [u,v]=cc[j],q=Q[j],tot=om*cap[j]*1e-12/(1+1/q**2),y=C(tot/q,tot);
  Y[u][u]=A(Y[u][u],y);
  if(v>=0){Y[v][v]=A(Y[v][v],y);Y[u][v]=S(Y[u][v],y);Y[v][u]=S(Y[v][u],y);}
 }
 const inside=[1,3,4],ports=[0,2],
 big=Array.from({length:7},()=>Array.from({length:7},()=>C()));
 for(let i=0;i<3;i++)for(let j=0;j<3;j++)big[i][j]=Y[inside[i]][inside[j]];
 for(let i=0;i<3;i++)for(let j=0;j<4;j++){big[i][3+j]=C(B[inside[i]][j]);big[3+j][i]=C(-B[inside[i]][j]);}
 for(let i=0;i<4;i++)for(let j=0;j<4;j++)big[3+i][3+j]=z[i][j];
 const rhs=Array.from({length:7},(_,i)=>Array.from({length:2},(_,k)=>
 i<3?K(Y[inside[i]][ports[k]],-1):C(B[ports[k]][i-3])));
 const sol=solve(big,rhs);
 const y2=Array.from({length:2},(_,i)=>Array.from({length:2},(_,k)=>{
  let current=Y[ports[i]][ports[k]];
  for(let j=0;j<3;j++)current=A(current,M(Y[ports[i]][inside[j]],sol[j][k]));
  for(let j=0;j<4;j++)current=A(current,K(sol[j+3][k],B[ports[i]][j]));
  return current;
 }));
 const [a,b,c,d]=[y2[0][0],y2[0][1],y2[1][0],y2[1][1]],det=S(M(a,d),M(b,c));
 if(n2(c)<1e-27)throw Error("2port zero");
 const lpf=[[D(K(d,-1),c),D(C(-1),c)],[D(K(det,-1),c),D(K(a,-1),c)]];
 const total=matmul(matmul(p.pre,lpf),p.post),zl=C(60,-40),den=A(A(M(total[0][0],zl),total[0][1]),K(A(M(total[1][0],zl),total[1][1]),50)),il=-10*Math.log10(12000/n2(den));
 // Input-port-only 1V case for internal power balance.
 const V=Array.from({length:5},(_,i)=>i===0?C(1):i===2?C():sol[inside.indexOf(i)][0]);
 const I=Array.from({length:4},(_,i)=>sol[3+i][0]);
 let lossL=0,lossC=0;
 for(let j=0;j<4;j++)lossL+=om*L[j]*1e-9/25*n2(I[j]);
 for(let j=0;j<cc.length;j++){const[u,v]=cc[j],dif=v<0?V[u]:S(V[u],V[v]),q=Q[j];lossC+=om*cap[j]*1e-12/(q*(1+1/(q*q)))*n2(dif);}
 const Pin=y2[0][0][0]; // Vp=[1,0], port power Re(Vp* conj(Ip)), real Iin = Re(Y00)
 return {il,power_error_W:Pin-lossL-lossC,min_inductance_eig_nH:eigmin(ind),min_L_loss_W:lossL,min_C_loss_W:lossC};
}
const detail=[];
for(const z of candidates){
 const name=z.variant,conf={fixed:[[3,-1],[4,-1],[0,1],[1,2]],cv:config[name],extra:[[1,2]],flip:false};settings[name]=conf;
 const x=z.vector,full=summary(x,1,name,denseGrid),grid31=summary(x,1,name,mkgrid(31));
 let maxMna=0,maxPower=0,minEigen=1e4,checks=0,extremeProbe=null;
 for(const pp of threeGrid)for(const p of pp){
  const q=mnaProbe(x,conf,p),fast=evalSet(x,1,conf,[p]),il=p.role==="pass"?fast.worst:p.role==="H2"?fast.h2:fast.h3;
  let err=Math.abs(il-q.il);if(err>maxMna){maxMna=err;extremeProbe={band:cases[p.ci],role:p.role,f_MHz:p.f,fastIL:il,independentIL:q.il};}
  maxPower=Math.max(maxPower,Math.abs(q.power_error_W));minEigen=Math.min(minEigen,q.min_inductance_eig_nH);checks++;
 }
 detail.push({name,chip_area:6,number_of_GJM:3,PCB_pattern_C_count:2,grid31,grid1001:full,L_nH:x.slice(0,4),k:x.slice(8,11),fixed_C_pF:x.slice(4,8),PCB_bridge_pF:x[29],
    strict30_1001:full.h2>=30&&full.h3>=30,
    independent_mna:{probes:checks,max_IL_difference_dB:maxMna,max_power_balance_residual_W:maxPower,min_L_matrix_eigenvalue_nH:minEigen,most_disagreeing:extremeProbe}});
}
text({experiment:"EXP-046",verification:"28x1001 original S2P and independently solved 7x7 branch-current LPF MNA on 84 points",results:detail.map(d=>({name:d.name,grid1001:d.grid1001,strict:d.strict30_1001,MNA:d.independent_mna}))});
const path="experiments/chatgpt_topology_search/runs/EXP-046/independent_verified_gjm3_cf3_1001.json";
try{const u=await tools.mcp__GitHub__create_file({repository_full_name:ROOT,path,branch:"main",content:JSON.stringify({experiment_id:"EXP-046",phase:"Phase 2",constraint_id:"RF-T005",validation_type:"28 disconnected bands times 1001 + independent 7x7 branch-current MNA 84 probes each with complex loaded original frozen S2P and capacitor Qs",correction:"GJM3 revised Q80 for Cf3 replaces former PCB Q40 and allows capacitance above 0.2pF; baseline Qs and variable C values remain within RF-T005. Corrected capacitor loss denominator (1+1/(q*q)).",notes:"Finite grid only, not continuous extremum proof. 7x7 interior+4L branches plus 2 fixed port voltages, independent of optimizer's 4x4 L inverse and nodal Schur reduction. Constant-Q idealized parts, physical realization unverified",results:detail},null,2)+"\n",message:"Archive dense original-S2P and independent MNA validation of EXP-046 4L candidates"});text({saved:path,commit:u.result.commit_sha});}catch(e){text({save_error:String(e)});}
