// 음성 대조: 일부러 실패하는 검사를 자식 프로세스로 돌려 FAIL과 0이 아닌 종료코드를 확인한다.
const {spawnSync}=require('child_process'),path=require('path');
if(process.argv[2]==='child'){const {H}=require('./harness');const h=H('negative-child');(async()=>{
 await h.ck('일부러 실패: 문자열 반환',async()=>'not true');await h.ck('일부러 실패: undefined',async()=>{});await h.ck('일부러 실패: 1(참 같은 값)',async()=>1);
 await h.ck('일부러 실패: 예외',async()=>{throw new Error('boom')});await h.ck('통과 대조: true',async()=>true);h.done()})();return}
const r=spawnSync(process.execPath,[__filename,'child'],{encoding:'utf8'});console.log(r.stdout);
const fails=(r.stdout.match(/^FAIL /gm)||[]).length,passes=(r.stdout.match(/^PASS /gm)||[]).length;
const ok=r.status!==0&&fails===4&&passes===1;
console.log(`음성 대조: 자식 종료코드=${r.status}, FAIL ${fails}건(기대 4), PASS ${passes}건(기대 1) → ${ok?'PASS(하네스가 실패를 잡음)':'FAIL'}`);
process.exitCode=ok?0:1;
