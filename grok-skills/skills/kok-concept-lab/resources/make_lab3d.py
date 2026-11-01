#!/usr/bin/env python3
"""사용법: python3 make_lab3d.py lab.json out.html
1) safe_expr.py(AST 허용목록)로 모든 expr을 검사: 거부되면 만들지 않고 종료코드 2.
2) lab3d_template.html의 /*SAFE_EXPR*/ 에 safe_expr.js, `const DATA=/*LAB_JSON*/null;` 에 JSON('<'는 \\u003c)을 넣어 한 파일로 낸다."""
import json,sys,os
here=os.path.dirname(os.path.abspath(__file__));sys.path.insert(0,here)
from safe_expr import compile_expr
def validate(L):
    names={v['name'] for v in L['variables']}|{o['name'] for o in L['outputs']}|{'t'}
    if L.get('graph'):names.add(L['graph']['x']['name'])
    errs=[]
    for o in L['outputs']+(L.get('graph') or {}).get('y',[]):
        try:compile_expr(o['expr'],names)
        except Exception as e:errs.append(f"{o.get('name',o.get('label'))}: {e}")
    return errs
def make(src,out):
    L=json.load(open(src,encoding='utf-8'));errs=validate(L)
    if errs:print('거부(만들지 않음):',errs);sys.exit(2)
    t=open(os.path.join(here,'lab3d_template.html'),encoding='utf-8').read()
    js=open(os.path.join(here,'safe_expr.js'),encoding='utf-8').read()
    pl=json.dumps(L,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    h=t.replace('/*SAFE_EXPR*/',js,1).replace('const DATA=/*LAB_JSON*/null;','const DATA='+pl+';',1)
    os.makedirs(os.path.dirname(os.path.abspath(out)),exist_ok=True);open(out,'w',encoding='utf-8').write(h);print('wrote',out,len(h))
if __name__=='__main__':make(sys.argv[1],sys.argv[2])
