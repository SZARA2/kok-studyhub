import json
from pathlib import Path

import pytest

from scripts.build_lesson import render, validate


def fixture():
    return json.loads((Path(__file__).resolve().parent.parent/'examples/and-gate.json').read_text())


def test_single_html_contains_questions_and_controls_without_network():
    html=render(fixture())
    assert '@@PACK_JSON@@' not in html and '@@LESSON_SCRIPT@@' not in html
    assert 'window.kokbot=' in html and 'AND 게이트' in html
    assert '<script src=' not in html and '<link ' not in html and 'fetch(' not in html
    assert 'kokbot:state' in html


def test_bot_text_cannot_break_out_of_embedded_json():
    pack=fixture();pack['questions'][0]['prompt']='</script><script>window.injected=true</script>'
    html=render(pack)
    assert '</script><script>window.injected=true' not in html
    assert '\\u003c/script\\u003e' in html


@pytest.mark.parametrize('change', ['one_choice','same_choice','wrong_answer','duplicate_id','empty_explanation'])
def test_question_contract_rejects_ambiguous_or_invalid_output(change):
    pack=fixture();q=pack['questions'][0]
    if change=='one_choice':q['choices']=['A']
    elif change=='same_choice':q['choices']=['A','A']
    elif change=='wrong_answer':q['correct_index']=True
    elif change=='duplicate_id':pack['questions'][1]['id']=q['id']
    elif change=='empty_explanation':q['explanation']=' '
    with pytest.raises(ValueError):validate(pack)
