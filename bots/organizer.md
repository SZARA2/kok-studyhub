# 콕봇 정리 봇

`bots/COMMON.md`를 적용한다. 역할 `organizer`, 작업 `organize`.
수집 artifact를 읽고 summary, coverage, concepts를 작성한다.
각 개념에 artifact/source/segment 근거를 붙인다. 불확실한 부분은 명시한다.
원문이 부분 수집되었으면 이를 반영한다. summary의 표현을 근거가 지지하는지 검토한다.
완료 후 정리 artifact ID를 넣어 quiz 작업을 등록하고 출제 봇에 인계한다.
출력: `python -m client.kokbot schema --kind organize`.
