"""Durable handoff ledger. Never browses sources, calls a model, or authors content.

The same ledger is usable directly by the local CLI without an HTTP server.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from .models import Attempt, CourseCreate, JobCreate, RESULT_MODELS, TASK_ROLES


class Problem(Exception):
    def __init__(self, status: int, message: str):
        self.status, self.message = status, message
        super().__init__(message)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS courses(id TEXT PRIMARY KEY, payload TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS jobs(
                id TEXT PRIMARY KEY, course_id TEXT, kind TEXT NOT NULL, input TEXT NOT NULL,
                status TEXT NOT NULL, created REAL NOT NULL, owner TEXT, lease_hash TEXT,
                lease_until REAL, artifact_id TEXT, error TEXT);
            CREATE INDEX IF NOT EXISTS jobs_queue ON jobs(kind,status,created);
            CREATE TABLE IF NOT EXISTS artifacts(
                id TEXT PRIMARY KEY, course_id TEXT, kind TEXT NOT NULL, job_id TEXT UNIQUE NOT NULL,
                author TEXT NOT NULL, payload TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY, payload TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS objects(key TEXT PRIMARY KEY, payload TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS tickets(id TEXT PRIMARY KEY, owner TEXT NOT NULL, key TEXT NOT NULL, expires REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0);
            ''')

    @contextmanager
    def db(self, write=False):
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            if write:
                db.execute('BEGIN IMMEDIATE')
            yield db
            if write:
                db.execute('COMMIT')
        except Exception:
            if write:
                db.execute('ROLLBACK')
            raise
        finally:
            db.close()

    def create_course(self, request: CourseCreate):
        value = request.model_dump(mode='json')
        value['id'] = value['id'] or 'course_' + uuid4().hex
        with self.db(True) as db:
            old = db.execute('SELECT payload FROM courses WHERE id=?', (value['id'],)).fetchone()
            if old and old['payload'] != encoded(value):
                raise Problem(409, 'Course ID already has different content')
            db.execute('INSERT OR IGNORE INTO courses VALUES(?,?,?)', (value['id'], encoded(value), time.time()))
        return value

    def courses(self):
        with self.db() as db:
            return [json.loads(r[0]) for r in db.execute('SELECT payload FROM courses ORDER BY created DESC LIMIT 500')]

    def create_job(self, request: JobCreate):
        value = request.model_dump(mode='json')
        value['id'] = value['id'] or 'job_' + uuid4().hex
        with self.db(True) as db:
            if value['kind'] != 'tutor' and not value['course_id']:
                raise Problem(422, 'course_id is required for this job kind')
            if value['course_id'] and not db.execute('SELECT 1 FROM courses WHERE id=?', (value['course_id'],)).fetchone():
                raise Problem(404, 'Course not found')
            old = db.execute('SELECT * FROM jobs WHERE id=?', (value['id'],)).fetchone()
            if old:
                if any(old[k] != value[k] for k in ('kind', 'course_id')) or old['input'] != encoded(value['input']):
                    raise Problem(409, 'Job ID already has different content')
                return self._job(old)
            db.execute('INSERT INTO jobs(id,course_id,kind,input,status,created) VALUES(?,?,?,?,?,?)',
                       (value['id'], value['course_id'], value['kind'], encoded(value['input']), 'queued', time.time()))
            return self._job(db.execute('SELECT * FROM jobs WHERE id=?', (value['id'],)).fetchone())

    @staticmethod
    def _job(row):
        if not row:
            raise Problem(404, 'Job not found')
        item = dict(row)
        item.pop('lease_hash', None)
        item['input'] = json.loads(item['input'])
        if item['status'] == 'running' and item['lease_until'] < time.time():
            item['status'] = 'expired'
        return item

    def job(self, job_id):
        with self.db() as db:
            return self._job(db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone())

    def jobs(self, kind=None, course_id=None):
        with self.db() as db:
            rows = db.execute('SELECT * FROM jobs WHERE (? IS NULL OR kind=?) AND (? IS NULL OR course_id=?) ORDER BY created DESC LIMIT 500',
                              (kind, kind, course_id, course_id))
            return [self._job(r) for r in rows]

    def claim(self, job_id, actor, seconds=600):
        with self.db(True) as db:
            row = db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            job = self._job(row)
            if actor['role'] != TASK_ROLES[job['kind']]:
                raise Problem(403, 'This role cannot perform this job')
            if job['status'] not in ('queued', 'expired', 'failed'):
                raise Problem(409, 'Job is already leased or completed')
            token = secrets.token_urlsafe(32)
            until = time.time() + seconds
            db.execute("UPDATE jobs SET status='running',owner=?,lease_hash=?,lease_until=?,error=NULL WHERE id=?",
                       (actor['name'], digest(token), until, job_id))
            job.update(status='running', owner=actor['name'], lease_until=until, error=None, lease_token=token)
            return job

    def _lease(self, db, job_id, actor, token, allow_completed=False):
        row = db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        job = self._job(row)
        if actor['role'] != TASK_ROLES[job['kind']] or row['owner'] != actor['name'] or not secrets.compare_digest(row['lease_hash'] or '', digest(token)):
            raise Problem(403, 'Lease does not belong to this bot')
        if allow_completed and row['status'] == 'completed':
            return row
        if row['status'] != 'running' or row['lease_until'] < time.time():
            raise Problem(409, 'Lease expired or inactive; claim again before submitting')
        return row

    def heartbeat(self, job_id, actor, token):
        with self.db(True) as db:
            self._lease(db, job_id, actor, token)
            until = time.time() + 600
            db.execute('UPDATE jobs SET lease_until=? WHERE id=?', (until, job_id))
        return {'lease_until': until}

    @staticmethod
    def _artifact(db, artifact_id, kind=None, course_id=None):
        row = db.execute('SELECT * FROM artifacts WHERE id=?', (artifact_id,)).fetchone()
        if not row:
            raise Problem(422, 'Referenced artifact does not exist')
        item = dict(row)
        item['result'] = json.loads(item.pop('payload'))
        if kind and item['kind'] != kind:
            raise Problem(422, 'Referenced artifact has wrong kind')
        if course_id is not None and item['course_id'] != course_id:
            raise Problem(422, 'Cross-course artifact references are not allowed')
        return item

    def artifact(self, artifact_id):
        with self.db() as db:
            return self._artifact(db, artifact_id)

    def artifacts(self, kind=None, course_id=None):
        with self.db() as db:
            return [dict(r) for r in db.execute('SELECT id,course_id,kind,job_id,author,created FROM artifacts WHERE (? IS NULL OR kind=?) AND (? IS NULL OR course_id=?) ORDER BY created DESC LIMIT 500',
                                                (kind, kind, course_id, course_id))]

    def _evidence(self, db, evidence, course):
        artifact = self._artifact(db, evidence['artifact_id'], 'collect', course)
        source = next((s for s in artifact['result']['sources'] if s['id'] == evidence['source_id']), None)
        if not source or source['status'] == 'blocked' or not any(s['id'] == evidence['segment_id'] for s in source['segments']):
            raise Problem(422, 'Evidence must name a readable source segment')
        return source['status']

    def _validate(self, db, kind, result, course):
        value = RESULT_MODELS[kind].model_validate(result).model_dump(mode='json')
        if kind == 'organize':
            states = [self._evidence(db, e, course) for c in value['concepts'] for e in c['evidence']]
            if value['coverage'] == 'complete' and 'partial' in states:
                raise Problem(422, 'Partial evidence cannot claim complete coverage')
        elif kind == 'quiz':
            notes = self._artifact(db, value['notes_artifact_id'], 'organize', course)['result']
            for q in value['questions']:
                if q['concept_id'] not in {c['id'] for c in notes['concepts']}:
                    raise Problem(422, 'Unknown concept ID')
                for e in q['evidence']:
                    self._evidence(db, e, course)
        elif kind == 'format':
            quiz = self._artifact(db, value['quiz_artifact_id'], 'quiz', course)['result']
            source = {q['id']: q for q in quiz['questions']}
            for q in value['questions']:
                original = source.get(q['source_question_id'])
                if not original or original['correct_index'] != q['correct_index']:
                    raise Problem(422, 'Device question must preserve the source answer index')
        elif kind == 'schedule':
            ids = set()
            for item in value['items']:
                if item['id'] in ids:
                    raise Problem(422, 'Duplicate review item ID')
                ids.add(item['id'])
                pack = self._artifact(db, item['pack_id'], 'format', course)['result']
                if item['question_id'] not in {q['id'] for q in pack['questions']}:
                    raise Problem(422, 'Review question is not in the pack')
        return value

    def complete(self, job_id, actor, token, result):
        with self.db(True) as db:
            row = self._lease(db, job_id, actor, token, allow_completed=True)
            value = self._validate(db, row['kind'], result, row['course_id'])
            payload = encoded(value)
            if row['status'] == 'completed':
                old = self._artifact(db, row['artifact_id'])
                if encoded(old['result']) != payload:
                    raise Problem(409, 'Completed result is immutable; create a new job')
                return old
            artifact_id = 'art_' + uuid4().hex
            db.execute('INSERT INTO artifacts VALUES(?,?,?,?,?,?,?)', (artifact_id, row['course_id'], row['kind'], job_id, actor['name'], payload, time.time()))
            db.execute("UPDATE jobs SET status='completed',artifact_id=? WHERE id=?", (artifact_id, job_id))
            if row['kind'] == 'tutor':
                legacy = json.loads(row['input']).get('_legacy')
                if legacy:
                    key = '그록봇 빌드데이/결과/' + legacy + '.json'
                    db.execute('INSERT OR REPLACE INTO objects VALUES(?,?,?)', (key, encoded({'id': legacy, **value}), time.time()))
            return self._artifact(db, artifact_id)

    def fail(self, job_id, actor, token, reason):
        with self.db(True) as db:
            self._lease(db, job_id, actor, token)
            db.execute("UPDATE jobs SET status='failed',error=? WHERE id=?", (reason, job_id))
        return {'status': 'failed'}

    def record_attempt(self, request: Attempt):
        value = request.model_dump(mode='json')
        with self.db(True) as db:
            pack = self._artifact(db, value['pack_id'], 'format')['result']
            if value['question_id'] not in {q['id'] for q in pack['questions']}:
                raise Problem(422, 'Question is not in this pack')
            old = db.execute('SELECT payload FROM attempts WHERE id=?', (value['id'],)).fetchone()
            if old and old[0] != encoded(value):
                raise Problem(409, 'Attempt ID already has different content')
            db.execute('INSERT OR IGNORE INTO attempts VALUES(?,?,?)', (value['id'], encoded(value), time.time()))
        return value

    def attempts(self, learner_id=None):
        with self.db() as db:
            values = [json.loads(r[0]) for r in db.execute('SELECT payload FROM attempts ORDER BY created DESC LIMIT 2000')]
        return [v for v in values if learner_id is None or v['learner_id'] == learner_id]

    def ticket(self, key, actor):
        import re
        if not re.fullmatch(r'그록봇 빌드데이/요청/[A-Za-z0-9_-]{1,79}\.json', key):
            raise Problem(422, 'Only the Kok request folder is accepted')
        token = secrets.token_urlsafe(32)
        with self.db(True) as db:
            db.execute('DELETE FROM tickets WHERE expires<?', (time.time(),))
            db.execute('INSERT INTO tickets(id,owner,key,expires) VALUES(?,?,?,?)', (token, actor['name'], key, time.time()+300))
        return token

    def upload(self, token, actor, value):
        # The upload is only a handoff. The tutor Bot must author the response.
        import re
        if not isinstance(value, dict):
            raise Problem(422, 'Request must be an object')
        request_id = value.get('id', '')
        if not isinstance(request_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,79}', request_id):
            raise Problem(422, 'Invalid request ID')
        context = [value.get(k) for k in ('transcript', 'text', 'request', 'problem')]
        if not any(str(v).strip() for v in context if v):
            raise Problem(422, 'No lecture or question content; nothing was sent to a Bot')
        with self.db(True) as db:
            ticket = db.execute('SELECT * FROM tickets WHERE id=?', (token,)).fetchone()
            if not ticket or ticket['owner'] != actor['name'] or ticket['expires'] < time.time():
                raise Problem(403, 'Upload ticket expired or belongs to another operator')
            if ticket['key'].split('/')[-1] != request_id + '.json':
                raise Problem(422, 'Request ID must match the upload filename')
            old = db.execute('SELECT payload FROM objects WHERE key=?', (ticket['key'],)).fetchone()
            if old and old[0] != encoded(value):
                raise Problem(409, 'Request ID already exists')
            db.execute('INSERT OR IGNORE INTO objects VALUES(?,?,?)', (ticket['key'], encoded(value), time.time()))
            job_id = 'tutor_' + digest(request_id)[:32]
            payload = encoded({**value, '_legacy': request_id})
            db.execute('INSERT OR IGNORE INTO jobs(id,course_id,kind,input,status,created) VALUES(?,NULL,?,?,?,?)', (job_id, 'tutor', payload, 'queued', time.time()))
            db.execute('UPDATE tickets SET used=1 WHERE id=?', (token,))
        return {'ok': True, 'job_id': job_id}

    def object(self, key):
        with self.db() as db:
            row = db.execute('SELECT payload FROM objects WHERE key=?', (key,)).fetchone()
            if not row:
                raise Problem(404, 'Object not found')
            return json.loads(row[0])

    def objects(self, prefix):
        from datetime import datetime, timezone
        with self.db() as db:
            rows = db.execute('SELECT key,created FROM objects ORDER BY created DESC LIMIT 1000')
            return [{'key': r['key'], 'uploaded': datetime.fromtimestamp(r['created'], timezone.utc).isoformat()} for r in rows if r['key'].startswith(prefix)]
