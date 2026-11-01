"""Receive, store and hand over Bot-authored collection notes. No Bot execution."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

Identifier = Annotated[str, Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$')]


class CollectedNotes(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    id: Identifier | None = None
    title: str = Field(min_length=1, max_length=200)
    source_url: HttpUrl
    coverage: Literal['complete', 'partial', 'blocked']
    content_markdown: str = Field(max_length=500_000)
    notes: str = Field(default='', max_length=5000)

    @model_validator(mode='after')
    def require_readable_content(self):
        if self.coverage != 'blocked' and not self.content_markdown:
            raise ValueError('Readable results must contain collected notes')
        if self.coverage == 'blocked' and not self.notes:
            raise ValueError('Blocked results must explain the missing access')
        return self


class BodyLimit:
    def __init__(self, app): self.app=app
    async def __call__(self, scope, receive, send):
        if scope['type']!='http': return await self.app(scope,receive,send)
        chunks=[];size=0
        while True:
            message=await receive()
            if message['type']=='http.disconnect': return
            size+=len(message.get('body',b''))
            if size>1_048_576:
                return await JSONResponse({'detail':'Request exceeds 1 MiB'},status_code=413)(scope,receive,send)
            chunks.append(message)
            if not message.get('more_body'): break
        async def replay(): return chunks.pop(0) if chunks else await receive()
        await self.app(scope,replay,send)


def create_app(db_path=None, keys=None):
    credentials=keys if keys is not None else json.loads(Path(os.environ['KOKBOT_KEYS_FILE']).read_text())
    allowed={'operator','collector','questioner'}
    if not credentials or any(r.get('role') not in allowed or len(r.get('key',''))<32 or not r.get('name') for r in credentials):
        raise RuntimeError('Configure named operator/collector/questioner keys of at least 32 characters')
    if len({r['key'] for r in credentials})!=len(credentials) or len({r['name'] for r in credentials})!=len(credentials):
        raise RuntimeError('Credential names and values must be unique')
    path=Path(db_path or os.getenv('KOKBOT_DB','/data/handoff.sqlite3'))
    path.parent.mkdir(parents=True,exist_ok=True)
    def db():
        connection=sqlite3.connect(path,timeout=15);connection.row_factory=sqlite3.Row
        return connection
    with db() as connection:
        connection.executescript('''PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS handoffs(id TEXT PRIMARY KEY,producer TEXT NOT NULL,payload TEXT NOT NULL,checksum TEXT NOT NULL,created_at TEXT NOT NULL,received_at TEXT,received_by TEXT);
        ''')
    app=FastAPI(title='콕봇 결과물 전달 API',version='1.0.0',docs_url=None,redoc_url=None)
    app.add_middleware(BodyLimit)
    def auth(request:Request):
        header=request.headers.get('authorization','');token=header[7:] if header.startswith('Bearer ') else ''
        actor=None
        for record in credentials:
            if secrets.compare_digest(token.encode(),record['key'].encode()): actor={'name':record['name'],'role':record['role']}
        if actor is None: raise HTTPException(401,'A team API key is required',headers={'WWW-Authenticate':'Bearer'})
        return actor
    def role(actor,roles):
        if actor['role'] not in roles: raise HTTPException(403,'This role cannot perform this action')
    def row(identifier):
        with db() as connection: value=connection.execute('SELECT * FROM handoffs WHERE id=?',(identifier,)).fetchone()
        if not value: raise HTTPException(404,'Result not found')
        return value
    def unpack(value,content=True):
        result=json.loads(value['payload'])
        if not content: result.pop('content_markdown',None)
        return {**result,'producer':value['producer'],'sha256':value['checksum'],'created_at':value['created_at'],
                'received_at':value['received_at'],'received_by':value['received_by']}
    @app.middleware('http')
    async def safe_headers(request,call_next):
        response=await call_next(request)
        response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',
                                 'Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'"})
        return response
    @app.get('/healthz')
    def health():
        with db() as connection: connection.execute('SELECT 1').fetchone()
        return {'status':'ok','service':'kokbot-result-handoff','revision':os.getenv('KOKBOT_REVISION','development'),'model_execution':False,'automatic_deployment':False}
    @app.get('/',response_class=HTMLResponse)
    def home():
        return '''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>콕봇 결과물 전달 API</title><style>body{font:16px/1.9 system-ui;max-width:760px;margin:60px auto;padding:24px;color:#263b30;background:#f6f4ed}code{background:#e6eadf;padding:4px 7px}a{color:#456441}</style><h1>콕봇 결과물 전달 API</h1><p>내 Grok Bot이 링크의 문제·자료를 수집하고 정리한 결과를 보관합니다.<br>용철님 Bot이 이 결과를 받아 출제와 정적 웹 생성을 맡습니다.</p><p><code>POST /api/v1/handoffs</code> 결과 등록<br><code>GET /api/v1/handoffs</code> 목록 조회<br><code>GET /api/v1/handoffs/{id}</code> 본문 조회<br><code>POST /api/v1/handoffs/{id}/ack</code> 수신 확인</p><p>모든 자료 API는 역할별 팀 키가 필요합니다. 서버가 수집·요약·출제·웹 생성을 실행하지 않습니다.</p><p><a href="https://github.com/SZARA2/kok-studyhub/blob/main/docs/API.md">연결 안내</a> · <a href="openapi.json">OpenAPI 명세</a></p></html>'''
    @app.get('/api/v1/handoffs')
    def listing(unreceived:bool=False,actor=Depends(auth)):
        with db() as connection:
            values=connection.execute('SELECT * FROM handoffs WHERE (?=0 OR received_at IS NULL) ORDER BY created_at DESC LIMIT 200',(int(unreceived),)).fetchall()
        return {'items':[unpack(v,False) for v in values]}
    @app.post('/api/v1/handoffs',status_code=201)
    def publish(body:CollectedNotes,actor=Depends(auth)):
        role(actor,{'collector','operator'})
        value=body.model_dump(mode='json');value['id']=value['id'] or 'notes_'+uuid4().hex
        payload=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
        checksum=hashlib.sha256(payload.encode()).hexdigest()
        with db() as connection:
            connection.execute('BEGIN IMMEDIATE')
            old=connection.execute('SELECT * FROM handoffs WHERE id=?',(value['id'],)).fetchone()
            if old and (old['payload']!=payload or old['producer']!=actor['name']):
                raise HTTPException(409,'Result ID already exists with different content or author; use a new ID for revisions')
            connection.execute('INSERT OR IGNORE INTO handoffs VALUES(?,?,?,?,?,NULL,NULL)',(value['id'],actor['name'],payload,checksum,datetime.now(timezone.utc).isoformat()))
        return unpack(row(value['id']))
    @app.get('/api/v1/handoffs/{identifier}')
    def read(identifier:Identifier,actor=Depends(auth)): return unpack(row(identifier))
    @app.get('/api/v1/handoffs/{identifier}/markdown',response_class=PlainTextResponse)
    def markdown(identifier:Identifier,actor=Depends(auth)):
        return PlainTextResponse(unpack(row(identifier))['content_markdown'],headers={'Content-Disposition':f'attachment; filename="{identifier}.md"'})
    @app.post('/api/v1/handoffs/{identifier}/ack')
    def acknowledge(identifier:Identifier,actor=Depends(auth)):
        role(actor,{'questioner','operator'});row(identifier)
        with db() as connection:
            connection.execute('UPDATE handoffs SET received_at=?,received_by=? WHERE id=? AND received_at IS NULL',
                               (datetime.now(timezone.utc).isoformat(),actor['name'],identifier))
        return unpack(row(identifier),False)
    return app
