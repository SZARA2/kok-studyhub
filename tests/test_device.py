import json
import subprocess
import sys
from pathlib import Path


def test_button_bridge_deduplicates_and_records_without_server(tmp_path):
    pack={'id':'offline_pack','result':{'title':'Synthetic fixture','quiz_artifact_id':'quiz1','questions':[{'id':'q1','source_question_id':'original1','question_lines':['AND(1,0)?'],'choices':['0','1'],'correct_index':0,'explanation_lines':['Both inputs must be 1.']}]}}
    source=tmp_path/'pack.json';source.write_text(json.dumps(pack))
    attempts=tmp_path/'attempts.jsonl'
    event={'type':'button','button':1,'event_id':'press1'}
    finish={'type':'button','button':2,'event_id':'press2'}
    result=subprocess.run([sys.executable,'-m','device.bridge','--pack',str(source),'--attempts',str(attempts)],
                          input='\n'.join(map(json.dumps,[event,event,finish]))+'\n',capture_output=True,text=True,check=True)
    output=[json.loads(line) for line in result.stdout.splitlines()]
    assert [e['type'] for e in output]==['frame','answer','frame','finished']
    assert output[1]['correct'] is True
    saved=[json.loads(line) for line in attempts.read_text().splitlines()]
    assert len(saved)==1 and saved[0]['selected_index']==0
