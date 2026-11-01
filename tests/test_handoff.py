import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.models import CourseCreate, JobCreate, TASK_ROLES
from backend.store import Problem, Store
from client.kokbot import LocalTransport

KEYS = [{'name': r, 'role': r, 'key': 'test-only-' + r + '-'+ 'x'*32} for r in ['operator','device',*TASK_ROLES.values()]]


def headers(role='operator'):
    return {'Authorization': 'Bearer '+next(k['key'] for k in KEYS if k['role']==role)}


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(tmp_path/'ledger.sqlite',KEYS))


def post(client,path,body,role='operator',status=200):
    response=client.post('/api/v1/'+path,json=body,headers=headers(role))
    assert response.status_code==status, response.text
    return response.json()


def course(client,identifier='course1'):
    return post(client,'courses',{'id':identifier,'title':'Synthetic AND gate fixture'},status=201)


def job(client,kind,course_id='course1'):
    return post(client,'jobs',{'course_id':course_id,'kind':kind},status=201)


def complete(client,kind,result,course_id='course1'):
    j=job(client,kind,course_id)
    role=TASK_ROLES[kind]
    lease=post(client,f"jobs/{j['id']}/claim",{},role)
    return post(client,f"jobs/{j['id']}/complete",{'lease_token':lease['lease_token'],'result':result},role)


def pipeline(client):
    course(client)
    source=complete(client,'collect',{'sources':[{'id':'s1','title':'Synthetic AND truth table','status':'complete','segments':[{'id':'line1','text':'AND is 1 only when both inputs are 1.'}]}]})
    evidence=[{'artifact_id':source['id'],'source_id':'s1','segment_id':'line1'}]
    notes=complete(client,'organize',{'summary':'AND gate','coverage':'complete','concepts':[{'id':'and','title':'AND','explanation':'Both inputs must be 1.','evidence':evidence}]})
    quiz=complete(client,'quiz',{'notes_artifact_id':notes['id'],'questions':[{'id':'q1','concept_id':'and','question':'AND(1,0)?','choices':['0','1'],'correct_index':0,'explanation':'One input is 0.','evidence':evidence}]})
    pack=complete(client,'format',{'title':'AND','quiz_artifact_id':quiz['id'],'questions':[{'id':'dq1','source_question_id':'q1','question_lines':['AND(1,0)?'],'choices':['0','1'],'correct_index':0,'explanation_lines':['Both inputs must be 1.']}]})
    return source,notes,quiz,pack


def test_auth_roles_and_no_private_files(client):
    assert client.get('/healthz').json()['model_execution'] is False
    assert client.get('/api/v1/courses').status_code==401
    assert client.post('/api/v1/courses',json={'title':'x'},headers=headers('device')).status_code==403
    for path in ('/.env','/.git/config','/hub/server.py','/backend/main.py','/assets/../backend/main.py'):
        assert client.get(path).status_code==404
    assert client.get('/').status_code==200


def test_full_pipeline_and_idempotent_attempt(client):
    source,notes,quiz,pack=pipeline(client)
    assert client.get('/api/v1/packs/'+pack['id'],headers=headers('device')).json()==pack
    assert client.get('/api/v1/artifacts/'+source['id'],headers=headers('device')).status_code==403
    attempt={'id':'try1','learner_id':'learner1','pack_id':pack['id'],'question_id':'dq1','selected_index':0,'answered_at':'2026-11-01T05:00:00Z'}
    for _ in range(2): post(client,'attempts',attempt,'device',201)
    assert len(client.get('/api/v1/attempts',headers=headers('scheduler')).json()['items'])==1
    post(client,'attempts',{**attempt,'selected_index':1},'device',409)
    assert len(client.get('/api/v1/jobs',headers=headers()).json()['items'])==4
    # Server does not invent/enqueue additional learning work.
    review=complete(client,'schedule',{'items':[{'id':'r1','learner_id':'learner1','pack_id':pack['id'],'question_id':'dq1','due_at':'2026-11-02T08:00:00+09:00','reason':'Authored by the scheduler fixture'}]})
    assert review['result']['items'][0]['due_at'].startswith('2026-11-02')


def test_wrong_role_stale_lease_and_immutable_completion(client):
    course(client);j=job(client,'collect')
    post(client,f"jobs/{j['id']}/claim",{},'organizer',403)
    lease=post(client,f"jobs/{j['id']}/claim",{},'collector')
    post(client,f"jobs/{j['id']}/claim",{},'collector',409)
    with client.app.state.store.db(True) as db: db.execute('UPDATE jobs SET lease_until=0 WHERE id=?',(j['id'],))
    result={'sources':[{'id':'blocked','title':'Private page','status':'blocked','note':'No access'}]}
    payload={'lease_token':lease['lease_token'],'result':result}
    post(client,f"jobs/{j['id']}/complete",payload,'collector',409)
    lease2=post(client,f"jobs/{j['id']}/claim",{},'collector')
    post(client,f"jobs/{j['id']}/complete",payload,'collector',403)
    payload['lease_token']=lease2['lease_token']
    a=post(client,f"jobs/{j['id']}/complete",payload,'collector')
    assert post(client,f"jobs/{j['id']}/complete",payload,'collector')['id']==a['id']
    payload['result']['sources'][0]['title']='Changed'
    post(client,f"jobs/{j['id']}/complete",payload,'collector',409)


def test_concurrent_claim_exactly_one_winner(tmp_path):
    store=Store(tmp_path/'ledger.sqlite')
    store.create_course(CourseCreate(id='c',title='Race'))
    j=store.create_job(JobCreate(kind='collect',course_id='c'))
    def claim(name):
        try: return store.claim(j['id'],{'name':name,'role':'collector'})['status']
        except Problem as e: return e.status
    with ThreadPoolExecutor(max_workers=8) as pool: results=list(pool.map(claim,map(str,range(8))))
    assert results.count('running')==1
    assert results.count(409)==7


def test_evidence_course_and_screen_bounds(client):
    source,notes,quiz,pack=pipeline(client)
    course(client,'other')
    j=job(client,'organize','other');lease=post(client,f"jobs/{j['id']}/claim",{},'organizer')
    post(client,f"jobs/{j['id']}/complete",{'lease_token':lease['lease_token'],'result':notes['result']},'organizer',422)
    j=job(client,'format');lease=post(client,f"jobs/{j['id']}/claim",{},'formatter')
    result=pack['result'];result['questions'][0]['choices'][0]='긴문장'*10
    post(client,f"jobs/{j['id']}/complete",{'lease_token':lease['lease_token'],'result':result},'formatter',422)
    result['questions'][0]['choices'][0]='0';result['questions'][0]['correct_index']=1
    post(client,f"jobs/{j['id']}/complete",{'lease_token':lease['lease_token'],'result':result},'formatter',422)


def test_partial_and_fabricated_evidence_rejected(client):
    course(client)
    s=complete(client,'collect',{'sources':[{'id':'s','title':'Partial','status':'partial','segments':[{'id':'a','text':'Some content'}]}]})
    j=job(client,'organize');lease=post(client,f"jobs/{j['id']}/claim",{},'organizer')
    body={'lease_token':lease['lease_token'],'result':{'summary':'x','coverage':'complete','concepts':[{'id':'c','title':'c','explanation':'c','evidence':[{'artifact_id':s['id'],'source_id':'s','segment_id':'a'}]}]}}
    post(client,f"jobs/{j['id']}/complete",body,'organizer',422)
    body['result']['coverage']='partial';body['result']['concepts'][0]['evidence'][0]['segment_id']='missing'
    post(client,f"jobs/{j['id']}/complete",body,'organizer',422)


def test_legacy_request_response_and_empty_context(client):
    request_id='kok_fixture';key='그록봇 빌드데이/요청/'+request_id+'.json'
    r=client.post('/api/presign/put',params={'key':key},headers=headers());assert r.status_code==200
    url=r.json()['url']
    assert client.put(url,json={'id':request_id,'text':''},headers=headers()).status_code==422
    upload=client.put(url,json={'id':request_id,'text':'Explain AND gates'},headers=headers());assert upload.status_code==200
    jid=upload.json()['job_id'];lease=post(client,f'jobs/{jid}/claim',{},'tutor')
    post(client,f'jobs/{jid}/complete',{'lease_token':lease['lease_token'],'result':{'answer':'Both inputs must be 1.'}},'tutor')
    files=client.get('/api/list',params={'prefix':'그록봇 빌드데이/결과/'},headers=headers()).json()['files']
    assert len(files)==1
    result=client.get('/api/dl',params={'key':files[0]['key']},headers=headers()).json()
    assert result['id']==request_id and result['answer']=='Both inputs must be 1.'
    assert client.post('/api/presign/put',params={'key':'../../secret'},headers=headers()).status_code==422


def test_body_limit_and_tutor_no_executable_lab(client):
    assert client.post('/api/v1/courses',content=b'x'*1_048_577,headers=headers()).status_code==413
    j=job(client,'tutor',None);lease=post(client,f"jobs/{j['id']}/claim",{},'tutor')
    post(client,f"jobs/{j['id']}/complete",{'lease_token':lease['lease_token'],'result':{'answer':'Text','lab':{'expr':'fetch(secret)'}}},'tutor',422)


def test_local_transport_persists_without_webserver(tmp_path):
    operator=LocalTransport(tmp_path,'operator','operator')
    operator.call('POST','courses',{'id':'offline','title':'Offline fixture'})
    j=operator.call('POST','jobs',{'kind':'collect','course_id':'offline'})
    collector=LocalTransport(tmp_path,'collector','collector')
    lease=collector.call('POST',f"jobs/{j['id']}/claim",{})
    a=collector.call('POST',f"jobs/{j['id']}/complete",{'lease_token':lease['lease_token'],'result':{'sources':[{'id':'s','title':'Fixture','status':'complete','segments':[{'id':'line','text':'Local-only data'}]}]}})
    reopened=LocalTransport(tmp_path,'organizer','organizer')
    assert reopened.call('GET','artifacts/'+a['id'])['result']['sources'][0]['segments'][0]['text']=='Local-only data'
    assert reopened.call('GET','jobs')['items'][0]['status']=='completed'


def test_root_path_legacy_upload_url(tmp_path):
    client=TestClient(create_app(tmp_path/'ledger.sqlite',KEYS,'/kokbot'))
    r=client.post('/api/presign/put',params={'key':'그록봇 빌드데이/요청/kok_base.json'},headers=headers())
    assert r.json()['url'].startswith('/kokbot/api/objects/')
    assert client.get('/kokbot/healthz').status_code==200
