/* 통합 공부판 v2 (2026-10-15 노트북)
   - 데이터: /api/meta (config.json + 원본 공부판에서 바로 읽음), /api/extras (추가자료·링크·메모)
   - 과목 공부판은 원본 html 을 iframe src 로 연다 (같은 origin → 저장 키·필기 그대로)
   - 고칠 곳: 과목·경로·시험·링크 = config.json / 화면 = index.html·app.css / 동작 = 이 파일 */
(function(){
'use strict';
const $ = id => document.getElementById(id);
const LS = { get(k){ try { return localStorage.getItem(k); } catch(e){ return null; } }, set(k,v){ try { localStorage.setItem(k,v); } catch(e){} }, del(k){ try { localStorage.removeItem(k); } catch(e){} } };
const J = (k,d) => { try { const v = JSON.parse(LS.get(k) || 'null'); return v == null ? d : v; } catch(e){ return d; } };
const esc = s => String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const pad = n => String(n).padStart(2,'0');
const hms = ms => { ms = Math.max(0, ms); const s = Math.floor(ms/1000); return Math.floor(s/3600) + ':' + pad(Math.floor(s/60)%60) + ':' + pad(s%60); };
const fmtDT = t => { const d = new Date(t); return (d.getMonth()+1) + '/' + d.getDate() + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes()); };
const pct = (a,n) => n ? Math.round(a/n*100) + '%' : '-';
const kstDay = t => Math.floor((t + 9*3600e3)/864e5);
const enc = u => encodeURI(u);
const kb = n => n > 1048576 ? (n/1048576).toFixed(1) + 'MB' : Math.max(1, Math.round(n/1024)) + 'KB';
const ext = u => (String(u).split('?')[0].split('.').pop() || '').toLowerCase();
function toast(t, ms){ const el = $('toast'); el.textContent = t; el.classList.add('on'); clearTimeout(toast._t); toast._t = setTimeout(() => el.classList.remove('on'), ms || 2500); }
// 서버(server.py/드라이브 워커)가 있으면 서버를, 없으면(GitHub Pages 같은 정적 호스팅) meta.json 으로 동작
async function api(path, opt){
  try { const r = await fetch(path, Object.assign({ cache: 'no-store' }, opt || {})); if (r.ok && (r.headers.get('content-type') || '').includes('json')) return r.json(); throw new Error(path + ' ' + r.status); }
  catch (e) {
    if (/^\/api\/meta/.test(path)) return Object.assign(await (await fetch('meta.json', { cache: 'no-store' })).json(), { staticSnapshot: true });
    if (/^\/api\/extras/.test(path)) return { files: {}, links: [], memos: {} };
    if (!opt || !opt.method || opt.method === 'GET') return {};
    toast('서버에 저장하지 못했습니다. 이 공부판은 예시 화면입니다.'); throw e;
  }
}

let CFG = null, META = {}, ORDER = [], CARDS = {}, QUIZ = [], PLAN = [], MT = null, EXTRAS = { files: {}, links: [], memos: {} };
const SV = 'kw26v2:';

// ---------- 시험 D-day ----------
function exams(m){ return (m.exams || []).map(e => Object.assign({}, e, { s: Date.parse(e.start), e2: Date.parse(e.end) })); }
function nextExam(m){ const now = Date.now(); return exams(m).filter(e => e.e2 > now).sort((a,b) => a.s - b.s)[0] || null; }
function dd(m, long){
  const now = Date.now(), ex = exams(m);
  if (!ex.length) return { txt: long ? (m.note || '시험 일정 없음') : '일정 없음', cls: 'none' };
  const e = nextExam(m);
  if (!e) return { txt: '시험 끝', cls: 'over' };
  const tg = e.tag ? e.tag + ' ' : '';
  if (now >= e.s) return { txt: tg + '시험 중 · 종료까지 ' + hms(e.e2 - now), cls: 'live' };
  const dn = kstDay(e.s) - kstDay(now);
  if (dn >= 1) return { txt: 'D-' + dn + (long ? ' · ' + tg + e.label + ' · ' + e.place : ''), cls: dn <= 2 ? 'soon' : '' };
  return { txt: '오늘 ' + tg + '시작까지 ' + hms(e.s - now) + (long ? ' · ' + e.place : ''), cls: 'today' };
}

// ---------- 필기 있는지 ----------
const blankLen = {};
const pngDim = url => { try { const i = url.indexOf(','); const b = atob(url.slice(i+1, i+45)); const u = j => b.charCodeAt(j); return [(u(16)<<24|u(17)<<16|u(18)<<8|u(19))>>>0, (u(20)<<24|u(21)<<16|u(22)<<8|u(23))>>>0]; } catch(e){ return null; } };
const blankOf = (w,h) => { const k = w+'x'+h; if (blankLen[k]) return blankLen[k]; let n = 4000; try { if (w>0 && h>0 && w*h < 2.5e7) { const c = document.createElement('canvas'); c.width = w; c.height = h; const a = c.toDataURL('image/png').length; const g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0,0,w,h); n = Math.max(a, c.toDataURL('image/png').length); } } catch(e){} return blankLen[k] = n; };
function hasInk(prefix, id){ try { const raw = LS.get(prefix + id); if (!raw) return false; const w = JSON.parse(raw); if (w && w.memo && String(w.memo).trim()) return true; if (w && w.img && w.img.length > 200) { const d = pngDim(w.img); const b = d ? blankOf(d[0], d[1]) : 4000; return w.img.length > b*1.08 + 1200; } } catch(e){} return false; }

// ---------- 해커톤 문항 (원본 html 의 데이터 스크립트를 읽음) ----------
let HK = { A: [], B: [], ids: {}, ok: false };
async function loadHack(){
  const m = META.hack; if (!m) return;
  try {
    const doc = await (await fetch(enc(m.file), { cache: 'no-store' })).text();
    const mm = doc.match(/<script>\s*(var A=\[\],B=\[\];[\s\S]*?)<\/script>/);
    const r = (new Function(mm[1] + '\n;return [A,B];'))();
    HK = { A: r[0], B: r[1], ids: {}, ok: true };
    HK.A.forEach((x,i) => HK.ids['A'+(i+1)] = String(x[1] || ''));
    HK.B.forEach((x,i) => HK.ids['B'+(i+1)] = String(x[2] || ''));
  } catch(e){ console.warn('hack parse', e); }
}

// ---------- 과목별 진도 ----------
function stat(k){
  const m = META[k];
  if (m.kind === 'board') {
    const marks = J(m.subj + '_mock:marks', {});
    const list = (CARDS[k] || []).filter(c => !c[2]);
    let tried = 0, ok = 0, x = 0, u = 0;
    list.forEach(c => { const mk = marks[c[0]]; if (mk) { tried++; if (mk.s === 'o') ok++; else if (mk.s === 'x') x++; else if (mk.s === 'u') u++; } else if (hasInk(m.workPrefix, c[0])) tried++; });
    const hist = J(m.subj + '_mock:history', []); const last = hist[hist.length-1];
    const act = J(m.subj + '_mock:active', null);
    return { total: list.length, tried, ok, x, u, mock: last ? pct(last.o, last.n) + ' (' + last.o + '/' + last.n + ') · ' + fmtDT(last.at) : '', nmock: hist.length, active: act && act.kind };
  }
  if (m.kind === 'hack') {
    const st = J('skhx1:stats', {}); const w = J('skhx1:wrong', {});
    const ids = Object.keys(HK.ids); let tried = 0, ok = 0;
    ids.forEach(id => { const s = st[id]; if (s) { tried++; if (s.last === 1) ok++; } });
    const mocks = J('skhx1:mocks', []); const last = mocks[mocks.length-1];
    return { total: ids.length, tried, ok, x: Object.keys(w).filter(id => HK.ids[id] != null).length, u: null, mock: last ? last.set + '형 ' + last.ok + '/' + last.mc + ' (' + pct(last.ok, last.mc) + ') · ' + last.d : '', nmock: mocks.length };
  }
  if (m.kind === 'quiz') {
    const leit = J('kw26m:leit', {}); const w = J('kw26m:wrong', {}); let tried = 0, ok = 0;
    QUIZ.forEach(q => { const s = leit[q[0]]; if (s) { tried++; if (s.b >= 2) ok++; } });
    return { total: QUIZ.length, tried, ok, x: Object.keys(w).length, u: null, mock: '', nmock: 0 };
  }
  return null;
}

// ---------- 라우팅 ----------
let view = 'dash', cur = null, subTab = 'board';
const frames = {}, loaded = {}, essayIdx = {};
function setHash(){ const h = cur ? 'v=subj&k=' + cur + (subTab !== 'board' ? '&t=' + subTab : '') : 'v=' + view; if (location.hash.slice(1) !== h) history.replaceState(null, '', '#' + h); }
function markNav(){
  document.querySelectorAll('#sNav a').forEach(a => a.classList.toggle('on', cur ? a.dataset.k === cur : a.dataset.v === view));
}
function show(v){
  if (cur) { saveFrame(cur); cur = null; }
  view = v; LS.set(SV + 'view', v);
  document.body.classList.remove('insub', 'st-board', 'st-docs', 'st-memo');
  Object.keys(frames).forEach(x => frames[x].classList.remove('on'));
  $('loading').classList.remove('on');
  document.querySelectorAll('section.view').forEach(s => s.classList.toggle('on', s.id === 'v-' + v));
  markNav(); setHash(); render();
}
function render(){
  if (cur) return;
  if (view === 'dash') renderDash();
  else if (view === 'today') renderToday();
  else if (view === 'plan') renderPlan();
  else if (view === 'wrong') renderWrong();
  else if (view === 'extras') renderExtras();
  else if (view === 'memo') renderMemo('common', $('v-memo'));
  else if (view === 'settings') renderSettings();
  renderBadges();
}

// ---------- 사이드바 ----------
function renderSide(){
  $('sTitle').textContent = CFG.title || '통합 공부판'; document.title = CFG.title || '통합 공부판';
  $('sSubj').innerHTML = ORDER.map(k => { const m = META[k]; return '<a class="sub" data-k="' + k + '" style="--c:' + m.color + '"><i>' + esc(m.icon || m.short.slice(0,2)) + '</i><span>' + esc(m.name) + '</span><em data-sdd="' + k + '"></em></a>'; }).join('');
  document.querySelectorAll('#sNav a[data-v]').forEach(a => a.onclick = () => show(a.dataset.v));
  document.querySelectorAll('#sNav a[data-k]').forEach(a => a.onclick = () => openSubject(a.dataset.k));
  renderBadges();
}
function renderBadges(){
  ORDER.forEach(k => { const el = document.querySelector('[data-sdd="' + k + '"]'); if (!el) return; const d = dd(META[k], false); el.textContent = d.cls === 'none' ? '' : d.txt.replace(/시작까지.*/, '오늘'); el.className = (d.cls === 'soon' || d.cls === 'today' || d.cls === 'live') ? 'hot' : ''; });
  try { const n = wrongItems().length; $('nWrong').textContent = n || ''; } catch(e){}
  const ne = Object.values(EXTRAS.files || {}).reduce((a,b) => a + b.length, 0) + (EXTRAS.links || []).length; $('nExtra').textContent = ne || '';
  const p = PLAN.find(x => x.date === todayStr()); if (p) { const done = (J('kw26m:chk_v2', {})[p.date] || []).length; $('nToday').textContent = done + '/' + p.tasks.length; }
  const nx = ORDER.map(k => ({ k, e: nextExam(META[k]) })).filter(x => x.e).sort((a,b) => a.e.s - b.e.s)[0];
  if (nx) { const d = dd(META[nx.k], false); $('sNext').innerHTML = '다음 시험 <b>' + esc(META[nx.k].name) + (nx.e.tag ? ' ' + nx.e.tag : '') + '</b><br><span class="big">' + esc(d.txt) + '</span> · ' + esc(nx.e.label); }
}
$('sToggle').onclick = () => { document.body.classList.toggle('mini'); LS.set(SV + 'mini', document.body.classList.contains('mini') ? '1' : ''); };
if (LS.get(SV + 'mini')) document.body.classList.add('mini');
addEventListener('keydown', e => { if (e.key === '\\' && !/INPUT|TEXTAREA/.test((document.activeElement || {}).tagName || '') && !(document.activeElement || {}).isContentEditable) $('sToggle').click(); });

// ---------- 과목 화면 ----------
function frameWin(k){ try { return frames[k] && frames[k].contentWindow; } catch(e){ return null; } }
function saveFrame(k){ const w = frameWin(k); if (!w) return; try { if (w.__dgSaveWork && w.__dgCur) w.__dgSaveWork(w.__dgCur); } catch(e){} try { w.dispatchEvent(new w.Event('beforeunload')); } catch(e){} }
function jump(k, id){ const w = frameWin(k); try { const set = w.__dgSet || []; const i = set.findIndex(c => (c.id || ('q' + c.q)) === id) + 1; if (i > 0 && w.__dgShow) w.__dgShow(i); } catch(e){} }
function frameSrc(k){ const m = META[k]; if (m.kind === 'essay') { const i = essayIdx[k] || 0; return m.docs[i] ? m.docs[i].url : ''; } return m.file; }
function openSubject(k, cardId, tab){
  const m = META[k]; if (!m) return;
  if (cur && cur !== k) saveFrame(cur);
  cur = k; LS.set(SV + 'last', k); LS.set('kw26u:last', k);
  document.querySelectorAll('section.view').forEach(s => s.classList.remove('on'));
  document.body.classList.add('insub');
  $('subBar').style.setProperty('--c', m.color);
  $('bName').textContent = m.name;
  $('bNDocs').textContent = '(' + subjDocCount(k) + ')';
  const sel = $('bDocsSel');
  sel.innerHTML = m.kind === 'essay' ? m.docs.map((x,i) => '<button data-i="' + i + '"' + (i === (essayIdx[k] || 0) ? ' class="on"' : '') + '>' + esc(x.label) + '</button>').join('') : '';
  sel.querySelectorAll('button').forEach(b => b.onclick = () => { essayIdx[k] = +b.dataset.i; frames[k].src = enc(frameSrc(k)); $('bOrig').href = enc(frameSrc(k)); sel.querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b)); });
  $('bOrig').href = enc(frameSrc(k));
  if (m.kind === 'board' && cardId) LS.set(m.pre + '-last-q', cardId);
  let fr = frames[k];
  if (!fr) {
    fr = document.createElement('iframe'); fr.title = m.name;
    fr.setAttribute('allow', 'clipboard-read; clipboard-write; fullscreen; autoplay');
    frames[k] = fr; loaded[k] = false;
    fr.addEventListener('load', () => { loaded[k] = true; if (cur === k) $('loading').classList.remove('on'); if (k === 'quizz') {}
      // 1015: 숨은 상태로 처음 로드되면 문제판이 비는 경우가 있어 1번 자동 새로고침
      if (m.kind === 'board' && !fr.__healed) setTimeout(() => { try { const d = fr.contentDocument; if (d && !d.querySelector('select')) { fr.__healed = true; loaded[k] = false; fr.src = enc(frameSrc(k)) + (frameSrc(k).indexOf('?') < 0 ? '?' : '&') + 't=' + Date.now(); } } catch(e){} }, 1500); });
    Object.keys(frames).forEach(x => frames[x].classList.toggle('on', x === k));
    $('loading').classList.add('on');
    fr.src = enc(frameSrc(k));
    $('frames').appendChild(fr);
  } else if (cardId && m.kind === 'board') jump(k, cardId);
  Object.keys(frames).forEach(x => frames[x].classList.toggle('on', x === k));
  setSubTab(tab || (cardId ? 'board' : (subTab || 'board')));
  markNav(); tickBar(); renderBadges();
}
function setSubTab(t){
  subTab = t;
  document.body.classList.remove('st-board', 'st-docs', 'st-memo'); document.body.classList.add('st-' + t);
  document.querySelectorAll('#bTabs button').forEach(b => b.classList.toggle('on', b.dataset.st === t));
  $('bDocsSel').style.display = t === 'board' ? '' : 'none';
  if (t === 'docs') renderSubjDocs(cur);
  if (t === 'memo') renderMemo(cur, $('sv-memo'));
  if (t === 'board') { try { frames[cur].focus(); } catch(e){} if (!loaded[cur]) $('loading').classList.add('on'); } else $('loading').classList.remove('on');
  setHash();
}
document.querySelectorAll('#bTabs button').forEach(b => b.onclick = () => setSubTab(b.dataset.st));
$('bReload').onclick = () => { if (!cur) return; saveFrame(cur); loaded[cur] = false; $('loading').classList.add('on'); frames[cur].src = enc(frameSrc(cur)) + (frameSrc(cur).indexOf('?') < 0 ? '?' : '&') + 't=' + Date.now(); setSubTab('board'); };
function tickBar(){ if (!cur) return; const d = dd(META[cur], true); const el = $('bDd'); el.textContent = d.txt; el.className = 'dd ' + d.cls; }
addEventListener('pagehide', () => { Object.keys(frames).forEach(saveFrame); backup(true); });
(function(){ const a = document.createElement('div'); a.className = 'subview'; a.id = 'sv-docs'; const b = document.createElement('div'); b.className = 'subview'; b.id = 'sv-memo'; $('main').insertBefore(b, $('loading')); $('main').insertBefore(a, b); })();

// ---------- 자료 (링크 + 추가자료 파일) ----------
function subjDocCount(k){ const m = META[k] || {}; return (m.links || []).length + (m.docs || []).length + ((EXTRAS.files || {})[k] || []).length + (EXTRAS.links || []).filter(l => l.sub === k).length; }
const TY = u => { const e = ext(u); return e === 'md' ? 'MD' : e === 'pdf' ? 'PDF' : /^(wav|m4a|mp3|ogg)$/.test(e) ? '소리' : /^(mp4|webm|mov)$/.test(e) ? '영상' : /^(png|jpe?g|gif|webp)$/.test(e) ? '그림' : /^https?:/.test(u) ? '웹' : e === 'html' || e === 'htm' ? 'HTML' : e.toUpperCase() || '파일'; };
function linkRow(l, del){
  return '<div class="fi"><span class="ty">' + TY(l.url) + '</span><span class="fn" data-url="' + esc(l.url) + '" data-t="' + esc(l.label) + '">' + esc(l.label) + '</span>' + (l.note ? '<span class="fm">' + esc(l.note) + '</span>' : '') + (l.size ? '<span class="fm">' + kb(l.size) + ' · ' + fmtDT(l.mtime*1000) + '</span>' : '') + '<a class="btn sm alt" target="_blank" href="' + esc(/^https?:/.test(l.url) ? l.url : enc(l.url)) + '">새 탭</a>' + (del ? '<button class="btn sm alt" data-del="' + esc(del) + '">지우기</button>' : '') + '</div>';
}
function bindRows(root, back){
  root.querySelectorAll('.fn[data-url]').forEach(el => el.onclick = () => openViewer(el.dataset.url, el.dataset.t, back));
  root.querySelectorAll('[data-del]').forEach(b => b.onclick = async () => {
    const d = JSON.parse(b.dataset.del);
    if (!confirm('지울까? (data\\_지운자료 로 옮겨져서 되살릴 수 있음)')) return;
    try {
      if (d.type === 'file') await api('/api/delete?sub=' + encodeURIComponent(d.sub) + '&name=' + encodeURIComponent(d.name), { method: 'POST' });
      else { EXTRAS.links = EXTRAS.links.filter(l => l.id !== d.id); await api('/api/links', { method: 'POST', body: JSON.stringify(EXTRAS.links) }); }
      await loadExtras(); toast('지웠어'); cur ? renderSubjDocs(cur) : render();
    } catch(e){ toast('실패: ' + e.message); }
  });
}
function uploadUI(sub, withSel){
  return '<div class="drop" data-sub="' + sub + '">여기로 파일을 끌어다 놓거나 <label class="btn sm alt" style="cursor:pointer">파일 고르기<input type="file" multiple hidden></label>' + (withSel ? ' &nbsp;과목: <select class="upsub">' + ORDER.map(k => '<option value="' + k + '">' + esc(META[k].short) + '</option>').join('') + '<option value="common">공통</option></select>' : '') + '<div class="note">사진·PDF·녹음·메모 다 된다. 저장 위치: 통합공부판\\추가자료\\' + (withSel ? '(과목)' : sub) + '\\ (구글드라이브라 집 PC에도 동기화)</div></div>' +
    '<div class="frm"><input class="lkT" placeholder="링크 이름 (예: 친구 7주차 판서)"><input class="lkU" placeholder="주소 또는 드라이브 경로 (https://... 또는 /광운대학교/...)"><input class="lkN" placeholder="메모 (선택)" style="max-width:220px"><button class="btn sm lkAdd">링크 추가</button></div>';
}
function bindUpload(root, defSub, after){
  const dz = root.querySelector('.drop'); if (!dz) return;
  const subOf = () => { const s = root.querySelector('.upsub'); return s ? s.value : defSub; };
  const send = async files => {
    for (const f of files) { toast('올리는 중: ' + f.name, 60000); try { await fetch('/api/upload?sub=' + encodeURIComponent(subOf()) + '&name=' + encodeURIComponent(f.name), { method: 'POST', body: f }); } catch(e){ toast('실패: ' + f.name); return; } }
    await loadExtras(); toast(files.length + '개 올림'); after();
  };
  dz.ondragover = e => { e.preventDefault(); dz.classList.add('over'); };
  dz.ondragleave = () => dz.classList.remove('over');
  dz.ondrop = e => { e.preventDefault(); dz.classList.remove('over'); if (e.dataTransfer.files.length) send([...e.dataTransfer.files]); };
  dz.querySelector('input[type=file]').onchange = e => send([...e.target.files]);
  root.querySelector('.lkAdd').onclick = async () => {
    const t = root.querySelector('.lkT').value.trim(), u = root.querySelector('.lkU').value.trim(), n = root.querySelector('.lkN').value.trim();
    if (!u) { toast('주소를 넣어 줘'); return; }
    let url = u; const g = u.replace(/\\/g, '/').match(/내 드라이브(\/.*)$/); if (g) url = g[1];
    EXTRAS.links.push({ id: Date.now().toString(36), sub: subOf(), label: t || url.split('/').pop(), url, note: n, at: Date.now() });
    try { await api('/api/links', { method: 'POST', body: JSON.stringify(EXTRAS.links) }); await loadExtras(); toast('링크 추가'); after(); } catch(e){ toast('실패: ' + e.message); }
  };
  root.addEventListener('paste', e => { const fs = [...(e.clipboardData || {}).files || []]; if (fs.length) { e.preventDefault(); send(fs.map((f,i) => new File([f], f.name && f.name !== 'image.png' ? f.name : '붙여넣기_' + new Date().toTimeString().slice(0,8).replace(/:/g,'') + '_' + i + '.png', { type: f.type }))); } });
}
function renderSubjDocs(k){
  const m = META[k], root = $('sv-docs');
  const files = (EXTRAS.files || {})[k] || [], links = (EXTRAS.links || []).filter(l => l.sub === k);
  let h = '<div class="vh"><h2 style="color:' + m.color + '">' + esc(m.name) + ' 자료</h2></div>';
  if (m.docs && m.docs.length) h += '<h3>공부판 문서</h3><div class="flist">' + m.docs.map(x => linkRow(x)).join('') + '</div>';
  h += '<h3>기본 자료 (config.json)</h3><div class="flist">' + ((m.links || []).map(x => linkRow(x)).join('') || '<div class="fi note">없음</div>') + '</div>';
  h += '<h3>추가자료 · 링크 (' + (files.length + links.length) + ')</h3>' + uploadUI(k, false);
  h += '<div class="flist">' + (files.map(f => linkRow({ label: f.name, url: f.url, size: f.size, mtime: f.mtime }, JSON.stringify({ type: 'file', sub: k, name: f.name }))).join('') + links.map(l => linkRow(l, JSON.stringify({ type: 'link', id: l.id }))).join('') || '<div class="fi note">아직 없음. 위에 끌어다 놓거나 Ctrl+V로 캡처를 붙여 넣으면 된다.</div>') + '</div>';
  root.innerHTML = h; bindRows(root, null); bindUpload(root, k, () => { renderSubjDocs(k); $('bNDocs').textContent = '(' + subjDocCount(k) + ')'; });
}
function renderExtras(){
  const root = $('v-extras');
  const all = ['common'].concat(ORDER);
  let h = '<div class="vh"><h2>추가자료 · 링크</h2></div><div class="note">과목을 골라 올리면 그 과목 화면의 "자료" 탭에도 같이 보인다. 캡처는 이 화면에서 Ctrl+V 로 바로 붙여 넣기.</div>' + uploadUI('common', true);
  all.forEach(k => {
    const files = (EXTRAS.files || {})[k] || [], links = (EXTRAS.links || []).filter(l => l.sub === k);
    if (!files.length && !links.length) return;
    const nm = k === 'common' ? '공통' : META[k] ? META[k].name : k;
    h += '<h3>' + esc(nm) + ' (' + (files.length + links.length) + ')</h3><div class="flist">' + files.map(f => linkRow({ label: f.name, url: f.url, size: f.size, mtime: f.mtime }, JSON.stringify({ type: 'file', sub: k, name: f.name }))).join('') + links.map(l => linkRow(l, JSON.stringify({ type: 'link', id: l.id }))).join('') + '</div>';
  });
  h += '<h3>공통 바로가기 (config.json)</h3><div class="flist">' + (CFG.commonLinks || []).map(x => linkRow(x)).join('') + '</div>';
  root.innerHTML = h; bindRows(root, 'extras'); bindUpload(root, 'common', renderExtras);
}

// ---------- 뷰어 (md·pdf·html·소리·그림) ----------
let viewerBack = null;
function mdToHtml(src){
  const lines = String(src).replace(/\r/g, '').split('\n'); let out = '', i = 0;
  const inl = s => String(s).split(/(\$[^$\n]+\$)/).map(seg => (/^\$[^$]+\$/.test(seg) && window.__tex2mml) ? window.__tex2mml(seg.slice(1, -1), false) : inl0(seg)).join(''); /* __mdMath 10/23 */
  const inl0 = s => esc(s).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>').replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<i>$2</i>').replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, '<a href="$2" target="_blank">$1</a>');
  while (i < lines.length) {
    let l = lines[i];
    if (/^```/.test(l)) { let b = []; i++; while (i < lines.length && !/^```/.test(lines[i])) b.push(lines[i++]); i++; out += '<pre>' + esc(b.join('\n')) + '</pre>'; continue; }
    if (/^\s*\|/.test(l)) { const rows = []; while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(lines[i++]); const cells = r => r.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim()); let t = '<table>'; rows.forEach((r, j) => { if (/^\s*\|?\s*:?-{2,}/.test(r)) return; const tag = j === 0 ? 'th' : 'td'; t += '<tr>' + cells(r).map(c => '<' + tag + '>' + inl(c) + '</' + tag + '>').join('') + '</tr>'; }); out += t + '</table>'; continue; }
    let m;
    if ((m = l.match(/^(#{1,6})\s+(.*)/))) { out += '<h' + m[1].length + '>' + inl(m[2]) + '</h' + m[1].length + '>'; i++; continue; }
    if (/^>\s?/.test(l)) { let b = []; while (i < lines.length && /^>\s?/.test(lines[i])) b.push(lines[i++].replace(/^>\s?/, '')); out += '<blockquote>' + b.map(inl).join('<br>') + '</blockquote>'; continue; }
    if (/^\s*([-*]|\d+\.)\s+/.test(l)) { const ol = /^\s*\d+\./.test(l); let b = []; while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) { const ind = lines[i].match(/^\s*/)[0].length; b.push('<li style="margin-left:' + (ind*8) + 'px">' + inl(lines[i].replace(/^\s*([-*]|\d+\.)\s+/, '').replace(/^\[ \]\s*/, '☐ ').replace(/^\[x\]\s*/i, '☑ ')) + '</li>'); i++; } out += (ol ? '<ol>' : '<ul>') + b.join('') + (ol ? '</ol>' : '</ul>'); continue; }
    if (/^---+\s*$/.test(l)) { out += '<hr>'; i++; continue; }
    if (!l.trim()) { i++; continue; }
    let b = []; while (i < lines.length && lines[i].trim() && !/^(#|>|```|\s*\||\s*([-*]|\d+\.)\s)/.test(lines[i])) b.push(lines[i++]); out += '<p>' + b.map(inl).join('<br>') + '</p>';
  }
  return out;
}
async function openViewer(url, title, back){
  if (/^https?:/.test(url) && !/^https?:\/\/(localhost|127\.0\.0\.1)/.test(url)) { window.open(url, '_blank'); return; }
  viewerBack = cur ? { k: cur, t: subTab } : (back || view);
  if (cur) { saveFrame(cur); }
  const k0 = cur; cur = null;
  document.body.classList.remove('insub', 'st-board', 'st-docs', 'st-memo');
  Object.keys(frames).forEach(x => frames[x].classList.remove('on'));
  document.querySelectorAll('section.view').forEach(s => s.classList.toggle('on', s.id === 'v-viewer'));
  $('vwTitle').textContent = title || url.split('/').pop(); $('vwOpen').href = enc(url);
  const e = ext(url), body = $('vwBody');
  if (e === 'md' || e === 'txt' || e === 'json' || e === 'log') {
    body.innerHTML = '<div class="md">불러오는 중...</div>';
    try { const t = await (await fetch(enc(url), { cache: 'no-store' })).text(); body.innerHTML = '<div class="md">' + (e === 'md' ? mdToHtml(t) : '<pre>' + esc(t) + '</pre>') + '</div>'; } catch(err){ body.innerHTML = '<div class="md">못 읽음: ' + esc(err.message) + '</div>'; }
  } else if (/^(wav|m4a|mp3|ogg)$/.test(e)) body.innerHTML = '<div class="box"><audio controls autoplay style="width:100%" src="' + esc(enc(url)) + '"></audio><div class="note">속도: <button class="btn sm alt" data-r="1">1x</button> <button class="btn sm alt" data-r="1.25">1.25x</button> <button class="btn sm alt" data-r="1.5">1.5x</button> <button class="btn sm alt" data-r="2">2x</button></div></div>';
  else if (/^(mp4|webm|mov)$/.test(e)) body.innerHTML = '<video controls style="width:100%;max-height:80vh;background:#000;border-radius:10px" src="' + esc(enc(url)) + '"></video>';
  else if (/^(png|jpe?g|gif|webp)$/.test(e)) body.innerHTML = '<div style="overflow:auto"><img style="max-width:100%;border-radius:10px;background:#fff" src="' + esc(enc(url)) + '"></div>';
  else body.innerHTML = '<iframe src="' + esc(enc(url)) + '"></iframe>';
  body.querySelectorAll('[data-r]').forEach(b => b.onclick = () => { body.querySelector('audio').playbackRate = +b.dataset.r; });
  markNav();
}
$('vwBack').onclick = () => { const b = viewerBack; if (b && b.k) openSubject(b.k, null, b.t); else show(b || 'dash'); };

// ---------- 메모 ----------
let memoTimer = null;
function renderMemo(sub, root){
  const nm = sub === 'common' ? '공통 메모장' : META[sub].name + ' 메모';
  const txt = (EXTRAS.memos || {})[sub] || '';
  root.innerHTML = '<div class="vh"><h2>' + esc(nm) + '</h2><span class="note" id="mSt">자동 저장 (통합공부판\\data\\memo_' + sub + '.md)</span></div><div class="frm"><button class="btn sm alt" id="mStamp">시각 찍기</button><button class="btn sm alt" id="mView">읽기 모드</button></div><textarea class="memo" id="mTxt" placeholder="교수님 발언, 헷갈린 것, 질문할 것... 마크다운(# 제목, - 목록, **굵게**) 써도 된다.">' + esc(txt) + '</textarea>';
  const ta = root.querySelector('#mTxt'), st = root.querySelector('#mSt');
  const save = async () => { try { await fetch('/api/memo?sub=' + sub, { method: 'POST', body: ta.value }); EXTRAS.memos[sub] = ta.value; st.textContent = '저장됨 ' + new Date().toTimeString().slice(0,8); } catch(e){ st.textContent = '저장 실패 (서버 꺼짐?)'; } };
  ta.oninput = () => { st.textContent = '입력 중...'; clearTimeout(memoTimer); memoTimer = setTimeout(save, 800); };
  root.querySelector('#mStamp').onclick = () => { const d = new Date(); const s = '\n[' + (d.getMonth()+1) + '/' + d.getDate() + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + '] '; const p = ta.selectionStart; ta.value = ta.value.slice(0,p) + s + ta.value.slice(p); ta.focus(); ta.selectionStart = ta.selectionEnd = p + s.length; ta.oninput(); };
  root.querySelector('#mView').onclick = () => { const b = root.querySelector('#mView'); if (ta.style.display === 'none') { ta.style.display = ''; root.querySelector('.md') && root.querySelector('.md').remove(); b.textContent = '읽기 모드'; } else { ta.style.display = 'none'; const d = document.createElement('div'); d.className = 'md'; d.innerHTML = mdToHtml(ta.value); root.appendChild(d); b.textContent = '편집 모드'; } };
}

// ---------- 대시보드 ----------
function sortKey(k){ const m = META[k]; const e = nextExam(m); if (e) return [0, e.s]; if (!(m.exams || []).length) return [1, ORDER.indexOf(k)]; return [2, ORDER.indexOf(k)]; }
function nowBlock(){
  const p = PLAN.find(x => x.date === todayStr()); if (!p) return null;
  const nm = nowM(); const ts = p.tasks.map((x,j) => Object.assign({ j }, x)).sort((a,b) => hm(a.start) - hm(b.start));
  return { now: ts.find(x => nm >= hm(x.start) && nm < hm(x.end)), next: ts.find(x => hm(x.start) > nm), p };
}
function renderDash(){
  const ks = ORDER.slice().sort((a,b) => { const x = sortKey(a), y = sortKey(b); return x[0] - y[0] || x[1] - y[1]; });
  const near = ks.find(k => sortKey(k)[0] === 0);
  const nb = nowBlock(); const last = LS.get(SV + 'last');
  let h = '<div class="vh"><h2>대시보드</h2><span class="note">' + esc(MT.built) + ' 기준 · 원본 공부판이 바뀌면 새로고침(F5)만 하면 된다</span></div>';
  h += '<div class="nowcard"><div style="flex:1;min-width:240px">';
  if (nb && nb.now) h += '지금 블록 <b>' + esc(nb.now.start + '~' + nb.now.end + ' ' + nb.now.subject) + '</b><br>' + esc(nb.now.task).slice(0, 160);
  else if (nb && nb.next) h += '지금은 쉬는 시간 · 다음 <b>' + esc(nb.next.start + ' ' + nb.next.subject) + '</b><br>' + esc(nb.next.task).slice(0, 160);
  else h += '오늘 계획 블록 없음';
  h += '</div>' + (last && META[last] ? '<button class="btn" id="dResume">이어하기: ' + esc(META[last].name) + '</button>' : '') + '<button class="btn" id="dGoToday">오늘 할 일</button></div>';
  h += '<div class="grid">' + ks.map(k => {
    const m = META[k], d = dd(m, false), s = stat(k);
    let c = '<div class="sc' + (k === near ? ' near' : '') + '" data-k="' + k + '" style="--c:' + m.color + '"><div class="hd"><span class="nm">' + esc(m.name) + '</span><span class="dd ' + d.cls + '" data-dd="' + k + '">' + esc(d.txt) + '</span></div>';
    c += '<div class="ex">' + (exams(m).length ? exams(m).map(e => esc(e.label + ' · ' + e.place)).join('<br>') : esc(m.note || '')) + '</div>';
    if (s) {
      c += '<div class="bar"><i style="width:' + (s.total ? s.tried/s.total*100 : 0) + '%"></i><b style="width:' + (s.total ? s.ok/s.total*100 : 0) + '%"></b></div>';
      c += '<div class="st2">풀어 봄 <b>' + s.tried + '</b>/' + s.total + ' (' + pct(s.tried, s.total) + ') · 맞음 <b>' + s.ok + '</b>' + (s.x ? ' · 틀림 <span class="x">' + s.x + '</span>' : '') + (s.u ? ' · 모름 <span class="u">' + s.u + '</span>' : '') + '</div>';
      if (m.kind !== 'quiz') c += '<div class="st2 note">최근 실전 모의 ' + (s.mock ? esc(s.mock) + (s.nmock > 1 ? ' (총 ' + s.nmock + '회)' : '') : '없음') + (s.active === 'mock' ? ' · <b class="x">실전 진행 중</b>' : '') + '</div>';
    } else c += '<div class="st2 note">문서 ' + (m.docs || []).length + '개: ' + (m.docs || []).map(x => esc(x.label)).join(', ') + '</div>';
    c += '<div class="st2 note">자료 ' + subjDocCount(k) + '개</div></div>';
    return c;
  }).join('') + '</div>';
  h += '<h3>바로가기</h3><div class="ql">' + (CFG.commonLinks || []).map(l => '<a href="#" data-url="' + esc(l.url) + '" data-t="' + esc(l.label) + '">' + esc(l.label) + '</a>').join('') + '</div>';
  if (MT.errors && MT.errors.length) h += '<div class="box" style="color:#b91c1c">읽기 오류: ' + esc(MT.errors.join(' / ')) + '</div>';
  const root = $('v-dash'); root.innerHTML = h;
  root.querySelectorAll('.sc').forEach(el => el.onclick = () => openSubject(el.dataset.k));
  root.querySelectorAll('.ql a').forEach(a => a.onclick = e => { e.preventDefault(); openViewer(a.dataset.url, a.dataset.t, 'dash'); });
  const r = root.querySelector('#dResume'); if (r) r.onclick = () => openSubject(last);
  root.querySelector('#dGoToday').onclick = () => show('today');
}

// ---------- 오늘 할 일 ----------
const SUBJ_OF = s => /디지털/.test(s) ? 'dg' : /물리/.test(s) ? 'ph' : /법/.test(s) ? 'lk' : /공업수학|공수/.test(s) ? 'gs' : /인간존재|에세이/.test(s) ? 'essay' : /해커톤/.test(s) ? 'hack' : null;
function fileTarget(f){
  f = String(f || '');
  for (const k of ORDER) { const m = META[k]; if (m.file && f.indexOf(m.file.split('/').pop()) >= 0) return { k }; if (m.docs) { const i = m.docs.findIndex(d => f.indexOf(d.url.split('/').pop()) >= 0); if (i >= 0) return { k, i }; } }
  return null;
}
const hm = s => { const p = String(s || '0:0').split(':'); return (+p[0])*60 + (+p[1]); };
const nowM = () => { const d = new Date(); return d.getHours()*60 + d.getMinutes(); };
const todayStr = () => { const d = new Date(); return d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate()); };
const pickDay = () => { if (!PLAN.length) return todayStr(); const t = todayStr(); if (t < PLAN[0].date) return PLAN[0].date; if (t > PLAN[PLAN.length-1].date) return PLAN[PLAN.length-1].date; return t; };
const isStudy = x => x.kind !== '듣기' && x.kind !== '루틴' && x.kind !== '시험';
let day = null, scrolled = false;
function renderToday(){
  if (!PLAN.length) { $('dInfo').textContent = '계획 파일(study_plan.json)을 못 읽음'; return; }
  if (!day) day = pickDay();
  $('dPick').value = day; $('dPick').min = PLAN[0].date; $('dPick').max = PLAN[PLAN.length-1].date;
  const p = PLAN.find(x => x.date === day);
  if (!p) { $('dInfo').textContent = '계획표에 없는 날짜'; $('dList').innerHTML = ''; return; }
  const chk = J('kw26m:chk_v2', {}); const done = chk[day] || [];
  const isToday = day === todayStr(), nm = nowM();
  const dw = '일월화수목금토'[new Date(day + 'T00:00:00').getDay()];
  $('dInfo').innerHTML = '<b>' + day.slice(5).replace('-','/') + '(' + dw + ') · ' + esc(p.shift || '') + '</b>' + (isToday ? ' <span class="nowtag">오늘</span>' : '') + '<br>' + esc(p.note || '');
  const order = p.tasks.map((x,j) => j).sort((a,b) => hm(p.tasks[a].start) - hm(p.tasks[b].start));
  let nowTxt = '', nextTxt = '', tot = 0, dn = 0;
  $('dList').innerHTML = order.map(j => {
    const x = p.tasks[j], on = done.indexOf(j) >= 0, sk = SUBJ_OF(x.subject || ''), col = sk && META[sk] ? META[sk].color : '#94a3b8';
    if (isStudy(x)) { tot += x.minutes || 0; if (on) dn += x.minutes || 0; }
    let cls = 'task' + (on ? ' done' : '');
    if (isToday) { const s = hm(x.start), e = hm(x.end); if (nm >= s && nm < e) { cls += ' now'; nowTxt += (nowTxt ? ' / ' : '') + x.start + '~' + x.end + ' ' + x.subject; } else if (nm >= e) cls += ' past'; else if (!nextTxt) nextTxt = x.start + ' ' + x.subject; }
    const ft = fileTarget(x.file) || (sk && META[sk] ? { k: sk } : null);
    return '<label class="' + cls + '" style="--c:' + col + '"><input type="checkbox" data-j="' + j + '"' + (on ? ' checked' : '') + '><span class="tm">' + esc(x.start) + '~' + esc(x.end) + '</span><span class="tx"><span class="pill" style="--c:' + col + '">' + esc(x.subject || '') + '</span><span class="kd">' + esc(x.kind || '') + '</span>' + esc(x.task) + (x.goal ? '<span class="goal">목표: ' + esc(x.goal) + '</span>' : '') + '<span class="fp">' + esc(x.file || '') + (ft ? ' <button type="button" class="btn sm" data-open="' + ft.k + '" data-i="' + (ft.i || 0) + '">' + esc(META[ft.k].short) + ' 열기</button>' : '') + '</span></span><span class="mn">' + (x.minutes || 0) + '분</span></label>';
  }).join('');
  $('dNow').innerHTML = isToday ? '<b>지금 ' + pad(Math.floor(nm/60)) + ':' + pad(nm%60) + '</b> · ' + (nowTxt ? '진행 중: <b>' + esc(nowTxt) + '</b>' : '진행 중 블록 없음(식사·휴식·이동)') + (nextTxt ? ' · 다음: ' + esc(nextTxt) : '') : '';
  $('dPct').textContent = pct(dn, tot); $('dMin').textContent = '(' + dn + ' / ' + tot + '분, 듣기·루틴·시험 제외)';
  $('dList').querySelectorAll('input').forEach(c => c.onchange = () => { const all = J('kw26m:chk_v2', {}); const j = +c.dataset.j; const a = (all[day] || []).filter(v => v !== j); if (c.checked) a.push(j); all[day] = a; LS.set('kw26m:chk_v2', JSON.stringify(all)); renderToday(); renderBadges(); });
  $('dList').querySelectorAll('button[data-open]').forEach(b => b.onclick = e => { e.preventDefault(); e.stopPropagation(); if (META[b.dataset.open].kind === 'essay') essayIdx[b.dataset.open] = +b.dataset.i; openSubject(b.dataset.open, null, 'board'); });
  const nowEl = $('dList').querySelector('.task.now'); if (nowEl && !scrolled) { scrolled = true; try { nowEl.scrollIntoView({ block: 'center' }); } catch(e){} }
}
const shiftDay = n => { const i = PLAN.findIndex(x => x.date === day); const j = Math.min(PLAN.length-1, Math.max(0, i + n)); day = PLAN[j].date; renderToday(); };
$('dPrev').onclick = () => shiftDay(-1); $('dNext').onclick = () => shiftDay(1); $('dToday').onclick = () => { day = pickDay(); renderToday(); };
$('dPick').onchange = () => { day = $('dPick').value; renderToday(); };

// ---------- 계획표 ----------
function renderPlan(){
  const chk = J('kw26m:chk_v2', {}); const t = todayStr(), nm = nowM();
  let h = '<div class="vh"><h2>계획표</h2><button class="btn sm alt" id="pPdf">계획표 PDF</button><button class="btn sm alt" id="pMd">계획 원문(md)</button><button class="btn sm alt" id="pOpenAll">모두 펼치기</button></div><div class="note">원본: ' + esc(CFG.plan) + ' (집 PC가 계획을 바꾸면 새로고침으로 반영) · 체크는 오늘 할 일과 같은 기록</div>';
  // 과목별 합계
  const sum = {}; PLAN.forEach(p => p.tasks.forEach(x => { if (!isStudy(x)) return; const k = SUBJ_OF(x.subject || '') || '기타'; sum[k] = (sum[k] || { t: 0, d: 0 }); sum[k].t += x.minutes || 0; if ((chk[p.date] || []).indexOf(p.tasks.indexOf(x)) >= 0) sum[k].d += x.minutes || 0; }));
  h += '<div class="ql" style="margin:8px 0">' + Object.keys(sum).map(k => '<span class="pill" style="--c:' + (META[k] ? META[k].color : '#64748b') + '">' + esc(META[k] ? META[k].short : k) + ' ' + Math.round(sum[k].d/60*10)/10 + '/' + Math.round(sum[k].t/60*10)/10 + 'h</span>').join('') + '</div>';
  PLAN.forEach(p => {
    const done = chk[p.date] || []; const isT = p.date === t;
    const dw = '일월화수목금토'[new Date(p.date + 'T00:00:00').getDay()];
    const tot = p.tasks.filter(isStudy).reduce((a,x) => a + (x.minutes || 0), 0);
    const ts = p.tasks.map((x,j) => Object.assign({ j }, x)).sort((a,b) => hm(a.start) - hm(b.start));
    h += '<details class="pday' + (isT ? ' today' : '') + '"' + (isT || p.date > t && p.date <= addDay(t, 1) ? ' open' : '') + '><summary>' + p.date.slice(5).replace('-','/') + '(' + dw + ')' + (isT ? ' <span class="nowtag">오늘</span>' : '') + ' <span class="note" style="font-weight:400">' + esc((p.note || '').slice(0, 90)) + '</span><span class="pp">' + done.length + '/' + p.tasks.length + ' · ' + Math.round(tot/6)/10 + 'h</span></summary>';
    h += '<table class="pt"><tr><th style="width:96px">시간</th><th style="width:90px">과목</th><th>할 일</th><th style="width:200px">목표</th></tr>' + ts.map(x => { const k = SUBJ_OF(x.subject || ''); const on = done.indexOf(x.j) >= 0; const now = isT && nm >= hm(x.start) && nm < hm(x.end); return '<tr class="' + (on ? 'done' : '') + (now ? ' now' : '') + '"><td>' + esc(x.start + '~' + x.end) + '</td><td><span class="pill" style="--c:' + (k && META[k] ? META[k].color : '#94a3b8') + '">' + esc(k && META[k] ? META[k].short : x.subject) + '</span></td><td>' + esc(x.task) + '</td><td class="note">' + esc(x.goal || '') + '</td></tr>'; }).join('') + '</table></details>';
  });
  const root = $('v-plan'); root.innerHTML = h;
  root.querySelector('#pPdf').onclick = () => openViewer(CFG.planPdf, '계획표 PDF', 'plan');
  root.querySelector('#pMd').onclick = () => openViewer(CFG.planDoc, '계획 원문', 'plan');
  root.querySelector('#pOpenAll').onclick = () => root.querySelectorAll('details').forEach(d => d.open = true);
}
function addDay(s, n){ const d = new Date(s + 'T00:00:00'); d.setDate(d.getDate() + n); return d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate()); }

// ---------- 전체 오답 ----------
let wSubj = 'all', wType = 'all';
function wrongItems(){
  const out = [];
  ORDER.filter(k => META[k].kind === 'board').forEach(k => { const m = META[k]; const marks = J(m.subj + '_mock:marks', {}); const lab = {}; (CARDS[k] || []).forEach(c => lab[c[0]] = c[1]);
    Object.keys(marks).forEach(id => { const mk = marks[id]; if (!mk || !/[xu]/.test(mk.s || '') || lab[id] == null) return; out.push({ k, id, label: lab[id], s: mk.s, t: mk.t || 0, rec: (mk.h || []).map(s => s === 'o' ? '맞' : s === 'x' ? '틀' : '모').join(' ') + (mk.t ? ' · ' + fmtDT(mk.t) : '') }); }); });
  if (META.hack) { const hw = J('skhx1:wrong', {}); const hs = J('skhx1:stats', {}); Object.keys(hw).forEach(id => { if (HK.ids[id] == null) return; const s = hs[id] || {}; out.push({ k: 'hack', id, label: id + '. ' + HK.ids[id].replace(/<[^>]*>/g, '').slice(0, 90), s: 'x', t: 0, rec: s.n ? '푼 횟수 ' + s.n + ' · 맞음 ' + s.c : '' }); }); }
  if (META.quiz) { const qw = J('kw26m:wrong', {}); const ql = {}; QUIZ.forEach(q => ql[q[0]] = q); Object.keys(qw).forEach(id => { const q = ql[id]; if (!q) return; const w = qw[id] || {}; out.push({ k: 'quiz', id, label: '[' + q[1] + '] ' + q[2], s: 'x', t: 0, rec: '틀림 ' + (w.n || 1) + '회' + (w.last ? ' · ' + w.last : '') }); }); }
  return out;
}
function renderWrong(){
  const all = wrongItems(); const cnt = k => all.filter(x => x.k === k).length;
  $('wChips').innerHTML = '<button data-s="all"' + (wSubj === 'all' ? ' class="on"' : '') + '>전체 (' + all.length + ')</button>' + ORDER.filter(k => META[k].kind !== 'essay').map(k => '<button data-s="' + k + '"' + (wSubj === k ? ' class="on"' : '') + ' style="border-color:' + META[k].color + '">' + esc(META[k].short) + ' (' + cnt(k) + ')</button>').join('');
  $('wChips').querySelectorAll('button').forEach(b => b.onclick = () => { wSubj = b.dataset.s; renderWrong(); });
  $('wType').querySelectorAll('button').forEach(b => { b.classList.toggle('on', b.dataset.v === wType); b.onclick = () => { wType = b.dataset.v; renderWrong(); }; });
  const list = all.filter(x => (wSubj === 'all' || x.k === wSubj) && (wType === 'all' || x.s === wType)).sort((a,b) => ORDER.indexOf(a.k) - ORDER.indexOf(b.k) || b.t - a.t);
  if (!list.length) { $('wList').innerHTML = '<div class="box">아직 틀림·모름 표시가 없어. 공부판 위 줄의 맞음/틀림/모름 버튼이나 실전 모드 채점으로 쌓인다.</div>'; return; }
  $('wList').innerHTML = '<table class="wl"><tr><th>과목</th><th>표시</th><th>문제</th><th>기록</th><th></th></tr>' + list.map((x,i) => '<tr><td><span class="pill" style="--c:' + META[x.k].color + '">' + esc(META[x.k].short) + '</span></td><td><span class="mk ' + x.s + '">' + (x.s === 'x' ? '틀림' : '모름') + '</span></td><td>' + esc(x.label) + '</td><td class="note">' + esc(x.rec) + '</td><td><button class="btn sm" data-i="' + i + '">' + (META[x.k].kind === 'board' ? '이 카드로' : '열기') + '</button></td></tr>').join('') + '</table>';
  $('wList').querySelectorAll('button[data-i]').forEach(b => b.onclick = () => { const x = list[+b.dataset.i]; openSubject(x.k, META[x.k].kind === 'board' ? x.id : null, 'board'); });
}

// ---------- 기록 백업·옮기기 ----------
function dumpLS(){ const o = {}; try { for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); o[k] = localStorage.getItem(k); } } catch(e){} return o; }
let lastSig = '';
function backup(beacon){
  const o = dumpLS(); const s = JSON.stringify(o); const sig = s.length + ':' + s.slice(-200);
  if (sig === lastSig) return; lastSig = sig;
  if (beacon && navigator.sendBeacon) { navigator.sendBeacon('/api/lsbackup', new Blob([s], { type: 'application/json' })); return; }
  fetch('/api/lsbackup', { method: 'POST', body: s }).then(() => { LS.set(SV + 'bk', String(Date.now())); }).catch(() => {});
}
async function checkImport(force){
  try {
    const r = await api('/api/lsimport'); if (!r || !r.data) return 0;
    if (!force && LS.get(SV + 'imported') === r.at) return 0;
    let n = 0; Object.keys(r.data).forEach(k => { if (force || LS.get(k) == null) { LS.set(k, r.data[k]); n++; } });
    LS.set(SV + 'imported', r.at); if (n) toast('예전 기록 ' + n + '개 가져옴 (' + r.at + ')', 5000); return n;
  } catch(e){ return 0; }
}
function renderSettings(){
  const bk = +LS.get(SV + 'bk') || 0;
  const root = $('v-settings');
  root.innerHTML = '<div class="vh"><h2>설정 · 도움말</h2></div>' +
  '<div class="box"><b>주소</b>: <code>' + esc(location.origin) + '/</code> (로컬 서버, 이 컴퓨터에서만 열림). 즐겨찾기해 두면 된다.<br>서버 켜기: 통합공부판 폴더의 <code>서버켜기.cmd</code> 더블클릭 (로그인하면 자동으로 켜지게 등록돼 있음). Aside 한테 "통합공부판 열어줘" 라고 해도 된다.</div>' +
  '<div class="box"><b>고치는 법</b><ul><li>과목·공부판 파일·시험 일정·기본 자료 링크: <code>config.json</code> (저장 후 새로고침)</li><li>추가자료: 과목 화면 "자료" 탭이나 사이드바 "추가자료"에 끌어다 놓기 / Ctrl+V / 링크 추가. 파일은 <code>추가자료\\과목\\</code> 에 저장 (폴더에 직접 넣어도 보인다)</li><li>원본 공부판·계획(study_plan.json)은 집 PC가 고치고, 여기서는 새로고침만 하면 반영 (다시 생성할 필요 없음)</li><li>화면: <code>index.html</code>·<code>app.css</code>, 동작: <code>app.js</code>, 서버: <code>server.py</code></li><li>단축키: <kbd>\\</kbd> 사이드바 접기</li></ul></div>' +
  '<div class="box"><b>기록 (필기·맞음/틀림·체크)</b><br>브라우저 저장소에 있고, 5분마다 + 닫을 때 <code>data\\ls_backup_컴퓨터이름.json</code> 으로 자동 백업. 마지막 백업: ' + (bk ? fmtDT(bk) : '아직') + '<div class="frm"><button class="btn sm" id="sBk">지금 백업</button><button class="btn sm alt" id="sExp">기록 파일로 내려받기</button><label class="btn sm alt" style="cursor:pointer">기록 파일 불러오기<input type="file" id="sImp" accept=".json" hidden></label><button class="btn sm alt" id="sRestore">서버 백업에서 되살리기</button></div>' +
  '<div class="note">예전에 file:// 로 열던 공부판 기록 옮기기: 크롬 주소창에 통합공부판 폴더의 <code>기록옮기기.html</code> 을 file:// 로 열고 버튼 한 번 → 여기서 새로고침하면 빈 칸만 채워서 가져온다. <button class="btn sm alt" id="sForce">옮긴 기록 덮어쓰기로 다시 가져오기</button></div></div>' +
  '<div class="box"><b>상태</b><br>서버 메타: ' + esc(MT.built) + ' · 과목 ' + ORDER.length + '개 · 계획 ' + PLAN.length + '일 · 문제은행 ' + QUIZ.length + '문항 · 해커톤 ' + Object.keys(HK.ids).length + '문항' + (MT.errors.length ? '<br><span class="x">오류: ' + esc(MT.errors.join(' / ')) + '</span>' : '') + '<br>원본 수정 시각: ' + Object.keys(MT.files).map(k => esc((META[k] ? META[k].short : k) + ' ' + fmtDT(MT.files[k].mtime*1000))).join(' · ') + '</div>';
  root.querySelector('#sBk').onclick = () => { lastSig = ''; backup(false); toast('백업함'); setTimeout(renderSettings, 600); };
  root.querySelector('#sExp').onclick = () => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(dumpLS())], { type: 'application/json' })); a.download = '통합공부판_기록_' + todayStr() + '.json'; a.click(); };
  root.querySelector('#sImp').onchange = async e => { const f = e.target.files[0]; if (!f) return; try { const o = JSON.parse(await f.text()); const src = o.data || o; if (!confirm(Object.keys(src).length + '개 키를 덮어쓸까?')) return; Object.keys(src).forEach(k => LS.set(k, src[k])); toast('불러옴, 새로고침해'); } catch(err){ toast('실패: ' + err.message); } };
  root.querySelector('#sRestore').onclick = async () => { try { const r = await api('/api/lsbackup'); if (!r.data) { toast('서버 백업 없음'); return; } if (!confirm(r.at + ' 백업(' + Object.keys(r.data).length + '개)으로 덮어쓸까?')) return; Object.keys(r.data).forEach(k => LS.set(k, r.data[k])); toast('되살림, 새로고침해'); } catch(e){ toast('실패'); } };
  root.querySelector('#sForce').onclick = async () => { const n = await checkImport(true); toast(n ? n + '개 덮어씀, 새로고침해' : '옮긴 기록 없음'); };
}

// ---------- 시계 ----------
function tick(){
  const d = new Date(); $('sClock').textContent = (d.getMonth()+1) + '/' + d.getDate() + '(' + '일월화수목금토'[d.getDay()] + ') ' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
  document.querySelectorAll('[data-dd]').forEach(el => { const r = dd(META[el.dataset.dd], false); el.textContent = r.txt; el.className = 'dd ' + r.cls; });
  tickBar();
}
let lastMin = -1;
setInterval(tick, 1000);
setInterval(() => { const m = nowM(); if (m !== lastMin) { lastMin = m; renderBadges(); if (!cur && (view === 'today' || view === 'dash')) render(); } }, 20000);
addEventListener('storage', () => { if (!cur && view !== 'memo') render(); else renderBadges(); });
setInterval(() => backup(false), 5*60*1000);

// ---------- 시작 ----------
async function loadExtras(){ try { EXTRAS = await api('/api/extras'); } catch(e){} }
async function boot(){
  if (location.protocol === 'file:') { $('banner').innerHTML = '<b>file:// 로 열려 있어.</b> 이 화면은 로컬 서버에서 열어야 한다: <code>서버켜기.cmd</code> 실행 후 <a href="http://localhost:8626/">http://localhost:8626/</a>. 예전 기록 옮기기는 <a href="기록옮기기.html">기록옮기기.html</a>.'; $('banner').classList.add('on'); return; }
  try { MT = await api('/api/meta'); } catch(e){ $('banner').innerHTML = '서버 응답 없음: ' + esc(e.message) + ' · <code>서버켜기.cmd</code> 실행 후 새로고침'; $('banner').classList.add('on'); return; }
  CFG = MT.config; QUIZ = MT.quiz || []; PLAN = (MT.plan || []).slice().sort((a,b) => a.date < b.date ? -1 : 1); CARDS = MT.cards || {};
  (CFG.subjects || []).forEach(s => { META[s.key] = Object.assign({}, s, MT.boards[s.key] || {}); ORDER.push(s.key); });
  await checkImport(false);
  await Promise.all([loadExtras(), loadHack()]);
  renderSide();
  $('sFoot').innerHTML = '<span class="ok">예시 스냅샷 · 서버 저장 안 됨</span> · ' + esc(MT.built.slice(5, 16));
  const hp = {}; location.hash.slice(1).split('&').forEach(s => { const i = s.indexOf('='); if (s) hp[i < 0 ? s : s.slice(0,i)] = i < 0 ? '1' : decodeURIComponent(s.slice(i+1)); });
  tick();
  if (hp.v === 'subj' && META[hp.k]) { show('dash'); openSubject(hp.k, hp.card || null, hp.t || 'board'); }
  else show(hp.v && $('v-' + hp.v) && hp.v !== 'viewer' ? hp.v : 'dash');
  setTimeout(() => backup(false), 4000);
}
window.__hub = { openSubject, show, openViewer, frames, stat, wrongItems, get META(){ return META; }, get PLAN(){ return PLAN; } };
boot();
})();

// 1018 머리줄 접기 (상태 기억)
(() => { const K = "kw26u:subfold"; const set = on => { document.body.classList.toggle("subfold", on); try { localStorage.setItem(K, on ? "1" : "0"); } catch(e){} }; let on = false; try { on = localStorage.getItem(K) === "1"; } catch(e){} set(on); const f = document.getElementById("bFold"), u = document.getElementById("bUnfold"); if (f) f.onclick = () => set(true); if (u) u.onclick = () => set(false); })();

/* 1022 모바일: ☰ 메뉴 서랍 */
(function(){ if (document.getElementById('mNavBtn')) return; var b=document.createElement('button'); b.id='mNavBtn'; b.textContent='☰'; b.title='메뉴'; var bg=document.createElement('div'); bg.id='mNavBg'; document.body.appendChild(b); document.body.appendChild(bg);
 var close=function(){document.body.classList.remove('mnav')}; b.onclick=function(){document.body.classList.toggle('mnav')}; bg.onclick=close;
 var nav=document.getElementById('sNav'); if (nav) nav.addEventListener('click', function(e){ if (e.target.closest('a') && innerWidth<=760) close(); }); })();
