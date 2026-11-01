# 결과물 등록·조회·수신 확인

기준 주소: `https://knowledge.openakashic.com/kokbot`

현재는 한 팀의 결과물을 공유하는 작은 API다. 나중에 API를 쓰지 않아도 동일한 Markdown 결과물을 용철님 Bot에 직접 전달할 수 있다. 출제와 정적 웹 생성은 용철님 Bot이 수행하며 이 API에는 구현하지 않는다.

## 역할과 인증

모든 자료 요청에 `Authorization: Bearer <역할별 키>`를 보낸다.

- `collector`: 내 Grok Bot. 수집·정리한 결과 등록과 조회.
- `questioner`: 용철님 Bot. 결과 조회·다운로드·수신 확인. 이 이름은 수신자의 역할이며 서버가 출제한다는 의미가 아니다.
- `operator`: 팀 관리용 등록·조회·수신 확인.

키는 비공개 환경변수 `KOKBOT_KEY`, 주소는 `KOKBOT_URL`에 설정한다. GitHub·Notion·공개 Bot 템플릿에 키나 비공개 강의 원문을 붙여 넣지 않는다. 사용자별 격리가 있는 공개 SaaS가 아니라 팀용 공유 공간이다.

## 1. 내 Bot이 결과 등록

`POST /api/v1/handoffs`

```json
{
  "id":"lecture1-notes-v1",
  "title":"강의 1 · 수집 및 정리",
  "source_url":"https://example.com/lecture",
  "coverage":"partial",
  "content_markdown":"# 읽은 범위\n...\n# 수집한 문제\n...\n# 핵심 내용 정리\n...\n# 출처 위치\n...",
  "notes":"로그인 없이 읽을 수 있는 부분만 수집함"
}
```

`id`는 생략 시 자동 생성된다. 재전송할 때 동일 ID를 사용하면 같은 결과를 중복 생성하지 않는다. 같은 ID로 내용을 바꾸면 409이며 수정본은 새 ID로 제출한다.

`coverage`는 `complete` / `partial` / `blocked`. 부분 수집을 완전 수집으로 표시하지 않는다. `blocked`라면 `notes`에 이유를 써야 하며 빈 본문을 허용한다. 나머지는 실제 읽은 본문이 필요하다.

서버는 등록한 결과를 그대로 저장하며 작성자, 시각, SHA-256을 붙인다. 등록 성공이 용철님 Bot 실행·출제 완료를 뜻하지 않는다.

## 2. 용철님 Bot이 결과 받기

- `GET /api/v1/handoffs` — 최근 200개 메타데이터 목록.
- `GET /api/v1/handoffs?unreceived=true` — 아직 수신 확인하지 않은 결과.
- `GET /api/v1/handoffs/{id}` — 원문과 메타데이터.
- `GET /api/v1/handoffs/{id}/markdown` — Markdown 파일 내용.
- `POST /api/v1/handoffs/{id}/ack` — 수신 확인. 빈 JSON `{}`로 호출할 수 있다.

`ack`는 "이 결과를 받았다"만 기록한다. 출제·웹 생성·보드 실행이 완료됐다는 상태로 사용하지 않는다. 여러 번 호출해도 첫 수신 시각은 유지된다.

## 최소 CLI

```bash
python -m client.handoff send result.json
python -m client.handoff list
python -m client.handoff get lecture1-notes-v1 --out result.json
python -m client.handoff markdown lecture1-notes-v1 --out lesson.md
python -m client.handoff ack lecture1-notes-v1
```

후속 단계에서는 `lesson.md`를 용철님 Bot에 전달하면 된다. 새 Bot을 여러 개 만들거나 작업 임대·학습팩 규격을 맞출 필요가 없다. 소스의 문제/표/수식은 가능한 한 그대로 보존하고, 내 Bot의 정리와 구분해 작성한다.

오류: 인증 없음/잘못된 키 401, 역할 불일치 403, 없는 결과 404, ID 충돌 409, 내용 형식 오류 422, 1 MiB 초과 413. 본문은 공개하지 않으며 `/healthz`와 `/openapi.json`만 인증 없이 확인할 수 있다.
