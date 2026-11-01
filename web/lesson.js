'use strict';
(()=>{
 const pack=JSON.parse(document.getElementById('lesson-data').textContent),$=id=>document.getElementById(id);
 const storageKey='kokbot.lesson.v1.'+pack.id;let index=0,phase='question',records=[],seen=new Set(),feedback=null;
 // A content fingerprint prevents an edited lesson from restoring incompatible progress.
 let hash=2166136261;for(const ch of JSON.stringify(pack)){hash^=ch.charCodeAt(0);hash=Math.imul(hash,16777619);}const fingerprint=(hash>>>0).toString(16);
 try{const saved=JSON.parse(localStorage.getItem(storageKey)||'null');if(saved?.fingerprint===fingerprint&&Number.isInteger(saved.index)&&saved.index>=0&&saved.index<pack.questions.length&&['question','feedback','finished'].includes(saved.phase)&&Array.isArray(saved.records)){index=saved.index;phase=saved.phase;records=saved.records;feedback=saved.feedback;}}catch{}
 function state(){const q=pack.questions[index];return {version:1,lessonId:pack.id,phase,index,total:pack.questions.length,question:phase==='finished'?null:{id:q.id,prompt:q.prompt,choices:[...q.choices],display:q.display||null},feedback:feedback?{...feedback}:null,attemptCount:records.length};}
 function save(){try{localStorage.setItem(storageKey,JSON.stringify({fingerprint,index,phase,records,feedback}));}catch{$('notice').textContent='이 브라우저는 자동 저장을 허용하지 않습니다. 닫기 전에 풀이 기록을 저장해 주세요.';}}
 function render(){
   const q=pack.questions[index],finished=phase==='finished';$('title').textContent=pack.title;$('badge').textContent=pack.synthetic?'합성 예시 · 실제 강의 아님':'개인 학습 웹';
   $('progress').textContent=finished?'학습 완료':`${index+1} / ${pack.questions.length}`;$('bar').style.width=(finished?100:index/pack.questions.length*100)+'%';
   $('prompt').textContent=finished?'오늘 배운 내용을 잘 챙겼어요.':q.prompt;
   $('choice1').textContent=q.choices[0];$('choice2').textContent=q.choices[1];
   $('answer1').hidden=$('answer2').hidden=finished;$('answer1').disabled=$('answer2').disabled=phase!=='question';
   $('feedback').hidden=phase==='question';$('feedback').textContent=finished?`${records.filter(r=>r.correct).length} / ${records.length} 정답 · 풀이 기록을 저장할 수 있어요.`:feedback?(feedback.correct?'정답이에요!\n':'다시 기억해 볼까요?\n')+feedback.explanation:'';
   $('pet').textContent=finished?'◕ᴥ◕':feedback?(feedback.correct?'✧ᴥ✧':'◕ᴥ◕'):'▰ᴥ▰';
   $('next').hidden=phase!=='feedback';$('restart').hidden=!finished;$('hint').textContent=phase==='question'?'버튼 1=A · 버튼 2=B. 키보드 숫자 1·2도 사용할 수 있어요.':phase==='feedback'?'버튼 1 또는 2를 한 번 더 누르면 다음으로 넘어가요.':'학습을 마쳤어요. 버튼을 계속 눌러도 새 풀이가 생기지 않아요.';
   window.dispatchEvent(new CustomEvent('kokbot:state',{detail:state()}));
 }
 function press(button,eventId){
   if(button!==1&&button!==2)return {accepted:false,reason:'button must be 1 or 2'};
   if(eventId!==undefined){if(typeof eventId!=='string'||!eventId||eventId.length>160)return {accepted:false,reason:'invalid eventId'};if(seen.has(eventId))return {accepted:false,reason:'duplicate'};seen.add(eventId);if(seen.size>2000)seen.delete(seen.values().next().value);}
   if(phase==='finished')return {accepted:false,reason:'finished',state:state()};
   if(phase==='feedback'){if(index+1>=pack.questions.length)phase='finished';else{index++;phase='question';feedback=null;}}
   else{const q=pack.questions[index];feedback={correct:button-1===q.correct_index,explanation:q.explanation};records.push({id:crypto.randomUUID(),lesson_id:pack.id,question_id:q.id,selected_index:button-1,correct:feedback.correct,answered_at:new Date().toISOString()});phase='feedback';}
   save();render();return {accepted:true,state:state()};
 }
 $('answer1').onclick=()=>press(1);$('answer2').onclick=()=>press(2);$('next').onclick=()=>press(1);
 $('restart').onclick=()=>{index=0;phase='question';records=[];feedback=null;seen.clear();save();render();};
 document.addEventListener('keydown',e=>{if(e.repeat||e.ctrlKey||e.metaKey||e.altKey||e.target.closest('input,textarea,select,[contenteditable]'))return;const b=e.code==='Digit1'||e.code==='Numpad1'?1:e.code==='Digit2'||e.code==='Numpad2'?2:null;if(b){e.preventDefault();press(b,'keyboard:'+e.timeStamp+':'+e.code);}});
 $('export').onclick=()=>{const blob=new Blob([JSON.stringify({schema:'kokbot-attempts-v1',lesson_id:pack.id,items:records},null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=pack.id+'-attempts.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);};
 window.kokbot=Object.freeze({getState:state,press,exportAttempts:()=>JSON.parse(JSON.stringify(records))});render();
})();
