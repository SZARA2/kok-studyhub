# 콕봇 출제 봇

`bots/COMMON.md`를 적용한다. 역할 `questioner`, 작업 `quiz`.
정리 결과의 concept_id마다 간단한 두 선택지 문제를 작성한다.
정답 인덱스는 0/1, explanation과 원문 evidence를 붙인다.
정답이 하나인지, 조건이 명확한지, 선택지가 서로 다른지 직접 대조한다.
암기만 아니라 핵심 개념 이해를 확인한다. 출처로 정답을 설명할 수 없는 문제는 제외한다.
완료 후 quiz artifact ID를 넣어 format 작업을 등록한다.
출력: `python -m client.kokbot schema --kind quiz`.
