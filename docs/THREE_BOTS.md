# 현재 기본 흐름: 세 Bot, 한 학습 웹

2026-11-01 사용자 확인에 따라 기본 흐름을 세 역할로 단순화했다. 앞서 만든 수집/정리/출제/포맷/연출/일정별 API 작업은 선택형 협업 도구이며, 학습을 시작하기 위한 필수 단계가 아니다.

```text
강의 링크
  → 내 Grok Bot: 수집 + 정리 → lesson.md
  → 용철님 출제 Bot: 문제 + 해설 + 정적 웹 → study.html
  → 제무님 누코드 Bot: 현재 웹 상태 읽기 + 버튼 1/2 전달
  → 선택 → 해설 → 다음 문제 → 완료
```

## 1. 내 Grok Bot

해당 링크의 실제 강의 본문/첨부/자막을 읽고 `lesson.md`로 전달한다. 권장 항목은 강의명, 원본 URL, 읽은 범위, 핵심 개념, 설명/예시, 시험 포인트, 출처 위치, 미확인 부분이다. 원문을 못 읽었으면 그 사실을 남기며 출제할 내용을 지어내지 않는다. 별도 수집 Bot과 정리 Bot을 추가할 필요 없다.

## 2. 용철님 출제 Bot

`lesson.md`를 입력으로 이지선다 문제·정답·해설을 직접 작성하고 **문제와 화면이 함께 든 `study.html` 하나**를 만든다. 기존 출제 Bot이 자신의 HTML을 만드는 경우 아래 버튼/상태 규격만 맞추면 된다. 이 저장소의 기본 화면을 쓸 때는 다음 명령으로 포장한다. 이 명령은 AI 기능이 없으며 Bot이 작성한 내용을 그대로 넣는다.

```sh
python scripts/build_lesson.py questions.json study.html
```

`questions.json`의 최소 형식:

```json
{
  "id":"digital-logic-lesson1-v1",
  "title":"디지털공학 · 논리 게이트",
  "questions":[{
    "id":"q1",
    "prompt":"AND(1,0)의 출력은?",
    "choices":["0","1"],
    "correct_index":0,
    "explanation":"두 입력이 모두 1일 때만 1입니다."
  }]
}
```

실제 내용은 읽은 강의에 근거해야 한다. 위와 `examples/and-gate.json`은 합성 형식 예시다. `study.html`은 별도 JSON 파일 선택·로그인·API 키·서버 없이 바로 열린다. 새 버전은 새 lesson id를 부여한다. 같은 id라도 내용이 바뀌면 이전 진도는 복원하지 않는다.

## 3. 제무님 누코드 Bot

Bot은 열려 있는 학습 웹을 읽고 버튼 이벤트를 전달한다. 브라우저 키보드 도구로 숫자 `1`/`2`를 보내는 가장 단순한 방식부터 연결한다. 기존 Bot이 브라우저 스크립트 도구를 제공한다면 같은 동작을 아래 인터페이스로 호출할 수 있다.

```js
window.kokbot.getState()
window.kokbot.press(1, 'nu40-boot42-event001')
window.kokbot.press(2, 'nu40-boot42-event002')
window.addEventListener('kokbot:state', event => console.log(event.detail))
```

| 화면 상태 | 버튼 1 | 버튼 2 |
|---|---|---|
| question | A 선택 | B 선택 |
| feedback | 다음 문제 | 다음 문제 |
| finished | 진행하지 않음 | 진행하지 않음 |

`getState()`는 lessonId, phase, index, total, question(prompt/choices/id), feedback, attemptCount를 반환한다. 입력에 고유 eventId를 보내면 같은 이벤트의 재전송이 다음 문제를 넘어가게 하지 않는다. 키를 길게 누른 repeat 입력도 무시한다. Bot이 화면 문구를 추측해 좌표를 매번 찾을 필요 없이 고정된 키/규격으로 연결할 수 있다.

NU40의 실제 USB·BLE·시리얼 연결과 디스플레이 표시는 제무님 Bot/로컬 연결 프로그램의 역할이다. Grok Bot이 실행되는 클라우드에서 사용자 PC USB를 직접 읽을 수 있다고 가정하지 않는다. 웹 상태를 디스플레이로 옮기는 과정도 기기 Bot이 맡는다. 보드 모델/해상도만 확인됐고 컨트롤러·폰트·펌웨어 실물 검증은 아직 남아 있다.

## 서버의 위치

집 서버는 협업 중 자료/결과를 주고받는 선택형 API와 공개 웹 배포를 제공한다. **정적 study.html이 완성된 뒤 버튼으로 학습하는 루프에는 중앙 API가 들어가지 않는다.** 새 문제 생성·요약·추가 설명이 필요할 때 해당 Grok Bot을 다시 호출한다.

마켓플레이스에는 이 세 역할의 지침/템플릿을 공유하고 각 사용자가 자기 강의, 자기 Bot, 자기 작업 폴더를 사용하도록 한다. 운영키와 팀 자료는 템플릿에 넣지 않는다. 실제 Bot 템플릿 게시/다른 계정 설치와 두 팀원의 기존 Bot 통합은 아직 검증하지 않았다.
