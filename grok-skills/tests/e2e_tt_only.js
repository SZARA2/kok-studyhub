// 4번 단독: lecture.md 없이 익명 가상 시간표만으로 만든 웹. 사용: node e2e_tt_only.js <web.html> <screenshots dir>
const {H,chromium,CHROME}=require('./harness');const __h=H('e2e_tt_only');const ck=(n,f)=>__h.ck(n,f);const fs=require('fs'),path=require('path');
const [WEB,SHOT]=process.argv.slice(2).map(p=>path.resolve(p));fs.mkdirSync(SHOT,{recursive:true});
(async()=>{const b=await chromium.launch({executablePath:CHROME});const p=await (await b.newContext({viewport:{width:1100,height:1100}})).newPage();const errs=[];p.on('pageerror',e=>errs.push(e.message));
await p.goto('file://'+WEB);await p.evaluate(()=>localStorage.clear());await p.reload();await p.waitForTimeout(500);
await ck('홈: lecture.md 없음 안내',async()=>(await p.textContent('[data-testid=no-lecture]')).includes('lecture.md')||'없음');
await ck('홈: 1~3번 상태 "자료 필요", 4번은 완료',async()=>{const s=[];for(const n of [1,2,3,4])s.push(await p.textContent('[data-testid=status-'+n+']'));return s.slice(0,3).every(x=>x.includes('자료 필요'))&&s[3].startsWith('완료')||s.join('|')});
await ck('1~3번은 추측 생성 없이 자료 요청만',async()=>{for(const n of ['1','2','3']){await p.keyboard.press('Escape');await p.keyboard.press(n);if(!(await p.isVisible('[data-testid=need-lecture-'+n+']')))return n+' 안내 없음';if(n==='1'&&(await p.$$('.opt')).length)return '드릴 보기 생성됨';if(n==='3'&&await p.$('[data-testid=lab-frame]'))return '실험실 생성됨'}await p.keyboard.press('Escape');return true});
await ck('4번: 주간표 블록 표시',async()=>{await p.keyboard.press('4');const n=(await p.$$('[data-testid^=blk-]:not([data-testid^=blk-raw])')).length;await p.screenshot({path:path.join(SHOT,'14-tt-only.png'),fullPage:true});return n>0||'블록 0'});
await ck('4번: 마감 추측 없음(입력 일정 0건 → 확정 마감 행 없음)',async()=>!/확정/.test(await p.textContent('#tb'))||'확정 표기 있음');
await ck('4번: 겹치지 않는 계획 추가 → 새로고침 후 유지',async()=>{await p.fill('[data-testid=sch-title]','자습');await p.selectOption('[data-testid=sch-day]','일');await p.fill('[data-testid=sch-start]','20:00');await p.fill('[data-testid=sch-end]','21:00');await p.click('[data-testid=sch-add]');const m=await p.textContent('[data-testid=sch-msg]');await p.reload();await p.waitForTimeout(400);await p.keyboard.press('4');return m.includes('추가했습니다')&&(await p.textContent('#tb')).includes('자습')||m});
await ck('JS 오류 없음',async()=>errs.length===0||errs.join(';'));
await b.close();__h.done()})().catch(e=>{console.error(e);process.exitCode=1});
