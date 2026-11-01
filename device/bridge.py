"""Transport-neutral NDJSON button/display bridge. No board driver or AI runtime.

The NU40 firmware/USB adapter reads frame events and writes button events.
Run with a Bot-authored, exported pack; this also works without a server.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from uuid import uuid4

from backend.models import DevicePack


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack',required=True)
    parser.add_argument('--attempts',required=True)
    parser.add_argument('--learner',default='local_learner')
    args=parser.parse_args()
    envelope=json.loads(Path(args.pack).read_text(encoding='utf-8-sig'))
    pack=DevicePack.model_validate(envelope['result'])
    pack_id=envelope['id']; index=0; feedback=False; seen=set()
    def emit(value): print(json.dumps(value,ensure_ascii=False),flush=True)
    def frame():
        q=pack.questions[index]
        emit({'type':'frame','width':256,'height':64,'pack_id':pack_id,'question_id':q.id,
              'lines':q.explanation_lines if feedback else q.question_lines,
              'choices':[] if feedback else q.choices,'state':'feedback' if feedback else 'learning',
              'page':index+1,'total':len(pack.questions)})
    frame()
    for line in sys.stdin:
        try:
            event=json.loads(line)
            if event.get('type')!='button' or event.get('button') not in (1,2) or not isinstance(event.get('event_id'),str):
                raise ValueError('Expected {type:button,button:1|2,event_id:unique-string}')
            if event['event_id'] in seen: continue
            seen.add(event['event_id'])
            if feedback:
                if index+1==len(pack.questions): emit({'type':'finished','pack_id':pack_id}); break
                index+=1;feedback=False;frame();continue
            q=pack.questions[index]
            attempt={'id':'attempt_'+uuid4().hex,'learner_id':args.learner,'pack_id':pack_id,'question_id':q.id,'selected_index':event['button']-1,'answered_at':datetime.now(timezone.utc).isoformat()}
            target=Path(args.attempts);target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('a',encoding='utf-8') as output: output.write(json.dumps(attempt,ensure_ascii=False)+'\n')
            emit({'type':'answer','correct':attempt['selected_index']==q.correct_index,'attempt_id':attempt['id']})
            feedback=True;frame()
        except (ValueError,KeyError) as exc:
            emit({'type':'error','message':str(exc)})


if __name__=='__main__': main()
