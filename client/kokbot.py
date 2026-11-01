"""Use the same Grok Bot contracts over HTTPS or a local ledger without a server."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from backend.models import Attempt, CourseCreate, JobCreate, RESULT_MODELS, TASK_ROLES
from backend.store import Problem, Store


class LocalTransport:
    def __init__(self, directory, role, name):
        self.store = Store(Path(directory) / 'kokbot.sqlite3')
        self.actor = {'role': role, 'name': name}

    def call(self, method, path, body=None):
        parts = path.split('/')
        if parts[0] == 'courses':
            return self.store.create_course(CourseCreate.model_validate(body)) if method == 'POST' else {'items': self.store.courses()}
        if path == 'jobs':
            return self.store.create_job(JobCreate.model_validate(body)) if method == 'POST' else {'items': self.store.jobs()}
        if parts[0] == 'jobs' and len(parts) == 3:
            job_id, action = parts[1:]
            if action == 'claim': return self.store.claim(job_id, self.actor, body.get('lease_seconds', 600))
            if action == 'heartbeat': return self.store.heartbeat(job_id, self.actor, body['lease_token'])
            if action == 'complete': return self.store.complete(job_id, self.actor, body['lease_token'], body['result'])
            if action == 'fail': return self.store.fail(job_id, self.actor, body['lease_token'], body['reason'])
        if parts[0] in ('artifacts', 'packs') and len(parts) == 2: return self.store.artifact(parts[1])
        if path == 'artifacts': return {'items': self.store.artifacts()}
        if path == 'attempts':
            return self.store.record_attempt(Attempt.model_validate(body)) if method == 'POST' else {'items': self.store.attempts()}
        raise ValueError('Unsupported local operation: ' + path)


class HttpTransport:
    def __init__(self, url, key):
        from urllib.parse import urlsplit
        parsed = urlsplit(url)
        if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1', '::1')):
            raise ValueError('Use HTTPS, or HTTP on loopback only')
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Base URL must not contain credentials, query or fragment')
        if not key:
            raise ValueError('Set KOKBOT_KEY in the Bot environment; never put it in a public template')
        self.url, self.key = url.rstrip('/') + '/api/v1/', key

    def call(self, method, path, body=None):
        import httpx
        response = httpx.request(method, self.url + path, json=body,
                                headers={'Authorization': 'Bearer ' + self.key}, timeout=30, follow_redirects=False)
        if not response.is_success:
            raise Problem(response.status_code, response.text[:2000])
        return response.json()


def private_write(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
    target.chmod(0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local', help='Local shared directory; no network or server process')
    parser.add_argument('--role', choices=['operator', 'device', *TASK_ROLES.values()], default='operator')
    parser.add_argument('--name', default='local-bot')
    parser.add_argument('--url', default=os.getenv('KOKBOT_URL'))
    parser.add_argument('command', choices=['course','enqueue','courses','jobs','artifacts','claim','heartbeat','complete','fail','get','attempt','attempts','schema'])
    parser.add_argument('id', nargs='?')
    parser.add_argument('--file')
    parser.add_argument('--out')
    parser.add_argument('--lease-file')
    parser.add_argument('--kind', choices=list(TASK_ROLES))
    args = parser.parse_args()
    if args.command == 'schema':
        if args.kind not in RESULT_MODELS: parser.error('--kind is required')
        result = RESULT_MODELS[args.kind].model_json_schema()
    else:
        if not args.local and not args.url: parser.error('Set --local DIRECTORY or KOKBOT_URL / --url')
        transport = LocalTransport(args.local, args.role, args.name) if args.local else HttpTransport(args.url, os.getenv('KOKBOT_KEY', ''))
        body = json.loads(Path(args.file).read_text(encoding='utf-8-sig')) if args.file else None
        if args.command in ('course', 'enqueue', 'attempt'):
            if body is None: parser.error('--file is required')
            result = transport.call('POST', {'course':'courses','enqueue':'jobs','attempt':'attempts'}[args.command], body)
        elif args.command in ('courses','jobs','artifacts','attempts'):
            result = transport.call('GET', args.command)
            if args.kind: result['items'] = [x for x in result['items'] if x.get('kind') == args.kind]
        elif args.command == 'get':
            if not args.id: parser.error('Artifact ID is required')
            result = transport.call('GET','artifacts/'+args.id)
        else:
            if not args.id or not args.lease_file: parser.error('Job ID and --lease-file are required')
            if args.command == 'claim':
                result = transport.call('POST',f'jobs/{args.id}/claim',{})
                private_write(args.lease_file, {'job_id':args.id,'lease_token':result.pop('lease_token')})
            else:
                lease = json.loads(Path(args.lease_file).read_text(encoding='utf-8'))
                if lease['job_id'] != args.id: parser.error('Lease belongs to a different job')
                payload = {'lease_token':lease['lease_token']}
                if args.command == 'complete':
                    if body is None: parser.error('Bot-authored result --file is required')
                    payload['result'] = body
                if args.command == 'fail':
                    if not body or not body.get('reason'): parser.error('--file containing reason is required')
                    payload['reason'] = body['reason']
                result = transport.call('POST',f'jobs/{args.id}/{args.command}',payload)
    if args.out: private_write(args.out, result)
    else: print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    try:
        main()
    except (Problem, ValueError, OSError) as exc:
        raise SystemExit(str(exc))
