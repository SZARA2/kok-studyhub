#!/usr/bin/env python3
"""사용법: python3 build.py spec.json <출력폴더>  -> <출력폴더>/drill.html
spec은 <script type="application/json">에 넣고 '<' '>' '&'를 \\u003c 등으로 바꿔 HTML/스크립트 탈출을 막는다.
화면은 모든 글을 textContent로 넣으므로 spec 안의 HTML 태그는 글자로만 보인다."""
import json,sys,os
here=os.path.dirname(os.path.abspath(__file__))
def payload(spec):
    return json.dumps(spec,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
def build(spec_path,out_dir,name='drill.html'):
    spec=json.load(open(spec_path,encoding='utf-8'))
    t=open(os.path.join(here,'template.html'),encoding='utf-8').read()
    os.makedirs(out_dir,exist_ok=True);p=os.path.join(out_dir,name)
    open(p,'w',encoding='utf-8').write(t.replace('/*__SPEC__*/',payload(spec),1));return p
if __name__=='__main__':
    print('wrote',build(sys.argv[1],sys.argv[2],*(sys.argv[3:4])))
