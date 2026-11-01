import json,os,glob,base64,sys,argparse
from lecture_metadata import read_metadata
ap=argparse.ArgumentParser();ap.add_argument('d');ap.add_argument('--tt',default=None,help='timetable.json 경로 또는 none');ap.add_argument('--sch',default=None);ap.add_argument('--out',default=None);ap.add_argument('--key',default='kok-sch-demo');ap.add_argument('--tt-only',action='store_true',help='4번만: lecture.md·드릴·실험실·팟캐스트 없이 시간표로만 웹 생성')
A=ap.parse_args();d=A.d;R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rd=lambda p:open(os.path.join(d,p),encoding='utf-8').read()
log=[] if A.tt_only else [l.strip() for l in open(os.path.join(d,'gen.log'),encoding='utf-8')]
def t(k):
    m=[l for l in log if k in l];return (m[-1][:23]+' (Asia/Seoul)') if m else '로그 없음'
st=None if A.tt_only else json.loads(rd('podcast/status.json'))
aud=[] if A.tt_only else sorted(glob.glob(os.path.join(d,'podcast/audio.*')),key=lambda f:(not f.endswith('.mp3'),f));audio=None  # v1.2.0: mp3 우선
if aud:
    audio='podcast/'+os.path.basename(aud[0])  # 상대 경로: 웹 파일 옆 podcast/ 에 둠(HTML에 인라인하지 않음)
ttp=A.tt if A.tt is not None else os.path.join(d,'schedule/timetable.json')
TT=None if ttp=='none' or not os.path.exists(ttp) else json.load(open(ttp,encoding='utf-8'))
SCH=json.load(open(A.sch or os.path.join(d,'schedule/schedule.json'),encoding='utf-8'))
nr=sum(1 for c in (TT or {}).get('classes',[]) if c['needs_review'] and not c['confirmed'])
M4={"name":"일정 관리(시간표)","skill":"kok-schedule v1.2.0","status":"완료" if TT else "시간표 필요","status_label":(f"완료 · 확인 필요 {nr}건" if TT else "시간표 필요 (이미지/PDF/텍스트 보내기)"),"time":t('kok-schedule')}
if not A.tt_only:
  DATA={"source":read_metadata(os.path.join(d,'lecture.md')),
"modes":{"1":{"name":"문제 드릴","skill":"kok-problem-drill v1.2.0","status":"완료","time":t('kok-problem-drill')},
"2":{"name":"팟캐스트(NotebookLM)","skill":"kok-podcast v1.2.0","status":st['status'],"status_label":st.get('label',st['status']),"time":t('kok-podcast')+(' (대본만, 음원 없음)' if not audio else ' · 음원 '+st.get('duration','')+' mp3')},
"3":{"name":"개념 실험실","skill":"kok-concept-lab v1.2.0","status":"완료","time":t('kok-concept-lab')},
"4":M4},
"drill":json.loads(rd('drill/spec.json')),"lab":json.loads(rd('lab/lab.json')),"lab3d":"lab/lab3d.html","schedule":SCH,"timetable":TT,"storeKey":A.key,
"podcast":{"status":st,"script":rd('podcast_script.md'),"audio":audio}}
if A.tt_only:
    NEED={"status":"자료 필요","status_label":"자료 필요 (lecture.md 없음)","time":"생성 안 함"}
    DATA={"source":None,"modes":{"1":dict(NEED,name="문제 드릴",skill="kok-problem-drill v1.2.0"),"2":dict(NEED,name="팟캐스트(NotebookLM)",skill="kok-podcast v1.2.0"),"3":dict(NEED,name="개념 실험실",skill="kok-concept-lab v1.2.0"),"4":M4},
          "drill":None,"lab":None,"lab3d":None,"schedule":SCH,"timetable":TT,"storeKey":A.key,"podcast":None}
dr=os.path.join(R,'skills/kok-problem-drill/resources')
h=open(os.path.join(R,'tools/web_template.html'),encoding='utf-8').read()
h=h.replace('/*__MODE4CSS__*/',open(os.path.join(R,'tools/mode4.css'),encoding='utf-8').read()).replace('/*__MODE4JS__*/',open(os.path.join(R,'tools/mode4.js'),encoding='utf-8').read()).replace('/*__DRILLCSS__*/',open(dr+'/drill.css').read()).replace('/*__DRILLJS__*/',open(dr+'/drill.js').read()).replace('/*__DATA__*/null',json.dumps(DATA,ensure_ascii=False).replace('</','<\\/'))
out=os.path.abspath(A.out or os.path.join(d,'web/index.html'));os.makedirs(os.path.dirname(out),exist_ok=True);open(out,'w',encoding='utf-8').write(h)
if aud:
    dst=os.path.join(os.path.dirname(out),audio);os.makedirs(os.path.dirname(dst),exist_ok=True)
    if not os.path.exists(dst) or os.path.getsize(dst)!=os.path.getsize(aud[0]):
        try:os.remove(dst)
        except OSError:pass
        try:os.link(aud[0],dst)
        except OSError:import shutil;shutil.copy2(aud[0],dst)

import shutil
l3=os.path.join(d,'lab/lab3d.html');dst3=os.path.join(os.path.dirname(out),'lab/lab3d.html')
if not A.tt_only and os.path.abspath(l3)!=os.path.abspath(dst3):os.makedirs(os.path.dirname(dst3),exist_ok=True);shutil.copy2(l3,dst3)
print('ok',out,len(h))
