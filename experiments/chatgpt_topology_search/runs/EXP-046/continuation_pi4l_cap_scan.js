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

const varEdges=[
["series0",[[3,-1],[4,-1],[0,1]]],
["series1",[[3,-1],[4,-1],[1,2]]],
["total_bridge",[[3,-1],[4,-1],[0,2]]],
["tip_bridge",[[3,-1],[4,-1],[3,4]]],
["left_feedback",[[3,-1],[4,-1],[1,3]]],
["right_feedback",[[3,-1],[4,-1],[1,4]]],
["in_right_tip",[[3,-1],[4,-1],[0,4]]],
["out_left_tip",[[3,-1],[4,-1],[2,3]]]
];
let countStart=0;
const results=[];
for(const [label,cv] of varEdges){
 const conf={fixed:[[3,-1],[4,-1],[0,1],[1,2]],cv,extra:[[0,2]],flip:false};
 settings[label]=conf;
 let solns=[];
 for(let seed=0;seed<2;seed++){
 const x=oldx.slice();
 if(seed===1){
   x[0]=3.0;x[1]=4.3;x[2]=17;x[3]=12;
   x[4]=.35;x[5]=.20;x[6]=.2;x[7]=.2;
   x[8]=-.08;x[9]=.1;x[10]=.08;
   for(let b=0;b<6;b++){x[11+3*b]=2.0*Math.pow(0.86,b);x[12+3*b]=.7*Math.pow(.86,b);x[13+3*b]=.6;}
 }
 x[29]=.1;
 const start=summary(x,1,label,g5),initialCount=count;
 let delta=[.5,.8,2,2,.16,.2,.06,.06,.04,.04,.04,0,0,0];
 for(let step=0;step<3;step++){
   for(let ci=0;ci<6;ci++){
    simplex(x,[11+ci*3,12+ci*3,13+ci*3],1,conf,g5[ci],[.45,.45,.35].map(z=>z*Math.pow(.6,step)),145,30.04,6);
   }
   for(const id of [0,1,2,3,4,5,6,7,8,9,10,29]){
      let d=id===29?.045:delta[id]*Math.pow(.7,step);
      let vals=[-3,-1,0,1,3],scmin=1e10,best=x[id];
      for(let z of vals){
       const trial=x.slice();trial[id]=clip(x[id]+z*d,id);
       const rr=summary(trial,1,label,g5);
       const ss=rr.worst+15*(Math.max(0,30.05-rr.h2)**2+Math.max(0,30.05-rr.h3)**2);
       if(ss<scmin){scmin=ss;best=trial[id];}
      }
      x[id]=best;
   }
 }
 const fine=summary(x,1,label,g31),coarse=summary(x,1,label,g5);
 solns.push({seed,start,coarse,fine,vector:x,evalCount:count-initialCount});
 }
 const winner=solns.sort((a,b)=>{
  const fa=Math.max(0,30-a.fine.h2)+Math.max(0,30-a.fine.h3),fb=Math.max(0,30-b.fine.h2)+Math.max(0,30-b.fine.h3);
  return fa-fb||a.fine.worst-b.fine.worst;
 })[0];
 results.push({name:label,seed:winner.seed,fine:winner.fine,vector:winner.vector});
}
text({experiment:"EXP-046 pi-4L guided search",source:"RF-T005 original GitHub S2P 28x31 recheck",loops:count,summary:results.map(r=>({name:r.name,IL:r.fine.worst,H2:r.fine.h2,H3:r.fine.h3})),best:results.sort((a,b)=>Math.max(0,30-a.fine.h2)+Math.max(0,30-a.fine.h3)-Math.max(0,30-b.fine.h2)-Math.max(0,30-b.fine.h3)||a.fine.worst-b.fine.worst).slice(0,3)});
