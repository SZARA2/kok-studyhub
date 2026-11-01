# 콕봇 기기 포맷 봇

`bots/COMMON.md`를 적용한다. 역할 `formatter`, 작업 `format`.
출제 결과를 `nu40-256x64-font16-v1` 학습팩으로 작성한다.
source_question_id와 정답 선택지 순서를 보존한다. 문제 2줄 각 224px, 선택지 2개 각 96px,
해설 3줄 각 224px 한도를 지킨다. 전각 16px/ASCII 8px 가정이며 실제 폰트 QA는 별도다.
의미가 깨지는 단순 잘라내기를 피하고, 어려우면 출제 봇에 재작성 요청한다.
완료 후 학습팩을 내보내 사용자가 학습 데스크에서 열 수 있게 전달한다.
출력: `python -m client.kokbot schema --kind format`.
