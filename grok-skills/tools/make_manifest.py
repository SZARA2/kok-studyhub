#!/usr/bin/env python3
"""콕 리소스 팩 MANIFEST.json 생성. 사용: python3 tools/make_manifest.py [루트=.] [--out MANIFEST.json]
팩에 들어가는 파일(skills/, tools/, tests/ 스크립트·package 파일·samples) 전부의 sha256·크기와 스킬 버전을 적는다.
private/, node_modules/, __pycache__, tests/out, 로그·스크린샷(실행 결과물)은 넣지 않는다."""
import hashlib,json,os,re,sys,datetime
R=os.path.abspath(sys.argv[1] if len(sys.argv)>1 and not sys.argv[1].startswith('--') else '.')
out=sys.argv[sys.argv.index('--out')+1] if '--out' in sys.argv else os.path.join(R,'MANIFEST.json')
INC=['skills','tools','tests']
SKIP_DIR={'node_modules','__pycache__','private','out','logs','screenshots'}
def files():
    for top in INC:
        for d,ds,fs in os.walk(os.path.join(R,top)):
            ds[:]=sorted(x for x in ds if x not in SKIP_DIR)
            for f in sorted(fs):
                if f.endswith(('.pyc','.log','.png'))or f=='regress_result.txt':continue
                yield os.path.relpath(os.path.join(d,f),R).replace(os.sep,'/')
def sha(p):return hashlib.sha256(open(os.path.join(R,p),'rb').read()).hexdigest()
def ver(p):
    m=re.search(r'\|\s*버전\s*\|\s*(v[\d.]+)',open(os.path.join(R,p),encoding='utf-8').read());return m.group(1) if m else None
previous=os.path.join(R,'MANIFEST.json')
paths=[x['path'] for x in json.load(open(previous,encoding='utf-8'))['files']] if os.path.exists(previous) else list(files())
# Explicit release additions keep unrelated working files out of public packs.
paths=sorted(set(paths+['tools/verify_web.py','tests/test_partial_web.py']))
# These allowlisted resources are text and .gitattributes requires LF on every host.
for p in paths:
    fp=os.path.join(R,p)
    data=open(fp,'rb').read()
    if b'\r\n' in data:
        with open(fp,'wb') as stream:stream.write(data.replace(b'\r\n',b'\n'))
F=[{"path":p,"sha256":sha(p),"bytes":os.path.getsize(os.path.join(R,p))} for p in paths]
S={p.split('/')[1]:ver(p) for p in (x['path'] for x in F) if re.fullmatch(r'skills/kok-[\w-]+/SKILL\.md',p)}
versions=set(S.values())
if len(versions)!=1 or None in versions:raise ValueError('all seven skill versions must match')
M={"pack":"kok-skills","pack_version":next(iter(versions)),"pack_revision":"2026-11-01-delivery.3","created":datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')+' KST(Asia/Seoul)',
   "source":"Reviewed fixed resource bundle; public template memory supplies the actual URL and SHA256 for automatic first-run preparation.",
   "skills":S,"requires":{"python3":">=3.9","node":">=18","playwright(npm, tests/만)":"1.59.1","chromium":"playwright 기본 경로 또는 KOK_CHROME","ffmpeg/ffprobe":"팟캐스트 음원 확인용(선택)"},
   "files":F,"file_count":len(F)}
with open(out,'w',encoding='utf-8',newline='\n') as stream:json.dump(M,stream,ensure_ascii=False,indent=1)
print('manifest',out,len(F),'files',S)
