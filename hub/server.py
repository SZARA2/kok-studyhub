# -*- coding: utf-8 -*-
"""통합 공부판 로컬 서버 (2026-10-15 노트북)
실행: python server.py   (표준 라이브러리만)  → http://localhost:8626/
- G:\\내 드라이브 전체를 읽기 전용으로 보여 준다 (127.0.0.1 에만 열림, 외부 접속 불가)
- 쓰기는 이 폴더(통합공부판) 안의 data\\, 추가자료\\ 에만 한다
API
  GET  /api/meta                     과목 카드 목록·계획·퀴즈 (원본 파일에서 바로 읽음, 다시 생성할 필요 없음)
  GET  /api/extras                   추가자료 파일 목록 + 링크 + 메모
  POST /api/upload?sub=dg&name=x     파일 올리기 (추가자료\\dg\\x)
  POST /api/delete?sub=dg&name=x     추가자료 파일 지우기 (휴지통 폴더로 이동)
  POST /api/links                    링크 목록 저장 (data\\links.json)
  POST /api/memo?sub=dg              과목 메모 저장 (data\\memo_dg.md)
  POST /api/lsbackup                 브라우저 기록 백업 (data\\ls_backup.json)
  POST /api/lsimport                 file:// 로 쓰던 기록 옮기기 (data\\ls_import.json)
"""
import json, os, re, sys, time, html as H, urllib.parse, mimetypes, shutil, socket, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get('KW_HUB_PORT', '8626'))
if sys.stdout is None or sys.stderr is None:   # pythonw (창 없이 실행) 대비
    _null = open(os.devnull, 'w', encoding='utf-8')
    sys.stdout = sys.stdout or _null
    sys.stderr = sys.stderr or _null
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))   # G:\내 드라이브
HUB_URL = '/' + os.path.relpath(HERE, ROOT).replace(os.sep, '/') + '/'
DATA = os.path.join(HERE, 'data')
EXTRA = os.path.join(HERE, '추가자료')
TRASH = os.path.join(HERE, 'data', '_지운자료')
for d in (DATA, EXTRA, TRASH):
    os.makedirs(d, exist_ok=True)

mimetypes.add_type('text/markdown', '.md')
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('audio/wav', '.wav')
mimetypes.add_type('audio/mp4', '.m4a')
TEXTLIKE = ('.md', '.txt', '.json', '.js', '.css', '.html', '.htm', '.csv', '.py', '.log')

def rd(p):
    with open(p, encoding='utf-8-sig') as f:
        return f.read()

def strip_tags(s):
    return re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]*>', ' ', str(s or '')))).strip()

def upath(u):
    """/광운대학교/... → G:\\내 드라이브\\광운대학교\\...  (ROOT 밖이면 None)"""
    u = urllib.parse.unquote(u.split('?', 1)[0].split('#', 1)[0])
    p = os.path.abspath(os.path.join(ROOT, u.lstrip('/').replace('/', os.sep)))
    if os.path.normcase(p) != os.path.normcase(ROOT) and not os.path.normcase(p).startswith(os.path.normcase(ROOT) + os.sep):
        return None
    return p

def safe_name(n):
    n = os.path.basename(str(n or '').replace('\\', '/'))
    n = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', n).strip(' .')
    return n[:150] or ('file_' + time.strftime('%H%M%S'))

def safe_sub(s):
    s = re.sub(r'[^\w-]', '', str(s or 'common'))
    return s or 'common'

# ---------------- 메타 (원본에서 바로 읽기, 파일 수정 시각으로 캐시) ----------------
_cache = {}
def cached(key, paths, fn):
    sig = tuple((p, os.path.getmtime(p) if os.path.exists(p) else 0) for p in paths)
    c = _cache.get(key)
    if c and c[0] == sig:
        return c[1]
    v = fn()
    _cache[key] = (sig, v)
    return v

def board_info(path):
    doc = rd(path)
    m = re.search(r'<script type="application/json" id="([\w-]+-data)">([\s\S]*?)</script>', doc)
    data = json.loads(m.group(2)) if m else []
    cfg = re.search(r"subj:\s*'([^']+)',\s*name:\s*'([^']+)',\s*workPrefix:\s*'([^']+)',\s*mockMin:\s*(\d+)", doc)
    lst = []
    for c in data:
        cid = c.get('id') or ('q' + str(c.get('q')))
        lab = c.get('label') or ((str(c['no']) + '. ' if c.get('no') is not None else '') + str(c.get('topic') or c.get('title') or cid))
        lst.append([cid, strip_tags(lab)[:90], 1 if c.get('info') else 0, 1 if (c.get('new1015') or c.get('prof7') or c.get('new')) else 0])
    return dict(cards=lst, subj=cfg.group(1) if cfg else '', workPrefix=cfg.group(3) if cfg else '', mockMin=int(cfg.group(4)) if cfg else 120)

def quiz_info(path):
    hub = rd(path)
    i = hub.find('const QUIZ = ')
    if i < 0:
        return []
    Q, _ = json.JSONDecoder().raw_decode(hub[i + len('const QUIZ = '):])
    return [[q['id'], q.get('s', ''), strip_tags(q.get('f', ''))[:80]] for q in Q]

def build_meta():
    cfgp = os.path.join(HERE, 'config.json')
    cfg = json.loads(rd(cfgp))
    out = dict(config=cfg, cards={}, boards={}, quiz=[], plan=[], files={}, errors=[], hub=HUB_URL, built=time.strftime('%Y-%m-%d %H:%M:%S'))
    for s in cfg.get('subjects', []):
        k = s['key']
        try:
            if s.get('kind') == 'board':
                p = upath(s['file'])
                b = cached('b:' + k, [p], lambda p=p: board_info(p))
                out['cards'][k] = b['cards']
                out['boards'][k] = dict(subj=b['subj'], workPrefix=b['workPrefix'], mockMin=b['mockMin'])
                out['files'][k] = dict(mtime=os.path.getmtime(p), size=os.path.getsize(p))
            elif s.get('kind') == 'quiz':
                p = upath(s['file'])
                out['quiz'] = cached('quiz', [p], lambda p=p: quiz_info(p))
                out['files'][k] = dict(mtime=os.path.getmtime(p), size=os.path.getsize(p))
            elif s.get('kind') == 'hack':
                p = upath(s['file'])
                out['files'][k] = dict(mtime=os.path.getmtime(p), size=os.path.getsize(p))
        except Exception as e:
            out['errors'].append(k + ': ' + repr(e))
    try:
        p = upath(cfg['plan'])
        out['plan'] = cached('plan', [p], lambda p=p: json.loads(rd(p)))
        out['files']['plan'] = dict(mtime=os.path.getmtime(p))
    except Exception as e:
        out['errors'].append('plan: ' + repr(e))
    return out

def list_extras():
    files = {}
    for sub in sorted(os.listdir(EXTRA)):
        d = os.path.join(EXTRA, sub)
        if not os.path.isdir(d):
            continue
        arr = []
        for root, _, fs in os.walk(d):
            for f in fs:
                if f.startswith('.') or f.lower() == 'desktop.ini':
                    continue
                p = os.path.join(root, f)
                rel = os.path.relpath(p, ROOT).replace(os.sep, '/')
                arr.append(dict(name=os.path.relpath(p, d).replace(os.sep, '/'), url='/' + rel, size=os.path.getsize(p), mtime=os.path.getmtime(p)))
        arr.sort(key=lambda x: -x['mtime'])
        files[sub] = arr
    links = []
    lp = os.path.join(DATA, 'links.json')
    if os.path.exists(lp):
        try:
            links = json.loads(rd(lp))
        except Exception:
            links = []
    memos = {}
    for f in os.listdir(DATA):
        m = re.match(r'memo_([\w-]+)\.md$', f)
        if m:
            memos[m.group(1)] = rd(os.path.join(DATA, f))
    return dict(files=files, links=links, memos=memos)

def write_atomic(p, data):
    tmp = p + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(data)
    os.replace(tmp, p)

# ---------------- HTTP ----------------
class H_(BaseHTTPRequestHandler):
    server_version = 'KwHub/1.0'

    def log_message(self, fmt, *a):
        pass

    def cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def j(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(b)))
        self.send_header('Cache-Control', 'no-store')
        self.cors()
        self.end_headers()
        self.wfile.write(b)

    def do_OPTIONS(self):
        self.send_response(204)
        self.cors()
        self.end_headers()

    def body(self):
        n = int(self.headers.get('Content-Length') or 0)
        return self.rfile.read(n) if n else b''

    def q(self):
        return {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).items()}

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path in ('/', '/hub', '/hub/'):
            self.send_response(302)
            self.send_header('Location', urllib.parse.quote(HUB_URL))
            self.end_headers()
            return
        if path == '/api/ping':
            return self.j(dict(ok=True, hub=HUB_URL, root=ROOT, host=socket.gethostname()))
        if path == '/api/meta':
            try:
                return self.j(build_meta())
            except Exception as e:
                return self.j(dict(error=repr(e)), 500)
        if path == '/api/extras':
            return self.j(list_extras())
        if path == '/api/lsimport':
            p = os.path.join(DATA, 'ls_import.json')
            return self.j(json.loads(rd(p)) if os.path.exists(p) else {})
        if path == '/api/lsbackup':
            p = os.path.join(DATA, 'ls_backup_' + safe_sub(socket.gethostname()) + '.json')
            return self.j(json.loads(rd(p)) if os.path.exists(p) else {})
        self.serve_file(path)

    def serve_file(self, path):
        p = upath(path)
        if p and os.path.isdir(p):
            if not path.endswith('/'):
                self.send_response(301)
                self.send_header('Location', urllib.parse.quote(urllib.parse.unquote(path) + '/'))
                self.end_headers()
                return
            idx = os.path.join(p, 'index.html')
            if os.path.exists(idx):
                p = idx
            else:
                items = sorted(os.listdir(p))
                h = '<meta charset="utf-8"><h3>' + H.escape(urllib.parse.unquote(path)) + '</h3><ul>' + ''.join('<li><a href="' + urllib.parse.quote(n) + ('/' if os.path.isdir(os.path.join(p, n)) else '') + '">' + H.escape(n) + '</a></li>' for n in items) + '</ul>'
                b = h.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(b)))
                self.end_headers()
                self.wfile.write(b)
                return
        if not p or not os.path.isfile(p):
            b = ('없는 파일: ' + urllib.parse.unquote(path)).encode('utf-8')
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return
        ctype = mimetypes.guess_type(p)[0] or 'application/octet-stream'
        if os.path.splitext(p)[1].lower() in TEXTLIKE:
            ctype = (ctype if ctype != 'text/markdown' else 'text/plain') + '; charset=utf-8'
        size = os.path.getsize(p)
        rng = self.headers.get('Range')
        start, end = 0, size - 1
        code = 200
        if rng:
            m = re.match(r'bytes=(\d*)-(\d*)', rng)
            if m:
                if m.group(1):
                    start = int(m.group(1))
                    if m.group(2):
                        end = min(int(m.group(2)), size - 1)
                elif m.group(2):
                    start = max(0, size - int(m.group(2)))
                code = 206
        if start > end and size:
            self.send_response(416)
            self.send_header('Content-Range', 'bytes */%d' % size)
            self.end_headers()
            return
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(end - start + 1 if size else 0))
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Last-Modified', time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(os.path.getmtime(p))))
        if code == 206:
            self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, end, size))
        self.cors()
        self.end_headers()
        if self.command == 'HEAD' or not size:
            return
        try:
            with open(p, 'rb') as f:
                f.seek(start)
                left = end - start + 1
                while left > 0:
                    chunk = f.read(min(1 << 20, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            pass

    def do_HEAD(self):
        self.serve_file(urllib.parse.urlsplit(self.path).path)

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        q = self.q()
        try:
            if path == '/api/upload':
                sub = safe_sub(q.get('sub'))
                d = os.path.join(EXTRA, sub)
                os.makedirs(d, exist_ok=True)
                name = safe_name(q.get('name'))
                p = os.path.join(d, name)
                base, ext = os.path.splitext(name)
                i = 2
                while os.path.exists(p):
                    p = os.path.join(d, '%s (%d)%s' % (base, i, ext))
                    i += 1
                write_atomic(p, self.body())
                return self.j(dict(ok=True, url='/' + os.path.relpath(p, ROOT).replace(os.sep, '/'), name=os.path.basename(p)))
            if path == '/api/delete':
                sub = safe_sub(q.get('sub'))
                name = str(q.get('name') or '').replace('\\', '/')
                p = os.path.abspath(os.path.join(EXTRA, sub, name.replace('/', os.sep)))
                if not os.path.normcase(p).startswith(os.path.normcase(os.path.join(EXTRA, sub)) + os.sep) or not os.path.isfile(p):
                    return self.j(dict(error='bad path'), 400)
                dst = os.path.join(TRASH, time.strftime('%m%d_%H%M%S_') + os.path.basename(p))
                shutil.move(p, dst)
                return self.j(dict(ok=True))
            if path == '/api/links':
                data = json.loads(self.body().decode('utf-8') or '[]')
                write_atomic(os.path.join(DATA, 'links.json'), json.dumps(data, ensure_ascii=False, indent=1).encode('utf-8'))
                return self.j(dict(ok=True))
            if path == '/api/memo':
                sub = safe_sub(q.get('sub'))
                write_atomic(os.path.join(DATA, 'memo_' + sub + '.md'), self.body())
                return self.j(dict(ok=True))
            if path == '/api/lsbackup':
                data = json.loads(self.body().decode('utf-8') or '{}')
                p = os.path.join(DATA, 'ls_backup_' + safe_sub(socket.gethostname()) + '.json')
                write_atomic(p, json.dumps(dict(at=time.strftime('%Y-%m-%d %H:%M:%S'), host=socket.gethostname(), data=data), ensure_ascii=False).encode('utf-8'))
                return self.j(dict(ok=True, n=len(data)))
            if path == '/api/lsimport':
                data = json.loads(self.body().decode('utf-8') or '{}')
                write_atomic(os.path.join(DATA, 'ls_import.json'), json.dumps(dict(at=time.strftime('%Y-%m-%d %H:%M:%S'), data=data), ensure_ascii=False).encode('utf-8'))
                return self.j(dict(ok=True, n=len(data)))
        except Exception as e:
            return self.j(dict(error=repr(e)), 500)
        self.j(dict(error='unknown api'), 404)

def main():
    try:
        s = socket.create_connection(('127.0.0.1', PORT), timeout=0.5)
        s.close()
        print('이미 켜져 있음: http://localhost:%d/' % PORT)
        return
    except OSError:
        pass
    srv = ThreadingHTTPServer(('127.0.0.1', PORT), H_)
    srv.daemon_threads = True
    print('통합 공부판 서버: http://localhost:%d/  (ROOT=%s)' % (PORT, ROOT))
    sys.stdout.flush()
    srv.serve_forever()

if __name__ == '__main__':
    main()
