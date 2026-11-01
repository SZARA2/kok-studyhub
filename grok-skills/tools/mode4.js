/* 4 일정 (v1.2.0: 시간표 기반 + 날짜가 명시된 항목만 오늘/내일·D-day·지난 일정 분리·카드/슬라이드) */
var DAYS=['월','화','수','목','금','토','일'],KEY=DATA.storeKey||'kok-sch',PX=0.8;
function ld(k,def){try{var s=JSON.parse(localStorage.getItem(KEY+k));if(s!=null)return s}catch(e){}return JSON.parse(JSON.stringify(def))}
function sv(k,v){try{localStorage.setItem(KEY+k,JSON.stringify(v))}catch(e){}}
var TT=DATA.timetable?ld(':tt',DATA.timetable.classes):null,IT=ld(':items',DATA.schedule.items),MAT=ld(':mat',DATA.schedule.materials||[]),EDIT=null;
function mn(t){return(t&&/^\d\d:\d\d$/.test(t))?(+t.slice(0,2))*60+(+t.slice(3)):null}
function rv(c){return !c.confirmed&&c.needs_review&&c.needs_review.length}
function rng(c){var s=mn(c.start),e=mn(c.end);if(e==null)e=24*60;else if(rv(c))e+=10;if(rv(c)&&c.needs_review.some(function(r){return r.field==='start'}))s-=10;return[s,e]}
function dayOf(it){if(it.day)return it.day;if(/^\d{4}-\d\d-\d\d$/.test(it.date||''))return DAYS[(new Date(it.date+'T00:00:00').getDay()+6)%7];return null}
function clash(day,s,e,skip){if(!TT||!day||s==null)return null;if(e==null)e=s+1;return TT.filter(function(c){return c.day===day}).filter(function(c){var r=rng(c);return s<r[1]&&e>r[0]})[0]||null}
function tm(it){return it.start?(it.start+(it.end?'~'+it.end:'')):(it.time||'시각 미정')}
function sch(){var S=DATA.schedule,h='';
 if(!TT){$('#sch').innerHTML='<div class="note" data-testid="tt-request"><b>시간표가 필요합니다.</b> 4번 일정 기능은 시간표를 기준으로 동작합니다. 봇 채팅에 시간표 <b>이미지·PDF·텍스트</b> 중 하나를 보내 주세요. (학교 사이트·LMS 로그인으로 가져오지 않습니다.) 1~3번 기능은 시간표 없이도 그대로 쓸 수 있습니다.</div>';return}
 var T=DATA.timetable;h+='<div class="note" data-testid="sch-note">'+esc(S.note)+'</div><p class="small">'+esc(T.recurrence)+' · '+esc(T.term_note)+'<br>'+esc(T.empty_cell_note)+'<br>출처: '+esc(T.source)+'</p>';
 h+='<h3>주간 시간표</h3><div id="wk"></div><p class="small">점선 테두리 = 확인 필요(needs_review). 아래가 흐린 블록 = 종료 시각 미확인. 겹침 검사는 확인 전 추정 종료에 10분 여유, 종료 미확인은 그날 끝까지 수업으로 봅니다.</p>';
 h+='<h3>확인·수정 <span class="small" id="rvc" data-testid="rv-count"></span></h3><div id="rv"></div>';
 h+='<h3>강의 자료 연결</h3><div id="mat"></div>';
 h+='<h3>날짜가 명시된 일정 <span class="small">(원문/사용자가 날짜를 준 항목만 · 날짜 없는 항목은 추측하지 않음)</span></h3><div id="dated" data-testid="dated"></div>';
 h+='<h3>계획</h3><div><input id="nt" data-testid="sch-title" placeholder="할 일 (예: 1234 입력해도 단축키 아님)"> <select id="ndy" data-testid="sch-day">'+DAYS.map(function(d){return'<option>'+d+'</option>'}).join('')+'</select> <input id="ns" type="time" data-testid="sch-start"> ~ <input id="ne" type="time" data-testid="sch-end"> <button id="add" data-testid="sch-add">추가</button> <button id="cxl" class="hidden" data-testid="sch-cancel">편집 취소</button></div><div id="msg" class="small" data-testid="sch-msg" role="status"></div><p class="small">직접 추가한 항목 라벨: 확정(사용자 입력). 과제·시험 마감은 사용자가 직접 입력할 때만 확정됩니다.</p>';
 h+='<table><thead><tr><th>요일/날짜</th><th>시각</th><th>내용</th><th>라벨·근거</th><th>상태</th><th></th></tr></thead><tbody id="tb"></tbody></table>';
 $('#sch').innerHTML=h;$('#add').onclick=addItem;$('#cxl').onclick=function(){EDIT=null;form()};draw()}
function form(it){$('#nt').value=it?it.title:'';$('#ndy').value=it?(dayOf(it)||'월'):'월';$('#ns').value=it?(it.start||''):'';$('#ne').value=it?(it.end||''):'';$('#add').textContent=it?'수정 저장':'추가';$('#cxl').classList.toggle('hidden',!it)}
function addItem(){var t=$('#nt').value.trim(),d=$('#ndy').value,s=$('#ns').value,e=$('#ne').value,m=$('#msg');if(!t){m.textContent='내용을 입력하세요.';return}
 if(s&&e&&mn(e)<=mn(s)){m.textContent='끝 시각이 시작보다 늦어야 합니다.';return}
 var c=clash(d,mn(s),e?mn(e):null);if(c){m.className='small bad';m.textContent='추가 안 됨: '+d+' '+(s||'')+' 은(는) 수업 「'+c.title+'」('+c.start+'~'+(c.end||'종료 미확인')+(rv(c)?', 확인 전 추정':'')+')과 겹칩니다.';return}
 if(EDIT){IT.forEach(function(it){if(it.id===EDIT){it.title=t;it.day=d;delete it.date;delete it.time;it.start=s||'';it.end=e||'';it.edited=true}});m.className='small';m.textContent='수정했습니다.';EDIT=null}
 else{IT.push({id:'u'+Date.now(),title:t,day:d,start:s||'',end:e||'',label:'확정',source:'사용자 직접 입력(웹)',done:false});m.className='small';m.textContent='추가했습니다.'}
 sv(':items',IT);form();draw()}
function draw(){var used=DAYS.slice(0,5);TT.concat(IT).forEach(function(x){var d=dayOf(x);if(d&&used.indexOf(d)<0)used.push(d)});used.sort(function(a,b){return DAYS.indexOf(a)-DAYS.indexOf(b)});
 var lo=9*60,hi=18*60;TT.forEach(function(c){var r=rng(c);lo=Math.min(lo,mn(c.start));if(c.end)hi=Math.max(hi,mn(c.end));else hi=Math.max(hi,mn(c.start)+180)});lo=Math.floor(lo/60)*60;hi=Math.ceil(hi/60)*60+60;var H=(hi-lo)*PX;
 var g='<div class="wk" style="grid-template-columns:40px repeat('+used.length+',1fr)"><div></div>'+used.map(function(d){return'<div class="wh">'+d+'</div>'}).join('')+'<div class="wt" style="height:'+H+'px">';
 for(var m=lo;m<hi;m+=60)g+='<span style="top:'+((m-lo)*PX)+'px">'+(m/60)+'</span>';g+='</div>';
 used.forEach(function(d){g+='<div class="wc" data-testid="col-'+d+'" style="height:'+H+'px">';for(var m=lo;m<hi;m+=60)g+='<i style="top:'+((m-lo)*PX)+'px"></i>';
  TT.filter(function(c){return c.day===d}).forEach(function(c){var s=mn(c.start),e=c.end?mn(c.end):hi;g+='<div class="cb'+(rv(c)?' nr':'')+(c.end?'':' open')+'" data-testid="blk-'+c.id+'" data-day="'+d+'" style="top:'+((s-lo)*PX)+'px;height:'+((e-s)*PX)+'px"><b>'+esc(c.title)+'</b><br><span data-testid="blk-raw-'+c.id+'">'+esc(c.raw_label)+'</span><br><span class="small">'+esc(c.start)+'~'+esc(c.end||'종료 미확인')+'</span></div>'});
  IT.filter(function(it){return dayOf(it)===d&&it.start}).forEach(function(it){var s=mn(it.start),e=it.end?mn(it.end):s+30;if(s<lo||s>hi)return;g+='<div class="ib'+(it.label==='제안'?' sg':'')+(it.done?' dn':'')+'" data-testid="iblk-'+it.id+'" style="top:'+((s-lo)*PX)+'px;height:'+Math.max(14,(e-s)*PX)+'px">'+(it.label==='제안'?'제안 · ':'')+esc(it.title)+'</div>'});g+='</div>'});
 $('#wk').innerHTML=g+'</div>';
 var n=TT.filter(rv).length;$('#rvc').textContent='확인 필요 '+n+'건 / 전체 '+TT.length+'건';
 $('#rv').innerHTML='<table><thead><tr><th>요일</th><th>과목명</th><th>시작</th><th>종료</th><th>원문 표기(강의실 등)</th><th>확인 필요 이유</th><th></th></tr></thead><tbody>'+TT.map(function(c){return'<tr><td>'+esc(c.day)+'</td><td><input data-testid="rv-title-'+c.id+'" data-f="title" data-c="'+c.id+'" value="'+esc(c.title)+'"></td><td><input data-testid="rv-start-'+c.id+'" data-f="start" data-c="'+c.id+'" value="'+esc(c.start)+'" size="5" placeholder="HH:MM"></td><td><input data-testid="rv-end-'+c.id+'" data-f="end" data-c="'+c.id+'" value="'+esc(c.end||'')+'" size="5" placeholder="미확인"></td><td><input data-testid="rv-raw-'+c.id+'" data-f="raw_label" data-c="'+c.id+'" value="'+esc(c.raw_label)+'" size="8"></td><td class="small">'+(c.needs_review.length?c.needs_review.map(function(r){return esc(r.field)+': '+esc(r.reason)}).join('<br>'):'-')+'</td><td><span data-testid="rv-st-'+c.id+'" class="'+(rv(c)?'undone':'doneTxt')+'">'+(rv(c)?'확인 필요':'확인됨')+'</span><br><button data-ok="'+c.id+'" data-testid="rv-ok-'+c.id+'">'+(rv(c)?'확인':'다시 저장')+'</button></td></tr>'}).join('')+'</tbody></table><div id="rvm" class="small" data-testid="rv-msg"></div>';
 document.querySelectorAll('[data-ok]').forEach(function(b){b.onclick=function(){var id=b.dataset.ok,v={};document.querySelectorAll('[data-c="'+id+'"]').forEach(function(i){v[i.dataset.f]=i.value.trim()});
  if(!v.title||mn(v.start)==null||(v.end&&mn(v.end)==null)||(v.end&&mn(v.end)<=mn(v.start))){$('#rvm').textContent='시각은 HH:MM 형식, 종료는 시작보다 늦게 입력하세요.';return}
  TT.forEach(function(c){if(c.id===id){c.title=v.title;c.start=v.start;c.end=v.end||null;c.raw_label=String(v.raw_label);if(v.end){c.resolved=(c.resolved||[]).concat(c.needs_review);c.needs_review=[];c.confirmed=true}else{c.needs_review=c.needs_review.filter(function(r){return r.field==='end'});c.confirmed=false}}});sv(':tt',TT);$('#rvm').textContent=v.end?'확인했습니다.':'종료 시각이 비어 있어 확인 필요로 남깁니다.';draw()}});
 $('#mat').innerHTML=MAT.map(function(m){return'<div>'+esc(m.title)+' → <select data-testid="mat-'+m.id+'" data-mat="'+m.id+'"><option value="">미연결 (과목 선택)</option>'+TT.map(function(c){return'<option value="'+c.id+'"'+(m.linked_course===c.id?' selected':'')+'>'+esc(c.day+' '+c.title)+'</option>'}).join('')+'</select> <b data-testid="mat-st-'+m.id+'">'+(m.linked_course?'연결됨(사용자 선택)':'미연결')+'</b><div class="small">'+esc(m.reason||'')+'</div></div>'}).join('')||'<p class="small">자료 없음</p>';
 document.querySelectorAll('[data-mat]').forEach(function(s){s.onchange=function(){MAT.forEach(function(m){if(m.id===s.dataset.mat){m.linked_course=s.value||null;m.status=s.value?'연결됨':'미연결'}});sv(':mat',MAT);draw()}});
 var srt=IT.slice().sort(function(a,b){return(DAYS.indexOf(dayOf(a))+(a.start||a.time||'')).localeCompare(DAYS.indexOf(dayOf(b))+(b.start||b.time||''))});
 dated();$('#tb').innerHTML=srt.map(function(it){return'<tr><td>'+esc(it.date?it.date+' ('+(dayOf(it)||'-')+')':(it.day||'요일 미정')+' (매주)')+'</td><td>'+esc(tm(it))+'</td><td>'+esc(it.title)+'</td><td class="small">'+esc(it.label)+'<br>근거: '+esc(it.source)+'</td><td class="'+(it.done?'doneTxt':'undone')+'" data-testid="state-'+it.id+'">'+(it.done?'완료':'미완료')+'</td><td><button data-tg="'+it.id+'" data-testid="tg-'+it.id+'">'+(it.done?'되돌리기':'완료')+'</button> <button data-ed="'+it.id+'" data-testid="ed-'+it.id+'">편집</button></td></tr>'}).join('');
 document.querySelectorAll('[data-tg]').forEach(function(b){b.onclick=function(){IT.forEach(function(it){if(it.id===b.dataset.tg)it.done=!it.done});sv(':items',IT);draw()}});
 document.querySelectorAll('[data-ed]').forEach(function(b){b.onclick=function(){var it=IT.filter(function(x){return x.id===b.dataset.ed})[0];EDIT=it.id;form(it);$('#msg').textContent='편집 중: 값을 고치고 「수정 저장」을 누르세요.'}})}
function kNow(){return window.__KOK_NOW?new Date(window.__KOK_NOW):new Date()}
function ymd(d){return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)}
function hhmm(it){var x=it.start||it.time||'';return /^\d\d:\d\d$/.test(x)?x:null}
function datedInfo(it){var n=kNow(),t0=new Date(ymd(n)+'T00:00:00'),d=new Date(it.date+'T00:00:00'),dd=Math.round((d-t0)/864e5),hm=hhmm(it);
 var when=new Date(it.date+'T'+(hm||'23:59')+':00'),past=when<n,rel=dd===0?'오늘':dd===1?'내일':dd===-1?'어제':null;
 return{dd:dd,hm:hm,past:past,rel:rel,dlabel:past?'지남':(dd===0?'D-day':'D-'+dd),color:past?'gry':(dd<=1?'red':dd<=3?'yel':'gry')}}
function el(tag,cls,txt,tid){var e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;if(tid)e.setAttribute('data-testid',tid);return e}
var SLT=null;
function dated(){var box=document.getElementById('dated');if(!box)return;box.textContent='';
 var ds=IT.filter(function(it){return /^\d{4}-\d\d-\d\d$/.test(it.date||'')}).map(function(it){return{it:it,i:datedInfo(it)}});
 var nd=IT.length-ds.length;
 ds.sort(function(a,b){return(a.it.date+(a.i.hm||'99')).localeCompare(b.it.date+(b.i.hm||'99'))});
 var up=ds.filter(function(x){return !x.i.past&&!x.it.done}),past=ds.filter(function(x){return x.i.past||x.it.done});
 if(!ds.length){box.appendChild(el('p','small','날짜가 명시된 일정이 없습니다. 마감·날짜는 추측해서 만들지 않습니다.','dated-empty'));return}
 var card=el('div','card320',null,'dated-card');card.appendChild(el('b',null,'다가오는 일정 '+up.length+'건'));
 up.forEach(function(x){var r=el('div','row',null,'dc-'+x.it.id);r.appendChild(el('span','badge b-'+x.i.color,x.i.dlabel,'dd-'+x.it.id));
  r.appendChild(el('span',null,(x.i.rel?x.i.rel+' ':x.it.date+' ')+(x.i.hm||'시각 미정')));r.appendChild(el('span',null,x.it.title));card.appendChild(r)});
 if(!up.length)card.appendChild(el('div','small','다가오는 일정 없음'));box.appendChild(card);
 var sw=el('div','wrap',null,'dated-slider'),tr=el('div','track');sw.appendChild(tr);var dots=el('div','dots');
 up.forEach(function(x,k){var s=el('div','s '+x.i.color,null,'slide-'+x.it.id);s.appendChild(el('div','small',x.i.dlabel+' · '+(x.i.rel||x.it.date)));s.appendChild(el('div','big',x.it.title));s.appendChild(el('div',null,(x.i.hm||'시각 미정')+' · '+(x.it.label||'')));tr.appendChild(s);dots.appendChild(el('i',k?'':'on'))});
 if(up.length){box.appendChild(sw);box.appendChild(dots);var k=0;if(SLT)clearInterval(SLT);if(up.length>1)SLT=setInterval(function(){if(!document.body.contains(tr)){clearInterval(SLT);return}k=(k+1)%up.length;tr.style.transform='translateX(-'+(k*100)+'%)';[].forEach.call(dots.children,function(d,j){d.className=j===k?'on':''})},3000)}
 var pd=el('details',null,null,'dated-past');pd.appendChild(el('summary',null,'지난/완료 일정 '+past.length+'건'));past.forEach(function(x){pd.appendChild(el('div','small',x.it.date+' '+(x.i.hm||'')+' '+x.it.title+(x.it.done?' (완료)':' (지남)'),'past-'+x.it.id))});box.appendChild(pd);
 box.appendChild(el('p','small','날짜 없는 항목 '+nd+'건은 위 카드·D-day에 넣지 않았습니다(요일 반복 계획/날짜 미정).','dated-nodate'))}
