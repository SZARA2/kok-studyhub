// node: safe_expr.js 거부(실행 없음) + lab.json 기본값/극단값/검산
const {H}=require('./harness');const S=require('../skills/kok-concept-lab/resources/safe_expr.js');const L=require(require('path').join(require('./harness').DEMO,'lab/lab.json'));const h=H('safe_expr.js');
globalThis.__PWN=0;
const BAD=["__import__('os')","().__class__.__bases__[0].__subclasses__()","constructor","'x'.constructor.constructor('return 1')()","N.constructor","window","document","globalThis","globalThis.__PWN=1","lambda: 1","function(){return 1}","()=>1","x=>x","N=1","N+=1","eval('1')","alert(1)","Math.random()","Math.constructor","this","process.exit(1)","N?1:2","Function('return 1')()","[1][0]","{a:1}"];
const names=L.variables.map(v=>v.name).concat(L.outputs.map(o=>o.name),['t','m']);
(async()=>{
for(const e of BAD)await h.ck('거부: '+e,async()=>{try{S.compile(e,names);return '컴파일됨(거부 안 됨)'}catch(x){return globalThis.__PWN===0&&x instanceof Error}});
function run(V){const env={...V};for(const o of L.outputs)env[o.name]=S.compile(o.expr,names)(env);return env}
const d=Object.fromEntries(L.variables.map(v=>[v.name,v.value]));const r=run(d);
for(const o of L.outputs)await h.ck(`기본값 ${o.name}=${r[o.name]} ≈ ${o.expected}`,async()=>Math.abs(r[o.name]-o.expected)<1e-9);
for(const k of ['min','max']){const e=run(Object.fromEntries(L.variables.map(v=>[v.name,v[k]])));await h.ck(`극단값(${k}) 모든 출력 유한`,async()=>L.outputs.every(o=>Number.isFinite(e[o.name])))}
for(const c of L.checks){const e=run(c.vars);await h.ck(`검산 ${JSON.stringify(c.vars)} ${c.out}=${e[c.out]}`,async()=>Math.abs(e[c.out]-c.expect)<1e-9)}
const LIMS=[['1'+'+1'.repeat(150),'길이'],['-'.repeat(40)+'1','깊이'],['('.repeat(40)+'1'+')'.repeat(40),'깊이(괄호)'],[Array(120).fill('N').join('+'),'노드'],['2**65','지수 **'],['Math.pow(10,400)','지수 pow'],['1/0','Infinity'],['0/0','NaN'],['Math.log(0)','-Infinity'],['Math.sqrt(-1)','NaN'],['Math.exp(1000)','overflow']];
for(const [e,w] of LIMS)await h.ck('상한/유한성 오류: '+w,async()=>{try{S.compile(e,names)({N:1,M:1,p:0.5,t:0});return '오류 없음'}catch(x){return x instanceof Error}});
for(const bad of [Infinity,NaN,'abc'])await h.ck('유한하지 않은 입력 거부: '+bad,async()=>{try{S.compile('N',['N'])({N:bad});return '통과됨'}catch(x){return x instanceof Error}});
await h.ck('지수 경계 2**64 허용',async()=>S.compile('2**64',[])({})===2**64);
await h.ck('컴파일 캐시: 같은 식 재컴파일 시 캐시 크기 불변',async()=>{const a=S.cacheSize();S.compile(L.outputs[0].expr,names);return S.cacheSize()===a});
h.done(require('path').resolve(__dirname,'logs/test_safe_expr'))})();
