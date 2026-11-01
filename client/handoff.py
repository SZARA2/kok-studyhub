"""A thin result upload/download client. Does not collect sources or call models."""
import argparse
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request,urlopen


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['send','list','get','markdown','ack'])
    parser.add_argument('value',nargs='?');parser.add_argument('--out')
    args=parser.parse_args()
    base=os.environ['KOKBOT_URL'].rstrip('/');key=os.environ['KOKBOT_KEY']
    parts=urlsplit(base)
    if parts.scheme!='https' and not(parts.scheme=='http' and parts.hostname in ('localhost','127.0.0.1')):raise SystemExit('Use HTTPS or loopback HTTP')
    if parts.username or parts.password or parts.query or parts.fragment:raise SystemExit('Invalid base URL')
    path='/api/v1/handoffs';body=None;method='GET'
    if args.action=='send':
        if not args.value:parser.error('Provide result.json')
        body=Path(args.value).read_bytes();json.loads(body);method='POST'
    elif args.action in ('get','markdown','ack'):
        if not args.value or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',args.value):parser.error('Provide a result ID')
        path+='/'+args.value
        if args.action=='markdown':path+='/markdown'
        if args.action=='ack':path+='/ack';method='POST';body=b'{}'
    request=Request(base+path,data=body,method=method,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    with urlopen(request,timeout=30) as response:content=response.read().decode('utf-8')
    if args.out:
        output=Path(args.out);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(content,encoding='utf-8')
    else:print(content)


if __name__=='__main__':main()
