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
const Ledges=[[0,1],[1,3],[1,4],[1,2]],B=Array.from({length:5},()=>Array(4).fill(0));
for(let j=0;j<4;j++){let [u,v]=Ledges[j];B[u][j]++;B[v][j]--;}
const settings={
 base:{fixed:[[0,1],[4,-1],[1,2],[0,3]],cv:[[3,-1],[4,-1],[1,2]]},
 cap_bridge_in:{fixed:[[0,1],[4,-1],[1,2],[0,3]],cv:[[3,-1],[4,-1],[0,2]]},
 cap_bridge_out:{fixed:[[0,1],[4,-1],[1,2],[2,3]],cv:[[3,-1],[4,-1],[1,2]]},
 cf_to_output:{fixed:[[0,1],[4,-1],[1,2],[0,2]],cv:[[3,-1],[4,-1],[1,2]]},
 shunt_bridge:{fixed:[[0,1],[4,-1],[1,2],[0,3]],cv:[[2,3],[4,-1],[1,2]]},
 other_tip:{fixed:[[0,1],[4,-1],[1,2],[0,4]],cv:[[3,-1],[4,-1],[1,2]]},
 cross_shunt:{fixed:[[0,1],[4,-1],[1,2],[0,3]],cv:[[3,-1],[0,4],[1,2]]},
 fixed_trap:{fixed:[[0,1],[3,-1],[1,2],[0,4]],cv:[[3,-1],[4,-1],[1,2]]}
};
const Q=[80,40,80,40,35,35,35];
const oldx=[2.167260661613276,18.6422123291325,21.542921585434353,6.814365947708239,3.0788222295432957,0.2,0.5355546489220763,0.1939121340551198,.1,.06018549127444663,-.1,.571463452970501,.12152678963252792,1.072752370643013,.30532250210623946,.09536209219702954,1.471358712721476,.46716553899076185,.04842746677478945,.9197772135682876,.18571595787006873,.2511887066207075,.1654615263710131,.06735766380405078,.21409019977388702,.1941397811477295,.07209219627083502,.09977559316481487,0];
const lo=[.4,.4,.4,.4,.02,.02,.02,.02,-.1,-.1,-.1,...Array(18).fill(0)],hi=[27,27,27,27,100,.2,100,.2,.1,.1,.1,...Array(18).fill(3)];
function clip(a,i){return Math.max(lo[i],Math.min(hi[i],a));}
function matrix(x,t){let H=Array.from({length:4},(_,i)=>Array.from({length:4},(_,j)=>C(i===j?x[i]/25:0,i===j?x[i]:0)));const put=(a,b,k)=>{let z=k*Math.sqrt(x[a]*x[b]);H[a][b][1]+=z;H[b][a][1]+=z;};
put(0,1,x[8]);put(1,3,(1-t)*x[9]);put(0,3,t*x[9]);put(3,2,x[10]);
const I=Array.from({length:4},(_,i)=>Array.from({length:4},(_,j)=>C(i===j?1:0))),inv=solve(H,I);
return Array.from({length:5},(_,i)=>Array.from({length:5},(_,j)=>{let z=C();for(let a=0;a<4;a++)for(let b=0;b<4;b++)if(B[i][a]&&B[j][b])z=A(z,K(inv[a][b],B[i][a]*B[j][b]));return z;}));
}
let count=0;
function evalSet(x,t,conf,pt){count++;let coeff=matrix(x,t);let res={worst:-99,h2:100,h3:100,worstFreq:0},cs=conf.fixed.concat(conf.cv).concat(conf.extra||[]);
for(const p of pt){const om=2e6*Math.PI*p.f,Y=coeff.map(row=>row.map(v=>K(v,1/(om*1e-9))));const cap=[...x.slice(4,8),...x.slice(11+3*p.ci,14+3*p.ci),...(conf.extraValues||[])];
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

Q[5]=80;lo[5]=.02;hi[5]=100;Q[7]=40;Q[8]=40;
const baseline=[2.8620637892140897,14.515784353199596,15.172353695794211,7.052807039000568,2.103441837242361,0.47980580858538613,0.48433548828731254,0.14922891338268218,0.09196,0.004323991083479032,-0.1,0.4944086688811993,0,1.1739018522300941,0.361460939351354,0,1.0310267528522141,0.3876321344185157,0,0.9181431339271023,0.20419318530463504,0,0.5171236882612166,0.1504806036053823,0,0.2281843320045856,0,0,0,0.2],edges=[
["center_ground",[1,-1]],["parallel_series0",[0,1]],["parallel_series3",[1,2]],["right_shunt_ground",[4,-1]],
["IN_OUT_bridge",[0,2]],["same_Cp_parallel",[0,3]],["same_added_ground_parallel",[3,-1]],
["center_left_tip",[1,3]],["center_right_tip",[1,4]],["IN_right_tip",[0,4]],["OUT_right_tip",[2,4]],["OUT_left_tip",[2,3]]];
const found=[];
for(const [nm,e] of edges)for(const val of [.02,.10,.20]){
 const label=nm+"_"+val;settings[label]={fixed:settings.base.fixed,cv:settings.base.cv,extra:[[3,-1],e],extraValues:[baseline[29],val]};
 const z=baseline.slice();
 for(let ci=0;ci<6;ci++)for(let t=0;t<3;t++)simplex(z,[11+3*ci,13+3*ci],0,settings[label],g5[ci],[.16*.65**t,.20*.65**t],125,30.095,40);
 const r=summary(z,0,label,g31);
 found.push({label,edge:e,val,grid31:r,vector:z});
}
found.sort((a,b)=>{
 const A=a.grid31,B=b.grid31,fa=Math.max(0,30-A.h2)+Math.max(0,30-A.h3),fb=Math.max(0,30-B.h2)+Math.max(0,30-B.h3);return fa-fb||A.worst-B.worst;
});
text({study:"RF-F003 EXP-047 4L 2CV third fixed Q40 PCB pattern C optional",evaluations:count,passed30:found.filter(x=>x.grid31.h2>=30&&x.grid31.h3>=30).length,best:found.slice(0,14).map(x=>({label:x.label,IL:x.grid31.worst,H2:x.grid31.h2,H3:x.grid31.h3}))});
const path="experiments/chatgpt_topology_search/runs/EXP-047/third_pcb_screen_20261017.json";
const p={experiment_id:"EXP-047",constraint_id:"RF-F003",grid:"28x5 tune, 28x31 check",evaluations:count,additional_C1:[3,-1],additional_C1_pf:baseline[29],additional_C2_options:edges,values_pf:[.02,.10,.2],results:found,physical_notes:"PCB pattern C count max3; physical geometries and EM unverified"};
const f=await tools.mcp__GitHub__create_file({repository_full_name:ROOT,path,branch:"main",content:JSON.stringify(p,null,2)+"\n",message:"Record EXP-047 RF-F003 4L two-CV third PCB-C legal edge screen"});
text({saved:path,sha:f.result.commit_sha});
