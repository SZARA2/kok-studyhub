"""The complete Bot handoff path must also work with no HTTP service."""
import socket

from client.kokbot import LocalTransport


def test_all_bot_handoffs_without_network(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError('Local mode must not use the network')
    monkeypatch.setattr(socket, 'create_connection', no_network)
    operator=LocalTransport(tmp_path,'operator','owner')
    operator.call('POST','courses',{'id':'c','title':'Synthetic offline fixture'})
    def perform(kind,role,result):
        job=operator.call('POST','jobs',{'kind':kind,'course_id':'c'})
        bot=LocalTransport(tmp_path,role,role)
        lease=bot.call('POST',f"jobs/{job['id']}/claim",{})
        return bot.call('POST',f"jobs/{job['id']}/complete",{'lease_token':lease['lease_token'],'result':result})
    source=perform('collect','collector',{'sources':[{'id':'s','title':'Synthetic truth table','status':'complete','segments':[{'id':'a','text':'AND(1,0)=0. Both inputs must be 1 to output 1.'}]}]})
    evidence=[{'artifact_id':source['id'],'source_id':'s','segment_id':'a'}]
    notes=perform('organize','organizer',{'summary':'AND gate','coverage':'complete','concepts':[{'id':'and','title':'AND','explanation':'Both inputs must be 1.','evidence':evidence}]})
    quiz=perform('quiz','questioner',{'notes_artifact_id':notes['id'],'questions':[{'id':'q','concept_id':'and','question':'AND(1,0)?','choices':['0','1'],'correct_index':0,'explanation':'One input is zero.','evidence':evidence}]})
    pack=perform('format','formatter',{'title':'AND','quiz_artifact_id':quiz['id'],'questions':[{'id':'dq','source_question_id':'q','question_lines':['AND(1,0)?'],'choices':['0','1'],'correct_index':0,'explanation_lines':['Both inputs must be 1.']}]})
    reaction=perform('react','director',{'states':[{'state':'correct','animation':'jump','sound':'none'}]})
    operator.call('POST','attempts',{'id':'try1','learner_id':'student','pack_id':pack['id'],'question_id':'dq','selected_index':0,'answered_at':'2026-11-01T14:00:00+09:00'})
    scheduler=LocalTransport(tmp_path,'scheduler','scheduler')
    assert scheduler.call('GET','attempts')['items'][0]['pack_id']==pack['id']
    schedule=perform('schedule','scheduler',{'items':[{'id':'review1','learner_id':'student','pack_id':pack['id'],'question_id':'dq','due_at':'2026-11-02T14:00:00+09:00','reason':'Synthetic Bot-authored review'}]})
    reopened=LocalTransport(tmp_path,'device','device')
    assert reopened.call('GET','packs/'+pack['id'])['result']['questions'][0]['correct_index']==0
    assert reopened.call('GET','artifacts/'+reaction['id'])['result']['states'][0]['animation']=='jump'
    assert reopened.call('GET','artifacts/'+schedule['id'])['result']['items'][0]['due_at']=='2026-11-02T14:00:00+09:00'
    assert len(operator.call('GET','jobs')['items'])==6
