# 콕봇 API · v1

공개 기준 주소: `https://knowledge.openakashic.com/kokbot`
개발 기준 주소: `http://127.0.0.1:8080`

서버는 JSON 보관·전달·형식/참조 검증만 한다. 수집, 요약, 출제, 기기용 문장 작성, 연출 선택, 복습 일정 결정, 튜터 답변은 **각 Grok Bot이 직접 수행**한다. 서버에 모델 API 키나 모델 호출 코드는 없다. 작업 등록 자체가 Grok Bot을 자동으로 깨우지는 않는다. 각 Bot의 도구와 사용자가 승인한 루틴에서 작업을 가져온다.

## 인증과 범위

`Authorization: Bearer <역할별 키>`가 모든 데이터 API에 필요하다. URL·Git·공개 봇 템플릿에 키를 넣지 않는다. 이 버전은 **신뢰하는 팀원들이 쓰는 하나의 작업 공간**이다. 사용자별 강의 격리, 결제, 공개 다중 사용자 SaaS는 구현 범위가 아니다.

| 역할 | 수행할 작업 | 주요 권한 |
|---|---|---|
| operator | 팀 웹 화면 | 강의/작업 등록, 결과 읽기, 풀이 기록 |
| collector | collect | 수집 작업 인수·결과 제출 |
| organizer | organize | 정리 작업 인수·결과 제출 |
| questioner | quiz | 출제 작업 인수·결과 제출 |
| formatter | format | 기기 포맷 작업 인수·결과 제출 |
| director | react | 반응·소리 매핑 제출 |
| scheduler | schedule | 풀이 기록을 읽고 복습 일정 제출 |
| tutor | tutor | 기존 콕 화면의 구간 질문 답변 |
| device | 없음 | 학습팩/연출/일정 읽기, 풀이 기록 |

Bot은 다른 역할의 작업을 등록하여 넘길 수 있지만, 다른 역할로 작업을 인수하거나 결과를 제출할 수 없다. Bot 키는 팀 자료를 읽을 수 있으므로 외부 수강생에게 제공하지 않는다. 장치 키는 원문·요약·출제 원본을 읽을 수 없다.

## 호출 순서

1. `POST /api/v1/courses` — `{title, source_url, description?}` → `id`.
2. `POST /api/v1/jobs` — `{course_id, kind:"collect", input:{url}}` → 작업.
3. 수집 Bot: `GET /api/v1/jobs?kind=collect`에서 `queued`, `expired`, `failed` 작업 확인.
4. `POST /api/v1/jobs/{id}/claim` — `{lease_seconds:600}` → 입력과 `lease_token`.
5. **Bot이 자기 도구로 실제 자료를 읽고 결과 JSON을 작성한다.**
6. `POST /api/v1/jobs/{id}/complete` — `{lease_token, result}` → 불변 `artifact`.
7. Bot 또는 작업 담당자가 다음 역할의 작업을 등록한다. `input.artifact_ids`에 이전 결과 ID를 넣는다.

작업을 인수한 Bot은 5분 간격으로 `POST .../heartbeat`에 `{lease_token}`을 보내면 된다. 기본 임대는 10분, 최초 인수 시 최대 30분이다. 만료되면 다시 인수해야 한다. 수행 불가 시 `POST .../fail`에 `{lease_token, reason}`을 제출한다. 인증된 Bot 이름·작업 종류·임대 토큰이 모두 일치해야 한다.

원본 접근 불가는 수집 결과에 `status:"blocked"`, 부분 접근은 `partial`로 남긴다. 제목만 보고 읽지 않은 본문을 채우지 않는다. 학습 결과를 서버가 보충하거나 자동 생성하지 않는다.

## 결과 형식

정확한 JSON Schema는 `python -m client.kokbot schema --kind collect`처럼 각 종류로 출력한다. 전체 HTTP 명세는 `/openapi.json`에 있다.

- collect: `sources[{id,title,url?,status,segments[{id,text,locator}],note}]`
- organize: `summary,coverage,concepts[{id,title,explanation,evidence}]`
- quiz: `notes_artifact_id,questions[{id,concept_id,question,choices:[A,B],correct_index,explanation,evidence}]`
- format: `title,quiz_artifact_id,display_contract,questions[{id,source_question_id,question_lines,choices,correct_index,explanation_lines}]`
- react: `states[{state,animation,sound}]` — 고정된 상태/에셋 이름만 허용.
- schedule: `items[{id,learner_id,pack_id,question_id,due_at,reason}]` — Bot이 시간과 이유를 결정.
- tutor: `answer,summary?,hints?,exam?,exam_note?` — 실행 가능한 HTML/실험 코드 제외.

`evidence`는 `[{artifact_id,source_id,segment_id}]`이며 동일 강의의 실제 수집 결과를 가리킨다. 결과 저장 시 참조와 형식을 검사한다. 의미적 사실성·교육적 품질까지 서버가 판단하거나 보증하지 않는다.

## 읽기·학습

- `GET /api/v1/me` — 현재 키 이름/역할
- `GET /api/v1/courses`
- `GET /api/v1/jobs?course_id=...&kind=...`
- `GET /api/v1/artifacts?course_id=...&kind=format` — 결과 목록
- `GET /api/v1/artifacts/{id}` — 결과 본문, 작성 Bot, 작업 ID
- `GET /api/v1/packs/{id}` — 기기용 학습팩
- `POST /api/v1/attempts` — `{id,learner_id,pack_id,question_id,selected_index,answered_at}`
- `GET /api/v1/attempts?learner_id=...` — 일정 Bot 입력

정답은 출제 Bot이 작성한 `correct_index`(0/1)를 사용한다. 장치/웹은 선택값을 비교해 즉시 피드백하고 기록만 보낸다. 학습팩 ID는 버전별로 고정된다. 풀이 도중 새 팩으로 자동 교체하지 않는다. `answered_at`, `due_at`는 시간대가 있는 ISO 8601 값이다.

동일 강의/작업/풀이 ID에 동일 입력을 재전송하면 기존 결과를 반환하고, 다른 내용을 보내면 409다. 완료된 결과는 수정되지 않는다. 변경은 새 작업으로 제출한다. 결과 제출 재시도는 원래 Bot과 임대 토큰, 동일 결과일 때만 허용된다.

## NU40 DK 256×64 계약

`display_contract = nu40-256x64-font16-v1`:

- 질문 최대 2줄, 각 224px. 우측 32px는 캐릭터 공간.
- 선택지 정확히 2개, 각 96px. 버튼 1=A, 버튼 2=B.
- 해설 최대 3줄, 각 224px. 해설 화면의 다음 버튼으로 다음 문제.
- 한글 등 전각 문자를 16px, ASCII를 8px로 계산하는 보수적인 계약이다. 실제 디스플레이 컨트롤러, 한글 폰트, USB/시리얼 방식은 하드웨어 담당자가 확정하고 실물에서 검증해야 한다.

`device/bridge.py`는 표준입출력 NDJSON 어댑터다. 펌웨어는 `{"type":"button","button":1,"event_id":"고유값"}`를 보내고, `frame`의 줄/선택지를 그린다. 이 저장소는 특정 NU40 드라이버나 핀맵을 추정해 플래싱하지 않는다.

## 기존 화면 호환

`kok/index.html`의 `/api/presign/put` → PUT → `/api/done` 요청을 튜터 작업으로 저장하고, 튜터 Bot의 완료 결과를 `/api/list`, `/api/dl`로 반환한다. 원래 화면의 요청/결과 폴더 기본값을 유지해야 한다. API 키는 중앙 화면에서 연결한 같은 탭의 `sessionStorage`를 쓴다. 빈 수업 본문은 거절한다. 시연 예시는 실제 Bot 응답과 분리한다.

`hub/`는 원본 공개 스냅샷이다. 실제 강의 파일과 개인 드라이브 서버는 포함되지 않는다. 실패한 저장 요청을 성공으로 표시하지 않는다.

요청 크기 한도는 1 MiB. 목록은 최근 500개(풀이 2000개)까지인 빌드데이용 MVP다. 팀이 커지면 페이지네이션·작업별 읽기 권한·명시적 보관/삭제 정책을 먼저 확장한다.
