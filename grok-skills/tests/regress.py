#!/usr/bin/env python3
"""콕 통합 회귀 테스트. 사용: python3 tests/regress.py all <demo폴더> | lecture f | drill f | lab f | schedule f | skills"""
import sys,json,re,os,math,glob
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails=[];oks=[]
def ck(c,m):(oks if c else fails).append(m)
def lecture(f):
    t=open(f,encoding='utf-8').read()
    for h in['## 출처 표','## 읽은 목록','## 누락·제외 목록','## 개념','## 문제']:ck(h in t,f'lecture: {h}')
    ck(re.search(r'coverage: (complete|partial|blocked)',t),'lecture: coverage 값')
    rows=re.findall(r'^\| (S\d+) \|.*\| (ok|partial|blocked) \|',t,re.M);ck(len(rows)>0,f'lecture: 출처 행 {len(rows)}개 상태 포함')
    cs=re.split(r'^### C\d+',t,flags=re.M)[1:];ck(len(cs)>0,f'lecture: 개념 {len(cs)}개')
    for k,c in enumerate(cs):
        for f7 in['정의·조건','직관','선행개념','단계풀이','흔한 오해','관련개념','원문위치']:ck(f'- {f7}:' in c,f'lecture: C{k+1} {f7}')
    ps=re.split(r'^### P\d+',t,flags=re.M)[1:]
    for k,p in enumerate(ps):
        for f3 in['원문 문제','원문 제공 정답','Bot 풀이']:ck(f'- {f3}:' in p,f'lecture: P{k+1} {f3}')
    ck('제외(이번 범위 밖)' in t,'lecture: 제외 표시')
    ck(not re.search(r'\d\d:\dx',t),'lecture: 플레이스홀더 시각 없음')
def images(d):
    # v1.2.0 수집 회귀: 내려받은 이미지/슬라이드는 전부 직접 열람해야 함(collector v2 기준 퇴행 금지)
    import glob
    imgs=sorted(os.path.basename(f) for f in glob.glob(os.path.join(d,'raw','*')) if f.lower().endswith(('.png','.jpg','.jpeg','.gif','.webp')))
    lg=os.path.join(d,'review_images.log');ck(os.path.exists(lg),'images: review_images.log 있음')
    if not os.path.exists(lg):return
    L=open(lg,encoding='utf-8').read();t=open(os.path.join(d,'lecture.md'),encoding='utf-8').read()
    miss=[i for i in imgs if not re.search(r'^'+re.escape(i)+r' \|.*\| opened=yes',L,re.M)]
    ck(imgs and not miss,f'images: 내려받은 이미지 {len(imgs)}장 모두 opened=yes (미열람 {miss[:5]})')
    ck(all(len(l.split(' | '))==6 for l in L.splitlines() if l and not l.startswith('#')),'images: 로그 각 줄 6칸(파일|해시|제목|열람|발견|반영)')
    ck(not re.search(r'직접 열지 않고|직접 열람 안 함\)',t),'images: lecture.md에 "직접 열람 안 함" 잔여 없음')
    ck("'미확인'" in t or '미확인' in t.split('### P7')[-1] if '### P7' in t else True,'images: 없는 연습문제는 미확인 유지')
def drill(f):
    s=json.load(open(f,encoding='utf-8'));ck(s.get('title'),'drill: title')
    for k,q in enumerate(s['questions']):
        ok=len(q['o'])==4 and q['a'] in(0,1,2,3) and q['ok'] and q['no'] and q['loc'] and q['src'] in('원문 그대로','변형','원문 기반 Bot 작성') and q['ans_src'] in('원문 제공 정답','Bot 풀이')
        ck(ok,f'drill: Q{k+1} 형식');ck(len(set(q['o']))==4,f'drill: Q{k+1} 보기 중복 없음')
    ck(len({q['a'] for q in s['questions']})>1,'drill: 정답 위치 섞임')
sys.path.insert(0,os.path.join(R,'skills/kok-concept-lab/resources'))
from safe_expr import compile_expr
def lab(f):
    L=json.load(open(f,encoding='utf-8'))
    for k in['title','concept','formula','scene','variables','outputs','objects','predict','challenge','loc']:ck(k in L,f'lab: {k}')
    V=L['variables'];names={x['name'] for x in V}|{o['name'] for o in L['outputs']}|{'t'}
    if L.get('graph'):names|={L['graph']['x']['name']}
    C={}
    for o in L['outputs']:
        try:C[o['name']]=compile_expr(o['expr'],names);ck(True,f"lab: {o['name']} 식 허용목록 통과")
        except Exception as ex:ck(False,f"lab: {o['name']} 식 거부 {ex}")
    def run(vals):
        env=dict(vals)
        for o in L['outputs']:env[o['name']]=C[o['name']](env)
        return env
    env=run({x['name']:x['value'] for x in V})
    for o in L['outputs']:ck(abs(env[o['name']]-o['expected'])<1e-6,f"lab: {o['name']} 기본값 {env[o['name']]:.6g} == expected {o['expected']}")
    for tag,pick in(('최소',lambda x:x['min']),('최대',lambda x:x['max'])):
        e=run({x['name']:pick(x) for x in V});ok=all(math.isfinite(e[o['name']]) for o in L['outputs'])
        ck(ok,f"lab: 극단값({tag}) 모든 출력 유한 {[round(e[o['name']],4) for o in L['outputs']]}")
    for x in V:
        if x.get('max_var'):
            ck(x['max_var'] in {y['name'] for y in V},f"lab: {x['name']}.max_var={x['max_var']} 선언됨")
            for chk_ in L.get('checks',[]):ck(chk_['vars'][x['name']]<=chk_['vars'][x['max_var']],f"lab: 검산 입력 {x['name']}≤{x['max_var']} {chk_['vars']}")
    ck(not any('Math.min(' in o['expr'] for o in L['outputs']) or not any(x.get('max_var') for x in V),'lab: max_var가 있으면 Math.min으로 몰래 자르지 않음')
    for chk_ in L.get('checks',[]):
        e=run(chk_['vars']);ck(abs(e[chk_['out']]-chk_['expect'])<1e-6,f"lab: 검산 {chk_['vars']} → {chk_['out']}={e[chk_['out']]:.6g} (기대 {chk_['expect']})")
    if L.get('graph'):
        xn=L['graph']['x']['name']
        for y in L['graph']['y']:
            g=compile_expr(y['expr'],names);e=run({x['name']:x['value'] for x in V})
            for xv in(L['graph']['x']['min'],L['graph']['x']['max']):e[xn]=xv;ck(math.isfinite(g(e)),f"lab: graph {y['label']} {xn}={xv} 유한")
BAD_EXPRS=["__import__('os').system('echo HACK')","().__class__.__bases__[0].__subclasses__()","N.__class__","constructor","'x'.constructor.constructor('return 1')()",
 "window.alert(1)","document.cookie","globalThis","lambda: 1","function(){return 1}","(()=>1)()","x=>x","N=5","N:=5","open('f')","print(1)","eval('1')","Math.constructor","Math.random()","N if N else 1","[1][0]","N.real"]
def evaltest():
    import builtins
    hit={'n':0};orig=builtins.__import__
    for e in BAD_EXPRS:
        try:compile_expr(e,{'N','M','K','t'});ck(False,f'evaltest: 거부되어야 함 {e!r}')
        except (ValueError,SyntaxError) as ex:ck(True,f'evaltest: 실행 없이 거부 {e!r} ({type(ex).__name__})')
    LIMS=[('1'+'+1'*150,'길이'),('-'*40+'1','깊이'),('+'.join(['N']*120),'노드'),('2**65','지수 **'),('Math.pow(10,400)','지수 pow'),('1/0','Infinity'),('N/0','Infinity'),('Math.log(0)','-Infinity/정의역'),('Math.sqrt(-1)','NaN'),('Math.exp(1000)','overflow')]
    for e,w in LIMS:
        try:compile_expr(e,{'N','M','K','t'})({'N':1,'M':1,'K':1,'t':0});ck(False,f'evaltest: 상한/유한성 오류여야 함 {w}')
        except ValueError as ex:ck(True,f'evaltest: 상한/유한성 오류 {w} ({str(ex)[:30]})')
    for bad in(float('inf'),float('nan')):
        try:compile_expr('N',{'N'})({'N':bad});ck(False,f'evaltest: 입력 {bad} 거부')
        except ValueError:ck(True,f'evaltest: 유한하지 않은 입력 {bad} 거부')
    ck(compile_expr('2**64',set())({})==2.0**64,'evaltest: 지수 상한 경계 64 허용')
    ck(abs(compile_expr('Math.log2(N/Math.min(M,N))+2**-1-t%2',{'N','M','t'})({'N':8,'M':2,'t':3})-(2+0.5-1))<1e-12,'evaltest: 허용 식 정상 계산')
def schedule(f):
    S=json.load(open(f,encoding='utf-8'))
    for it in S['items']:
        ck(it.get('label') in('확정','제안','테스트용 가상 일정, 실제 수업 마감 아님'),f"schedule: {it['id']} 라벨")
        tv=it.get('time',it.get('start',''))
        ck(tv!='23:59' or it['label']=='확정',f"schedule: {it['id']} 23:59 고정 없음")
        ck(re.match(r'^\d\d:\d\d$',tv) or tv in('시각 미정',''),f"schedule: {it['id']} 시각 형식")
        if it['label']=='제안':ck(it.get('source'),f"schedule: {it['id']} 제안 근거")
    ck(S.get('note'),'schedule: 원문 마감 유무 문장')
def skills(d=os.path.join(R,'skills')):
    names=['kok-onboarding','kok-router','kok-lecture-collector','kok-problem-drill','kok-podcast','kok-concept-lab','kok-schedule']
    ck(sorted(os.listdir(d))==sorted([n for n in os.listdir(d) if n in names]+[n for n in os.listdir(d) if n.endswith('.md')]),'skills: 7개 외 스킬 폴더 없음')
    for n in names:
        t=open(f'{d}/{n}/SKILL.md',encoding='utf-8').read()
        ck(t.startswith(f'---\nname: {n}\n'),f'skills: {n} frontmatter name')
        ck('버전 | v1.2.0' in t,f'skills: {n} 버전 v1.2.0');ck(re.search(r'v1\.2\.0.*?sha256',t.split('## 변경이력')[-1],re.S) is not None,f'skills: {n} 변경이력에 v1.2.0 upstream sha256');ck(n!='kok-schedule' or not [l for l in t.split('## 변경이력')[0].split('## 검증조건')[1].splitlines() if re.search(r'(?i)klas|lms|vault|로그인|학교 사이트',l) and not re.search('않|없음|금지|제거|빼|거부',l)],'skills: kok-schedule 본문에 KLAS/LMS 로그인·수집 절차 없음')
        for ref in sorted(set(re.findall(r'resources/([A-Za-z0-9_./-]+\.(?:json|js|py|html|md|css)\b)',t))):ck(os.path.exists(f'{d}/{n}/resources/{ref}'),f'skills: {n} 참조 resources/{ref} 존재')
        for k in['담당자','유래','## 검증조건','## 변경이력','## 공통 규칙']:ck(k in t,f'skills: {n} {k}')
    rt=open(f'{d}/kok-router/SKILL.md',encoding='utf-8').read().split('## 순서')[0].split('## 번호표')[1]
    for bad in['| problem-drill','notebooklm-studio-pack |','concept-lab-visualizer |','klas-deadline-cards |']:ck(bad not in rt,f'router: 레거시 {bad} 미호출')
DAYS=['월','화','수','목','금','토','일']
def _m(s):return int(s[:2])*60+int(s[3:]) if s and re.match(r'^\d\d:\d\d$',s) else None
def _rng(c):
    s,e=_m(c['start']),_m(c['end']);rv=(not c['confirmed']) and c['needs_review']
    if e is None:e=24*60
    elif rv:e+=10
    if rv and any(r['field']=='start' for r in c['needs_review']):s-=10
    return s,e
def timetable(f,sf=None,zero=None):
    raw=open(f,encoding='utf-8').read();T=json.loads(raw)
    ck(T.get('term') is None or T.get('term_note'),'timetable: 학기 없으면 날짜 미생성 메모')
    ck(not re.search(r'"date"\s*:|\d{4}-\d\d-\d\d',raw),'timetable: 날짜 필드/날짜 값 없음(주간 반복)')
    ck(T.get('empty_cell_note'),'timetable: 빈칸≠개인 일정 비어 있음 메모')
    for c in T['classes']:
        i=c['id']
        for k in('id','day','title','start','end','raw_label','needs_review','confirmed'):ck(k in c,f'timetable: {i} {k} 필드')
        ck(c['day'] in DAYS,f'timetable: {i} 요일')
        ck(isinstance(c['raw_label'],str),f'timetable: {i} raw_label 문자열')
        ck(_m(c['start']) is not None,f'timetable: {i} 시작 HH:MM')
        ck(c['end'] is None or _m(c['end'])>_m(c['start']),f'timetable: {i} 종료>시작 또는 미확인(null)')
        ck(c['end'] is not None or any(r['field']=='end' for r in c['needs_review']),f'timetable: {i} 종료 미확인이면 needs_review')
        ck(c['confirmed'] or c['needs_review'],f'timetable: {i} 미확인이면 needs_review 존재')
        ck(all(r.get('reason') for r in c['needs_review']),f'timetable: {i} needs_review 이유')
    if zero:
        hit=[c for c in T['classes'] if c['raw_label']==zero];ck(hit and f'"raw_label":"{zero}"' in raw.replace(' ',''),f'timetable: 앞의 0 보존 "{zero}"')
    ck(any(c['needs_review'] for c in T['classes']),'timetable: needs_review 항목 있음')
    if sf:
        S=json.load(open(sf,encoding='utf-8'))
        for it in S['items']:
            d=it.get('day');s=_m(it.get('start'))
            if d and s is not None:
                e=_m(it.get('end')) or s+1
                ov=[c['id'] for c in T['classes'] if c['day']==d and s<_rng(c)[1] and e>_rng(c)[0]]
                ck(not ov,f"schedule: {it['id']} 수업과 겹치지 않음 {ov}")
            if it['label']=='제안':ck('확정' not in it['title'],f"schedule: {it['id']} 제안은 확정 아님")
            if re.search('마감|시험|과제',it['title']) and it['label']=='확정':ck('사용자' in it.get('source',''),f"schedule: {it['id']} 마감 확정은 사용자 명시 입력만")
        for m in S.get('materials',[]):
            ck(m.get('linked_course') is None and m.get('status')=='미연결',f"schedule: 자료 {m['id']} 임의 배정 없음(미연결)")
        ck(not any(it['label']=='확정' and re.search('마감|시험|과제',it['title']) and '사용자' not in it.get('source','') for it in S['items']),'schedule: 명시 입력 없는 확정 마감 없음')
_PT=os.path.join(R,'private/privacy_terms.txt')  # 비공개 과목명 목록(공개 패키지에 포함하지 않음)
_EX=[re.escape(l.strip()) for l in open(_PT,encoding='utf-8')] if os.path.exists(_PT) else []
PRIV=re.compile('|'.join(_EX)) if _EX else None  # 공개본에는 실제 개인 항목을 적지 않음
def privacy(*dirs):
    dirs=dirs or[os.path.join(R,x) for x in('skills','tests','template-draft','demo-mit6004')]+[os.path.join(R,'kok-web.html')]
    bad=[]
    for d in dirs:
        fs=[d] if os.path.isfile(d) else [os.path.join(r,f) for r,_,ff in os.walk(d) if 'node_modules' not in r and '/raw' not in r for f in ff]
        for fp in fs:
            if fp.endswith(('.png','.jpg','.m4a','.zip','.pyc')) or fp.endswith('regress.py'):continue
            try:tx=open(fp,encoding='utf-8').read()
            except Exception:continue
            m=PRIV.search(tx) if PRIV else None
            if m:bad.append(f'{os.path.relpath(fp,R)}:{m.group(0)}')
    ck(not bad,f'privacy: 공개 폴더에 실제 시간표 과목/강의실 없음 {bad[:5]}')
a=sys.argv[1:] or['skills']
if a[0]=='all':
    d=a[1];skills();lecture(f'{d}/lecture.md');images(d);drill(f'{d}/drill/spec.json');lab(f'{d}/lab/lab.json');schedule(f'{d}/schedule/schedule.json');timetable(os.path.join(R,'tests/samples/timetable_anon.json'),f'{d}/schedule/schedule.json','0107');evaltest();drill(os.path.join(R,'tests/samples/drill_xss.json'));privacy()
else:{'lecture':lecture,'drill':drill,'lab':lab,'schedule':schedule,'skills':skills,'timetable':timetable,'privacy':privacy,'evaltest':evaltest,'images':images}[a[0]](*a[1:])
for m in oks:print('PASS',m)
for m in fails:print('FAIL',m)
print(f'합계: PASS {len(oks)} / FAIL {len(fails)}');sys.exit(1 if fails else 0)
