#!/usr/bin/env python3
"""리소스 팩 검증(설치 전·준비 점검용). 네트워크·설치 없음.
사용:
  python3 tools/verify_pack.py <팩 루트> [--zip <받은.zip> --zip-sha256 <템플릿 지침의 값>]
검사: (1) zip을 줬으면 zip 전체 sha256 == 지침 값  (2) MANIFEST.json의 파일이 모두 있고 sha256·크기 일치
      (3) MANIFEST의 스킬 버전 == 각 SKILL.md 버전 == skills/VERSIONS.md  (4) 스킬 7개 모두 존재
      (5) resources 아래에 MANIFEST에 없는 파일(출처 불명) 없음
하나라도 틀리면 종료코드 1. 통과하기 전에는 팩을 쓰지 않는다(덮어쓰기·자동 설치 없음)."""
import hashlib,json,os,re,sys
a=sys.argv[1:];R=os.path.abspath(a[0] if a and not a[0].startswith('--') else '.')
opt=lambda k:a[a.index(k)+1] if k in a else None
fail=[];ok=[]
def ck(c,m):(ok if c else fail).append(m)
z,zs=opt('--zip'),opt('--zip-sha256')
if z:
    ck(bool(zs) and re.fullmatch(r'[0-9a-f]{64}',zs or '') is not None,'zip: 비교할 sha256(64자리)이 주어짐 — 없으면 검증 불가로 실패')
    ck(os.path.isfile(z),f'zip 파일 있음: {z}')
    h=hashlib.sha256(open(z,'rb').read()).hexdigest() if os.path.isfile(z) else '';ck(h==zs,f'zip sha256 {h[:16]}… == 지침 값 {(zs or "")[:16]}…')
mp=os.path.join(R,'MANIFEST.json');ck(os.path.exists(mp),'MANIFEST.json 있음')
if os.path.exists(mp):
    M=json.load(open(mp,encoding='utf-8'));listed=set()
    for f in M['files']:
        p=os.path.join(R,f['path']);listed.add(f['path'])
        if not os.path.exists(p):ck(False,f'없음: {f["path"]}');continue
        h=hashlib.sha256(open(p,'rb').read()).hexdigest()
        if h!=f['sha256'] or os.path.getsize(p)!=f['bytes']:ck(False,f'해시/크기 불일치: {f["path"]}')
    ck(len(M['files'])==M.get('file_count'),f'파일 수 {len(M["files"])} == file_count')
    ck(not [x for x in fail if x.startswith(('없음','해시'))],f'MANIFEST 파일 {len(M["files"])}개 모두 존재·sha256 일치')
    ck(len(M['skills'])==7,f'스킬 7개 ({len(M["skills"])})')
    V=open(os.path.join(R,'skills/VERSIONS.md'),encoding='utf-8').read() if os.path.exists(os.path.join(R,'skills/VERSIONS.md')) else ''
    for s,v in M['skills'].items():
        sp=os.path.join(R,'skills',s,'SKILL.md');sv=re.search(r'\|\s*버전\s*\|\s*(v[\d.]+)',open(sp,encoding='utf-8').read()).group(1) if os.path.exists(sp) else None
        ck(sv==v==M['pack_version'],f'{s}: SKILL.md {sv} == MANIFEST {v} == 팩 {M["pack_version"]}')
        ck(re.search(re.escape(s)+r'.*'+re.escape(v),V) is not None,f'{s}: VERSIONS.md에 {v}')
    extra=[]
    for d,ds,fs in os.walk(os.path.join(R,'skills')):
        ds[:]=[x for x in ds if x!='__pycache__']
        for f in fs:
            rp=os.path.relpath(os.path.join(d,f),R).replace(os.sep,'/')
            if not f.endswith('.pyc') and rp not in listed:extra.append(rp)
    ck(not extra,f'MANIFEST에 없는 skills 파일 없음 {extra[:5]}')
for m in ok:print('PASS',m)
for m in fail:print('FAIL',m)
print(f'[verify_pack] 합계 PASS {len(ok)} / FAIL {len(fail)}');sys.exit(1 if fail else 0)
