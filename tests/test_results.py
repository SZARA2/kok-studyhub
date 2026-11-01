import pytest
from fastapi.testclient import TestClient
from backend.handoff import create_app

KEYS=[{'name':r,'role':r,'key':'test-only-'+r+'x'*32} for r in ('operator','collector','questioner')]
def headers(role):return {'Authorization':'Bearer '+next(r['key'] for r in KEYS if r['role']==role)}
@pytest.fixture
def client(tmp_path):return TestClient(create_app(tmp_path/'handoff.sqlite3',KEYS))
def sample():return {'id':'notes1','title':'Synthetic fixture','source_url':'https://example.com/lecture','coverage':'partial','content_markdown':'# Read scope\nOnly the supplied sample text.','notes':'Synthetic test, not a real collected lecture.'}
def test_result_handoff_without_jobs_or_generation(client):
    r=client.post('/api/v1/handoffs',json=sample(),headers=headers('collector'));assert r.status_code==201
    value=r.json();assert value['producer']=='collector' and len(value['sha256'])==64
    assert client.get('/api/v1/handoffs/notes1',headers=headers('questioner')).json()['content_markdown']==sample()['content_markdown']
    assert client.get('/api/v1/handoffs/notes1/markdown',headers=headers('questioner')).text==sample()['content_markdown']
    assert client.post('/api/v1/handoffs/notes1/ack',headers=headers('collector')).status_code==403
    received=client.post('/api/v1/handoffs/notes1/ack',headers=headers('questioner')).json()
    assert received['received_by']=='questioner'
    assert client.post('/api/v1/handoffs/notes1/ack',headers=headers('questioner')).json()==received
    assert client.get('/api/v1/handoffs?unreceived=true',headers=headers('questioner')).json()['items']==[]
    assert client.get('/api/v1/jobs',headers=headers('operator')).status_code==404
def test_auth_and_immutable_ids(client):
    assert client.get('/api/v1/handoffs').status_code==401
    assert client.post('/api/v1/handoffs',json=sample(),headers=headers('questioner')).status_code==403
    for _ in range(2):assert client.post('/api/v1/handoffs',json=sample(),headers=headers('collector')).status_code==201
    assert len(client.get('/api/v1/handoffs',headers=headers('questioner')).json()['items'])==1
    changed={**sample(),'content_markdown':'Changed'}
    assert client.post('/api/v1/handoffs',json=changed,headers=headers('collector')).status_code==409
def test_partial_blocked_and_size(client):
    missing={**sample(),'content_markdown':''}
    assert client.post('/api/v1/handoffs',json=missing,headers=headers('collector')).status_code==422
    assert client.post('/api/v1/handoffs',json={**missing,'coverage':'blocked'},headers=headers('collector')).status_code==201
    assert client.post('/api/v1/handoffs',content=b'x'*1_048_577,headers=headers('collector')).status_code==413
def test_public_metadata_but_no_files_or_web_generator(client):
    health=client.get('/healthz').json();assert health['model_execution'] is False and health['automatic_deployment'] is False
    assert client.get('/').status_code==200
    for path in ('/.env','/.git/config','/hub/server.py','/assets/example.html','/workspace'):
        assert client.get(path).status_code==404
def test_persistence(tmp_path):
    path=tmp_path/'ledger.sqlite3'
    first=TestClient(create_app(path,KEYS));first.post('/api/v1/handoffs',json=sample(),headers=headers('collector'))
    second=TestClient(create_app(path,KEYS));assert second.get('/api/v1/handoffs/notes1',headers=headers('questioner')).json()['id']=='notes1'
