'use strict';
const $ = id => document.getElementById(id);
const ROOT = new URL('./', location.href);
const LABEL = {collect:'수집',organize:'정리',quiz:'출제',format:'기기 포맷',react:'연출',schedule:'복습 일정',tutor:'수업 튜터'};
const STATUS = {queued:'봇 대기',running:'작업 중',expired:'재접수 대기',completed:'완료',failed:'실패 · 재시도 가능'};
let key = sessionStorage.getItem('kokbot.key') || '', course = '', artifacts = [], jobs = [], pack = null, index = 0, answered = false, example = false;
let attempts = [], pending = JSON.parse(localStorage.getItem('kokbot.pending') || '[]');
let reactions = {};
let learner = localStorage.getItem('kokbot.learner');
if (!learner) { learner='learner_'+crypto.randomUUID().replaceAll('-',''); localStorage.setItem('kokbot.learner',learner); }
function notice(message) { $('notice').textContent=message; }
function safeError(e) { notice(e.message || String(e)); }
function savePending() { localStorage.setItem('kokbot.pending',JSON.stringify(pending)); $('pendingCount').textContent=pending.length ? `전송 대기 ${pending.length}건 · 이 브라우저에 보관 중` : ''; }
async function api(path, body) {
  if (!key) throw Error('팀 키를 먼저 연결해 주세요.');
  const r=await fetch(new URL('api/v1/'+path,ROOT),{method:body===undefined?'GET':'POST',headers:{Authorization:'Bearer '+key,...(body===undefined?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:JSON.stringify(body)});
  const data=await r.json();
  if (!r.ok) throw Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));
  return data;
}
function download(name,data) { const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000); }
function node(tag,text,cls) { const n=document.createElement(tag);n.textContent=text;if(cls)n.className=cls;return n; }
async function refresh() {
  const who=await api('me');$('identity').textContent=`${who.name} · ${who.role} 연결됨`;
  const courses=(await api('courses')).items, select=$('courseSelect');select.replaceChildren();
  courses.forEach(c=>{const o=node('option',c.title);o.value=c.id;select.append(o);});
  if(courses.some(c=>c.id===course)) select.value=course;
  course=select.value;
  if(!course){select.append(new Option('등록된 강의가 없어요',''));jobs=[];artifacts=[];}
  else { const filter='?course_id='+encodeURIComponent(course); [jobs,artifacts]=await Promise.all([api('jobs'+filter),api('artifacts'+filter)]).then(v=>v.map(x=>x.items)); }
  reactions={};const director=latest('react');if(director){const result=await api('artifacts/'+director.id);for(const state of result.result.states)reactions[state.state]=state;}
  $('reviewPlan').textContent='';const schedule=latest('schedule');if(schedule){const result=await api('artifacts/'+schedule.id);const mine=result.result.items.filter(i=>i.learner_id===learner);$('reviewPlan').textContent=mine.length?'일정 봇의 계획: '+mine.map(i=>new Date(i.due_at).toLocaleString('ko-KR')+' · '+i.reason).join(' / '):'일정 봇의 결과가 있습니다. 아직 이 기기의 복습 일정은 없어요.';}
  renderJobs();renderPacks();$('updated').textContent=new Date().toLocaleTimeString('ko-KR');notice('서버의 실제 작업 상태를 불러왔습니다.');
}
function latest(kind) { return artifacts.find(a=>a.kind===kind); }
function renderJobs(){
  $('flow').replaceChildren();
  Object.entries(LABEL).filter(([k])=>k!=='tutor').forEach(([kind,label])=>{const b=node('button',label+' 요청',latest(kind)?'ready':'');b.disabled=!course;b.onclick=()=>enqueue(kind).catch(safeError);$('flow').append(b);});
  $('jobs').replaceChildren();$('jobs').className=jobs.length?'':'empty';
  if(!jobs.length)$('jobs').textContent='등록된 작업이 없습니다.';
  jobs.slice(0,20).forEach(j=>{const row=node('div','','job'),left=node('div',''),right=node('div','');left.append(node('strong',LABEL[j.kind]+' 봇'),node('small',j.id));if(j.error)left.append(node('small',j.error));right.append(node('em',STATUS[j.status]||j.status,j.status));if(j.artifact_id){const b=node('button','결과 JSON','subtle download');b.onclick=async()=>{try{download(j.artifact_id+'.json',await api('artifacts/'+j.artifact_id));}catch(e){safeError(e);}};right.append(b);}row.append(left,right);$('jobs').append(row);});
}
async function enqueue(kind) {
  const previous={organize:'collect',quiz:'organize',format:'quiz',react:'format',schedule:'format'}[kind];
  if(previous&&!latest(previous))throw Error(LABEL[previous]+' 봇의 결과를 먼저 받아야 합니다.');
  const input={artifact_ids:artifacts.map(a=>a.id)};
  await api('jobs',{course_id:course,kind,input});await refresh();notice(LABEL[kind]+' 봇 작업을 요청했습니다. 봇이 가져가면 시작됩니다.');
}
function renderPacks(){const s=$('packSelect'),old=s.value;s.replaceChildren(new Option('학습팩 선택',''));artifacts.filter(a=>a.kind==='format').forEach(a=>s.append(new Option(a.id,a.id)));if([...s.options].some(o=>o.value===old))s.value=old;}
const ctx=$('screen').getContext('2d');
function draw(){
  ctx.fillStyle='#243b2d';ctx.fillRect(0,0,256,64);ctx.fillStyle='#c2dca5';ctx.font='16px "Malgun Gothic", monospace';ctx.textBaseline='top';
  const q=pack?.result.questions[index];
  const lines=q?q.question_lines:['작은 공부 친구','학습팩을 기다려요'];
  lines.slice(0,2).forEach((line,i)=>ctx.fillText(line,0,i*17,224));
  if(q){ctx.font='12px monospace';ctx.fillText('1 '+q.choices[0],0,46,112);ctx.fillText('2 '+q.choices[1],128,46,112);}
  // Static device avatar; runtime animations are separately authored by the director Bot.
  ctx.fillRect(233,7,18,16);ctx.fillRect(233,3,4,5);ctx.fillRect(247,3,4,5);ctx.fillStyle='#243b2d';ctx.fillRect(237,11,2,3);ctx.fillRect(245,11,2,3);
  $('counter').textContent=q?`${index+1} / ${pack.result.questions.length}`:'0 / 0';
  $('choice0').disabled=$('choice1').disabled=!q||answered;
  $('next').disabled=!q||!answered;
  $('questionText').textContent=q?q.question_lines.join(' '):'봇이 만든 학습팩을 선택하거나, 로컬 파일을 열어 주세요.';
}
function validPack(value){
  const p=value?.result||value;
  if(!p||p.display_contract!=='nu40-256x64-font16-v1'||!Array.isArray(p.questions)||!p.questions.length||p.questions.length>100)throw Error('지원되는 학습팩 형식이 아닙니다.');
  for(const q of p.questions){if(!q.id||!Array.isArray(q.question_lines)||q.question_lines.length<1||q.question_lines.length>2||!Array.isArray(q.choices)||q.choices.length!==2||![0,1].includes(q.correct_index)||!Array.isArray(q.explanation_lines)||![...q.question_lines,...q.choices,...q.explanation_lines].every(s=>typeof s==='string'&&s.length<=200))throw Error('학습팩의 문제 형식을 확인해 주세요.');}
  return {id:value.id||'local_'+crypto.randomUUID().replaceAll('-',''),result:p,local:!value.id||value.local};
}
function reaction(state){const selected=reactions[state];if(!selected)return;const pet=document.querySelector('.pixel-pet');pet.dataset.animation=selected.animation;setTimeout(()=>delete pet.dataset.animation,1000);if(selected.sound!=='none'){const Audio=window.AudioContext||window.webkitAudioContext;if(!Audio)return;const audio=new Audio(),osc=audio.createOscillator(),gain=audio.createGain();osc.type='sine';osc.frequency.value=selected.sound==='chime'?660:330;gain.gain.setValueAtTime(.035,audio.currentTime);gain.gain.exponentialRampToValueAtTime(.001,audio.currentTime+.16);osc.connect(gain).connect(audio.destination);osc.start();osc.stop(audio.currentTime+.18);osc.onended=()=>audio.close();}}
function loadPack(value,isExample=false){pack=validPack(value);index=0;answered=false;example=isExample;$('feedback').textContent='';$('packBadge').textContent=isExample?'합성 예시':pack.local?'로컬 학습팩':'봇 결과';draw();reaction('learning');}
async function choose(n){
  if(!pack||answered)return;answered=true;const q=pack.result.questions[index];
  $('feedback').textContent=(n===q.correct_index?'정답이에요. ':'다시 기억해 봐요. ')+q.explanation_lines.join(' ');draw();
  reaction(n===q.correct_index?'correct':'incorrect');
  if(example)return;
  const attempt={id:'attempt_'+crypto.randomUUID().replaceAll('-',''),learner_id:learner,pack_id:pack.id,question_id:q.id,selected_index:n,answered_at:new Date().toISOString()};attempts.push(attempt);
  if(pack.local){notice('로컬 학습입니다. 풀이 기록 저장으로 일정 봇에게 전달하세요.');return;}
  pending.push(attempt);savePending();await retryPending();
}
async function retryPending(){if(!key)return;for(const item of [...pending]){try{await api('attempts',item);pending=pending.filter(a=>a.id!==item.id);savePending();}catch(e){notice('풀이 기록을 보관했습니다. 연결 후 재전송해 주세요: '+e.message);break;}}}
$('connectForm').onsubmit=async e=>{e.preventDefault();key=$('apiKey').value.trim();sessionStorage.setItem('kokbot.key',key);$('apiKey').value='';try{await refresh();await retryPending();}catch(e){safeError(e);}};
$('disconnect').onclick=()=>{key='';sessionStorage.removeItem('kokbot.key');location.reload();};
$('refresh').onclick=()=>refresh().catch(safeError);
$('courseSelect').onchange=()=>{course=$('courseSelect').value;refresh().catch(safeError);};
$('courseForm').onsubmit=async e=>{e.preventDefault();try{const c=await api('courses',{title:$('courseTitle').value,source_url:$('courseUrl').value});course=c.id;await api('jobs',{course_id:c.id,kind:'collect',input:{url:c.source_url}});await refresh();}catch(e){safeError(e);}};
$('packSelect').onchange=async()=>{if(!$('packSelect').value)return;try{loadPack(await api('packs/'+$('packSelect').value));}catch(e){safeError(e);}};
$('choice0').onclick=()=>choose(0).catch(safeError);$('choice1').onclick=()=>choose(1).catch(safeError);
$('next').onclick=()=>{if(!pack||!answered)return;if(index+1>=pack.result.questions.length){$('feedback').textContent='학습을 마쳤어요. 처음부터 다시 볼 수 있어요.';index=0;}else{index++;$('feedback').textContent='';}answered=false;draw();};
$('importPack').onchange=async e=>{try{const file=e.target.files[0];if(file.size>1048576)throw Error('1 MiB 이하의 학습팩을 열어 주세요.');const value=JSON.parse(await file.text());value.local=true;loadPack(value);notice('서버 연결 없이 로컬 학습팩을 열었습니다.');}catch(err){safeError(err);}};
$('exportPack').onclick=()=>{if(pack)download(pack.id+'.json',pack);else notice('학습팩을 먼저 선택해 주세요.');};
$('exportAttempts').onclick=()=>download('kokbot-attempts.json',{schema:'kokbot-attempts-v1',items:attempts});
$('retryAttempts').onclick=()=>retryPending().catch(safeError);
$('demo').onclick=()=>loadPack({id:'example_and_gate',local:true,result:{title:'AND 게이트 · 합성 예시',display_contract:'nu40-256x64-font16-v1',quiz_artifact_id:'example_quiz',questions:[{id:'q1',source_question_id:'q1',question_lines:['AND: A=1, B=0','출력은 무엇일까요?'],choices:['0','1'],correct_index:0,explanation_lines:['둘 다 1일 때만 1']},{id:'q2',source_question_id:'q2',question_lines:['AND: A=1, B=1','출력은 무엇일까요?'],choices:['0','1'],correct_index:1,explanation_lines:['두 입력이 모두 1']}] }},true);
fetch(new URL('healthz',ROOT)).then(r=>{if(!r.ok)throw Error();return r.json();}).then(h=>{$('serverState').textContent='협업 서버 연결 가능';$('revision').textContent=h.revision.slice(0,7);}).catch(()=>{$('serverState').textContent='로컬 파일 학습 모드';});
savePending();draw();if(key)refresh().catch(safeError);
