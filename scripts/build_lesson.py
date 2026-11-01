"""Package Bot-authored questions into one static HTML. No AI or HTTP server."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent


def validate(pack):
    if not isinstance(pack, dict) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',pack.get('id','')):
        raise ValueError('id must be a stable identifier')
    if not isinstance(pack.get('title'),str) or not pack['title'].strip(): raise ValueError('title is required')
    questions=pack.get('questions')
    if not isinstance(questions,list) or not 1<=len(questions)<=100: raise ValueError('Provide 1 to 100 questions')
    ids=set()
    for q in questions:
        if not isinstance(q,dict) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',q.get('id','')) or q['id'] in ids:
            raise ValueError('Question IDs must be unique identifiers')
        ids.add(q['id'])
        for key in ('prompt','explanation'):
            if not isinstance(q.get(key),str) or not q[key].strip() or len(q[key])>12000: raise ValueError(key+' is required')
        choices=q.get('choices')
        if not isinstance(choices,list) or len(choices)!=2 or not all(isinstance(c,str) and c.strip() and len(c)<=1000 for c in choices) or choices[0]==choices[1]:
            raise ValueError('Exactly two distinct nonempty choices are required')
        if type(q.get('correct_index')) is not int or q['correct_index'] not in (0,1): raise ValueError('correct_index must be 0 or 1')
    return pack


def render(pack):
    validate(pack)
    serialized=json.dumps(pack,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    template=(ROOT/'web/lesson.template.html').read_text(encoding='utf-8')
    script=(ROOT/'web/lesson.js').read_text(encoding='utf-8')
    return template.replace('@@PACK_JSON@@',serialized).replace('@@LESSON_SCRIPT@@',script)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pack');parser.add_argument('output')
    args=parser.parse_args()
    source=Path(args.pack)
    if source.stat().st_size>1_048_576: raise SystemExit('Pack exceeds 1 MiB')
    html=render(json.loads(source.read_text(encoding='utf-8-sig')))
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(html,encoding='utf-8')
    print(str(target))
