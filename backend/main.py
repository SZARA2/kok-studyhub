from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.staticfiles import StaticFiles

from .models import (Attempt, ClaimRequest, CompleteRequest, CourseCreate, FailRequest,
                     JobCreate, LeaseRequest, TASK_ROLES)
from .store import Problem, Store

ROOT = Path(__file__).resolve().parent.parent
MAX_BODY = 1_048_576
READERS = {'operator', 'device', *TASK_ROLES.values()}
WRITERS = {'operator', *TASK_ROLES.values()}


class BodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        chunks, size = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            size += len(message.get('body', b''))
            if size > MAX_BODY:
                return await JSONResponse({'detail': 'Request exceeds 1 MiB'}, status_code=413)(scope, receive, send)
            chunks.append(message)
            if not message.get('more_body', False):
                break
        async def replay():
            if chunks:
                return chunks.pop(0)
            return await receive()
        await self.app(scope, replay, send)


def load_keys(path):
    records = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(records, list) or not records:
        raise RuntimeError('At least one named credential is required')
    names, keys = set(), set()
    for r in records:
        if set(r) != {'name', 'role', 'key'} or r['role'] not in READERS or len(r['key']) < 32:
            raise RuntimeError('Invalid credential file; see docs/OPERATIONS.md')
        if r['name'] in names or r['key'] in keys:
            raise RuntimeError('Credential names and keys must be unique')
        names.add(r['name']); keys.add(r['key'])
    return records


def create_app(db_path=None, keys=None, base_path=None):
    base = (base_path if base_path is not None else os.getenv('KOKBOT_BASE_PATH', '')).rstrip('/')
    if base and (not base.startswith('/') or '..' in base):
        raise RuntimeError('Invalid base path')
    credentials = keys if keys is not None else load_keys(os.environ['KOKBOT_KEYS_FILE'])
    if not credentials:
        raise RuntimeError('Empty credential set is not permitted')
    store = Store(db_path or os.getenv('KOKBOT_DB', '/data/kokbot.sqlite3'))
    app = FastAPI(title='Kokbot Handoff API', version='1.0.0', root_path=base,
                  description='Storage, validation and handoff only. All learning content is authored by independent Grok Bots.',
                  docs_url=None, redoc_url=None, openapi_url='/openapi.json')
    app.state.store = store
    app.add_middleware(BodyLimit)
    origins = [s.strip() for s in os.getenv('KOKBOT_CORS_ORIGINS', '').split(',') if s.strip()]
    if '*' in origins:
        raise RuntimeError('Use explicit CORS origins')
    if origins:
        app.add_middleware(CORSMiddleware, allow_origins=origins,
                           allow_methods=['GET', 'POST', 'PUT'], allow_headers=['Authorization', 'Content-Type'])

    bearer = HTTPBearer(auto_error=False)

    def auth(credential: HTTPAuthorizationCredentials | None = Depends(bearer)):
        token = credential.credentials if credential else ''
        found = None
        for record in credentials:
            if secrets.compare_digest(token.encode(), record['key'].encode()):
                found = {'name': record['name'], 'role': record['role']}
        if found is None:
            raise HTTPException(401, 'A valid team key is required', headers={'WWW-Authenticate': 'Bearer'})
        return found

    def roles(allowed):
        def require(actor=Depends(auth)):
            if actor['role'] not in allowed:
                raise HTTPException(403, 'This role is not allowed for this action')
            return actor
        return require

    @app.middleware('http')
    async def headers(request, call_next):
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Cache-Control'] = 'no-store' if '/api/' in request.url.path else 'no-cache'
        # Legacy examples contain inline scripts. API results are never executed.
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'"
        return response

    @app.exception_handler(Problem)
    async def problem_handler(request, exc):
        return JSONResponse({'detail': exc.message}, status_code=exc.status)

    @app.exception_handler(ValidationError)
    async def validation_handler(request, exc):
        # Do not reflect input data or credentials in error output.
        return JSONResponse({'detail': [{'loc': e['loc'], 'msg': e['msg'], 'type': e['type']} for e in exc.errors()]}, status_code=422)

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request, exc):
        return JSONResponse({'detail': [{'loc': e['loc'], 'msg': e['msg'], 'type': e['type']} for e in exc.errors()]}, status_code=422)

    @app.get('/healthz')
    def health():
        with store.db() as db:
            db.execute('SELECT 1').fetchone()
        return {'status': 'ok', 'service': 'kokbot-handoff', 'revision': os.getenv('KOKBOT_REVISION', 'development'), 'model_execution': False}

    @app.get('/api/v1/me')
    def me(actor=Depends(auth)):
        return actor

    @app.get('/api/v1/courses')
    def courses(actor=Depends(roles(READERS))):
        return {'items': store.courses()}

    @app.post('/api/v1/courses', status_code=201)
    def create_course(body: CourseCreate, actor=Depends(roles(WRITERS))):
        return store.create_course(body)

    @app.get('/api/v1/jobs')
    def jobs(kind: str | None = None, course_id: str | None = None, actor=Depends(roles(WRITERS))):
        return {'items': store.jobs(kind, course_id)}

    @app.post('/api/v1/jobs', status_code=201)
    def create_job(body: JobCreate, actor=Depends(roles(WRITERS))):
        return store.create_job(body)

    @app.get('/api/v1/jobs/{job_id}')
    def job(job_id: str, actor=Depends(roles(WRITERS))):
        return store.job(job_id)

    @app.post('/api/v1/jobs/{job_id}/claim')
    def claim(job_id: str, body: ClaimRequest, actor=Depends(roles(set(TASK_ROLES.values())))):
        return store.claim(job_id, actor, body.lease_seconds)

    @app.post('/api/v1/jobs/{job_id}/heartbeat')
    def heartbeat(job_id: str, body: LeaseRequest, actor=Depends(roles(set(TASK_ROLES.values())))):
        return store.heartbeat(job_id, actor, body.lease_token)

    @app.post('/api/v1/jobs/{job_id}/complete')
    def complete(job_id: str, body: CompleteRequest, actor=Depends(roles(set(TASK_ROLES.values())))):
        return store.complete(job_id, actor, body.lease_token, body.result)

    @app.post('/api/v1/jobs/{job_id}/fail')
    def fail(job_id: str, body: FailRequest, actor=Depends(roles(set(TASK_ROLES.values())))):
        return store.fail(job_id, actor, body.lease_token, body.reason)

    @app.get('/api/v1/artifacts')
    def artifacts(kind: str | None = None, course_id: str | None = None, actor=Depends(roles(READERS))):
        if actor['role'] == 'device' and kind not in ('format', 'react', 'schedule'):
            raise HTTPException(403, 'Device may list only format, react or schedule artifacts')
        return {'items': store.artifacts(kind, course_id)}

    @app.get('/api/v1/artifacts/{artifact_id}')
    def artifact(artifact_id: str, actor=Depends(roles(READERS))):
        value = store.artifact(artifact_id)
        if actor['role'] == 'device' and value['kind'] not in ('format', 'react', 'schedule'):
            raise HTTPException(403, 'Device may read only presentation artifacts')
        return value

    @app.get('/api/v1/packs/{pack_id}')
    def pack(pack_id: str, actor=Depends(roles(READERS))):
        value = store.artifact(pack_id)
        if value['kind'] != 'format':
            raise HTTPException(404, 'Learning pack not found')
        return value

    @app.post('/api/v1/attempts', status_code=201)
    def attempt(body: Attempt, actor=Depends(roles({'operator', 'device'}))):
        return store.record_attempt(body)

    @app.get('/api/v1/attempts')
    def attempts(learner_id: str | None = None, actor=Depends(roles(WRITERS))):
        return {'items': store.attempts(learner_id)}

    # Compatibility adapter for the original Kok screen. No filesystem paths.
    @app.get('/api/lockstate')
    def lockstate(actor=Depends(roles(WRITERS))):
        return {'locked': False}

    @app.post('/api/presign/put')
    def presign(key: str, actor=Depends(roles({'operator'}))):
        return {'url': base + '/api/objects/' + store.ticket(key, actor)}

    @app.put('/api/objects/{token}')
    async def upload(token: str, request: Request, actor=Depends(roles({'operator'}))):
        try:
            payload = await request.json()
        except ValueError:
            raise HTTPException(422, 'Invalid JSON')
        return store.upload(token, actor, payload)

    @app.post('/api/done')
    def done(body: dict, actor=Depends(roles({'operator'}))):
        store.object(body.get('key', ''))
        return {'ok': True}

    @app.get('/api/list')
    def listing(prefix: str = '', actor=Depends(roles(WRITERS))):
        return {'files': store.objects(prefix)}

    @app.get('/api/dl')
    def download(key: str, actor=Depends(roles(WRITERS))):
        return store.object(key)

    @app.get('/', response_class=HTMLResponse)
    def home():
        return (ROOT / 'web/index.html').read_text(encoding='utf-8')

    @app.get('/docs', response_class=HTMLResponse)
    def docs():
        return '<!doctype html><meta charset="utf-8"><title>Kokbot API</title><h1>Kokbot Handoff API</h1><p>Bearer 인증 · 단일 팀 작업 공간 · 모델 호출 없음</p><p><a href="openapi.json">OpenAPI JSON</a> · <a href="https://github.com/SZARA2/kok-studyhub/blob/main/docs/API.md">API 연결 안내</a></p>'

    app.mount('/assets', StaticFiles(directory=ROOT / 'web'), name='assets')
    # Publish only explicit source assets, never Python/configuration/runtime files.
    @app.get('/kok/{name:path}')
    def legacy_kok(name: str):
        allowed = {'index.html', 'lab.html', 'clip.json', 'example_result.json', 'spec.json', 'spec_rc.json', 'spec_bfield.json', 'lib/three.min.js'}
        name = name or 'index.html'
        if name not in allowed:
            raise HTTPException(404)
        return FileResponse(ROOT / 'kok' / name)

    @app.get('/hub/{name:path}')
    def legacy_hub(name: str):
        allowed = {'index.html', 'app.js', 'app.css', 'tex2mml.js', 'config.json', 'meta.json'}
        name = name or 'index.html'
        if name not in allowed:
            raise HTTPException(404)
        return FileResponse(ROOT / 'hub' / name)

    return app
