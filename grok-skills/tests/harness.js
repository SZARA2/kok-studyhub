// 엄격 하네스: 검사 함수의 반환값이 정확히 true일 때만 PASS. 그 외(문자열·undefined·객체·예외)는 FAIL+진단.
// FAIL이 하나라도 있으면 process.exitCode=1.
// H(음성 대조·식 단위 테스트)는 순수 node만 필요하다. chromium/CHROME은 처음 접근할 때만 ./browser.js(playwright)를 불러온다.
const fs=require('fs'),path=require('path');
const REPO=path.resolve(__dirname,'..'),DEMO=path.resolve(REPO,process.env.KOK_DEMO_DIR||'demo-mit6004');
const now=()=>new Date().toLocaleString('sv-SE',{timeZone:'Asia/Seoul'})+' KST';
function H(suite){const R=[];return{R,
 async ck(name,fn){let r,d='';try{r=await fn()}catch(e){r=undefined;d='예외: '+String(e&&e.message||e).split('\n')[0]}
  const pass=r===true;if(!pass&&!d)d='반환값 '+(typeof r)+': '+JSON.stringify(r);R.push({name,pass,at:now(),detail:pass?'':d});
  console.log((pass?'PASS ':'FAIL ')+name+(pass?'':' — '+d));if(!pass)process.exitCode=1},
 done(out){const p=R.filter(r=>r.pass).length,f=R.length-p;console.log(`[${suite}] 합계 PASS ${p} / FAIL ${f} / 전체 ${R.length}`);if(f)process.exitCode=1;
  if(out){fs.writeFileSync(out+'.json',JSON.stringify(R,null,1));fs.writeFileSync(out+'.md',`# ${suite}\n\n| 검사 | 결과 | 시각 | 진단 |\n|---|---|---|---|\n`+R.map(r=>`| ${r.name} | ${r.pass?'PASS':'FAIL'} | ${r.at} | ${String(r.detail).replace(/\|/g,'/')} |`).join('\n')+`\n\n합계 PASS ${p} / FAIL ${f}\n`)}
  return{p,f}}}}
module.exports={H,now,REPO,DEMO};
Object.defineProperty(module.exports,'chromium',{enumerable:true,get:()=>require('./browser').chromium});
Object.defineProperty(module.exports,'CHROME',{enumerable:true,get:()=>require('./browser').CHROME});
