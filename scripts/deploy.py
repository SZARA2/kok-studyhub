#!/usr/bin/env python3
"""Pull tested main commits on the deployment host. Never used as a PR runner.

Host-specific paths live in a private config.json outside this repository.
Only a narrow named Caddy route is added. Existing services are not restarted.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import time
import urllib.request
from pathlib import Path


def run(*args, capture=True, input=None):
    result = subprocess.run(args, input=input, text=True, stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.PIPE if capture else None, check=False)
    if result.returncode:
        # Config/credential content is never logged; command names and bounded errors only.
        raise RuntimeError(f'{args[0]} failed ({result.returncode}): '+(result.stderr or '')[-1500:])
    return result.stdout.strip() if capture else ''


def request_json(url):
    request=urllib.request.Request(url,headers={'Accept':'application/vnd.github+json','User-Agent':'kokbot-pull-deploy'})
    with urllib.request.urlopen(request,timeout=20) as response:
        return json.load(response)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_in_place(path, content):
    # Existing Caddy config is a single-file bind mount: preserve its inode.
    with open(path,'wb') as file:
        file.write(content);file.flush();os.fsync(file.fileno())


def route(host, prefix, container):
    return {'@id':'kokbot-public-route','match':[{'host':[host],'path':[prefix,prefix+'/*']}],
            'handle':[{'handler':'subroute','routes':[
                {'match':[{'path':[prefix]}],'handle':[{'handler':'static_response','headers':{'Location':[prefix+'/']},'status_code':308}]},
                {'handle':[{'handler':'rewrite','strip_path_prefix':prefix},
                           {'handler':'reverse_proxy','upstreams':[{'dial':container+':8080'}]}]}
            ]}],'terminal':True}


def deploy(root):
    cfg=json.loads((root/'config.json').read_text())
    owner_repo=cfg['repository']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',owner_repo):
        raise ValueError('Invalid repository')
    checkout=root/'checkout'
    if not (checkout/'.git').exists():
        run('git','clone','--no-checkout','https://github.com/'+owner_repo+'.git',str(checkout))
    run('git','-C',str(checkout),'fetch','--prune','origin','main')
    revision=run('git','-C',str(checkout),'rev-parse','origin/main')
    if not re.fullmatch(r'[a-f0-9]{40}',revision): raise ValueError('Invalid revision')
    state_path=root/'state.json'
    old_state=json.loads(state_path.read_text()) if state_path.exists() else {}
    if old_state.get('revision')==revision:
        print('Already deployed '+revision[:12]);return
    runs=request_json('https://api.github.com/repos/'+owner_repo+'/actions/workflows/ci.yml/runs?branch=main&event=push&head_sha='+revision+'&per_page=20')['workflow_runs']
    matching=[r for r in runs if r['head_sha']==revision and r['event']=='push' and r['head_branch']=='main']
    matching.sort(key=lambda r:r['id'],reverse=True)
    if not matching or matching[0]['conclusion']!='success':
        print('Waiting for successful main CI at '+revision[:12]);return
    run('git','-C',str(checkout),'checkout','--detach',revision)
    image='kokbot:'+revision[:12]
    run('docker','build','--build-arg','REVISION='+revision,'-t',image,str(checkout),capture=False)
    candidate='kokbot-'+revision[:12]
    existing=run('docker','ps','-a','--filter','name=^/'+candidate+'$','--format','{{.Names}}')
    if existing:
        if old_state.get('container')==candidate: raise RuntimeError('Candidate is the current live container')
        run('docker','rm','-f',candidate)
    data=root/'data';data.mkdir(exist_ok=True,mode=0o700)
    database=data/'kokbot.sqlite3'
    if database.exists():
        backups=root/'backups';backups.mkdir(exist_ok=True,mode=0o700)
        snapshot=backups/(str(int(time.time()))+'.sqlite3')
        with sqlite3.connect(f'file:{database}?mode=ro',uri=True) as source, sqlite3.connect(snapshot) as target:
            source.backup(target)
        snapshot.chmod(0o600)
        for old in sorted(backups.glob('*.sqlite3'))[:-7]:old.unlink()
    keys=root/'keys.json'
    if not keys.exists() or keys.stat().st_mode & 0o077: raise RuntimeError('keys.json must exist with mode 600')
    run('docker','run','-d','--name',candidate,'--restart','unless-stopped',
        '--network',cfg['network'],'--user',str(os.getuid())+':'+str(os.getgid()),
        '--memory','512m','--cpus','1','--pids-limit','128','--read-only',
        '--log-opt','max-size=5m','--log-opt','max-file=2',
        '--cap-drop','ALL','--security-opt','no-new-privileges:true','--tmpfs','/tmp:rw,noexec,nosuid,size=32m',
        '-v',str(data)+':/data','-v',str(keys)+':/run/secrets/kokbot-keys.json:ro',
        '-e','KOKBOT_KEYS_FILE=/run/secrets/kokbot-keys.json','-e','KOKBOT_BASE_PATH='+cfg['prefix'],image)
    switched=False
    config_path=Path(cfg['caddy_config'])
    old_bytes=None
    new_bytes=None
    try:
        for _ in range(40):
            status=run('docker','inspect','--format','{{.State.Health.Status}}',candidate)
            if status=='healthy':break
            if status=='unhealthy':raise RuntimeError('Candidate failed its container health check')
            time.sleep(1)
        else:raise RuntimeError('Candidate did not become healthy')
        # Lock is shared by all Kokbot invocations; refuse config drift during validation.
        with open(str(config_path)+'.kokbot.lock','w') as config_lock:
            fcntl.flock(config_lock,fcntl.LOCK_EX)
            old_bytes=config_path.read_bytes()
            previous=json.loads(old_bytes)
            active=json.loads(run('docker','exec',cfg['caddy_container'],'wget','-qO-','http://127.0.0.1:2019/config/'))
            if active!=previous:raise RuntimeError('Caddy active config differs from disk; preserve it and reconcile first')
            new_config=json.loads(old_bytes)
            routes=new_config['apps']['http']['servers'][cfg.get('caddy_server','srv0')]['routes']
            routes[:]=[r for r in routes if r.get('@id')!='kokbot-public-route']
            routes.insert(0,route(cfg['host'],cfg['prefix'],candidate))
            new_bytes=json.dumps(new_config,ensure_ascii=False,indent=2).encode()
            # Validate candidate via stdin in an isolated temporary file in the Caddy container.
            validation_file='/tmp/kokbot-config-'+revision[:12]+'.json'
            run('docker','exec','-i',cfg['caddy_container'],'sh','-c','umask 077; cat > '+validation_file,input=new_bytes.decode())
            try:
                run('docker','exec',cfg['caddy_container'],'caddy','validate','--config',validation_file)
            finally:
                run('docker','exec',cfg['caddy_container'],'rm','-f',validation_file)
            if sha(config_path.read_bytes())!=sha(old_bytes):raise RuntimeError('Caddy file changed during validation')
            backup=root/'caddy-before-'+revision[:12]+'.json'
            backup.write_bytes(old_bytes);backup.chmod(0o600)
            write_in_place(config_path,new_bytes)
            try:
                run('docker','exec',cfg['caddy_container'],'caddy','reload','--config',cfg['caddy_container_config'])
            except Exception:
                write_in_place(config_path,old_bytes)
                run('docker','exec',cfg['caddy_container'],'caddy','reload','--config',cfg['caddy_container_config'])
                raise
            switched=True
        health_url='https://'+cfg['host']+cfg['prefix']+'/healthz'
        health=request_json(health_url)
        if health.get('revision')!=revision:raise RuntimeError('Public health revision does not match the deployed commit')
        state={'revision':revision,'container':candidate,'deployed_at':time.time(),'ci_run':matching[0]['html_url'],'health_url':health_url}
        temp=root/'state.next.json';temp.write_text(json.dumps(state,indent=2));temp.replace(state_path)
        print('Deployed '+revision+'; public health verified; CI '+matching[0]['html_url'])
    except Exception:
        if switched and old_bytes is not None:
            with open(str(config_path)+'.kokbot.lock','w') as config_lock:
                fcntl.flock(config_lock,fcntl.LOCK_EX)
                # Preserve any unrelated concurrent changes: replace only our route.
                current=json.loads(config_path.read_bytes())
                routes=current['apps']['http']['servers'][cfg.get('caddy_server','srv0')]['routes']
                old_routes=json.loads(old_bytes)['apps']['http']['servers'][cfg.get('caddy_server','srv0')]['routes']
                old_route=next((r for r in old_routes if r.get('@id')=='kokbot-public-route'),None)
                routes[:]=[r for r in routes if r.get('@id')!='kokbot-public-route']
                if old_route:routes.insert(0,old_route)
                write_in_place(config_path,json.dumps(current,ensure_ascii=False,indent=2).encode())
                run('docker','exec',cfg['caddy_container'],'caddy','reload','--config',cfg['caddy_container_config'])
        run('docker','rm','-f',candidate)
        raise
    # Cleanup failure must never roll back a healthy deployment to a stopped container.
    previous_container=old_state.get('container')
    if previous_container and previous_container!=candidate and re.fullmatch(r'kokbot-[a-f0-9]{12}',previous_container):
        try:
            run('docker','stop','--time','15',previous_container)
            # Keep one previous stopped container/image for manual rollback.
            for name in run('docker','ps','-a','--filter','name=kokbot-','--format','{{.Names}}').splitlines():
                if name not in (previous_container,candidate) and re.fullmatch(r'kokbot-[a-f0-9]{12}',name):run('docker','rm',name)
        except Exception:
            print('Deployment is healthy; previous-container cleanup needs operator review')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True,type=Path)
    args=parser.parse_args()
    args.root.mkdir(parents=True,exist_ok=True,mode=0o700)
    with open(args.root/'deploy.lock','w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        deploy(args.root)
