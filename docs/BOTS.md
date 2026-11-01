# 선택형 협업 API와 로컬 원장 연결

**기본 흐름은 [세 Bot](THREE_BOTS.md)**이다. 내 Bot이 수집·정리, 용철님 Bot이 문제와 정적 웹 생성, 제무님 Bot이 버튼을 전달한다. 아래의 작업 원장·역할별 API는 이 흐름에 필수가 아니며 팀 협업을 세분화할 때만 사용한다.

## 지금: 협업 API

각 Bot에 `bots/<role>.md`를 첫 메시지로 전달한다. 자기 역할 키만 해당 Bot의 로컬 환경에 설정한다. 공통 저장소를 읽을 수 있는 터미널/파일 도구를 활성화해야 한다. Bot 계정의 도구·루틴 실행 권한은 앱에서 확인한다.

```bash
python -m venv .venv
# 운영체제에 맞게 가상환경 활성화 후
pip install -r requirements.txt
export KOKBOT_URL=https://knowledge.openakashic.com/kokbot
# KOKBOT_KEY는 팀의 비공개 키 파일/환경에서 주입. 공유 메시지에 붙여 넣지 않는다.
python -m client.kokbot jobs --kind collect
python -m client.kokbot claim JOB_ID --lease-file runtime/collect-lease.json
python -m client.kokbot schema --kind collect --out runtime/collect-schema.json
# 여기서 수집 Bot이 실제 자료를 읽고 runtime/result.json을 작성한다.
python -m client.kokbot complete JOB_ID --lease-file runtime/collect-lease.json --file runtime/result.json
```

PowerShell에서는 `export` 대신 `$env:KOKBOT_URL='https://knowledge.openakashic.com/kokbot'`로 설정한다. 키는 터미널 출력에 표시하지 않는다. CLI도 임대 토큰은 화면에 출력하지 않고 `--lease-file`에 저장한다.

다음 작업은 Bot이나 담당자가 `enqueue --file runtime/next-job.json`으로 등록한다. 작업 등록이 Grok Bot 앱에 대한 실행 호출은 아니다. 처음에는 각 Bot에 "내 역할의 대기 작업 하나를 처리해"라고 요청한다. 반복 실행은 Grok Bot에서 사용자가 설정한 루틴으로 연결한다. 무제한 짧은 주기의 반복 호출을 기본 활성화하지 않는다.

## 다음: 공유 서버 없이 같은 기기/서버의 Bot끼리

입출력 Schema와 Bot 지침은 그대로 유지한다. 전송 방식만 HTTPS에서 로컬 파일 원장으로 바꾼다.

```bash
python -m client.kokbot --local ./runtime/team --role operator --name operator course --file course.json
python -m client.kokbot --local ./runtime/team --role operator --name operator enqueue --file job.json
python -m client.kokbot --local ./runtime/team --role collector --name collector jobs --kind collect
python -m client.kokbot --local ./runtime/team --role collector --name collector claim JOB_ID --lease-file runtime/lease.json
# Bot이 자기 도구로 작업하고 결과 파일 작성
python -m client.kokbot --local ./runtime/team --role collector --name collector complete JOB_ID --lease-file runtime/lease.json --file result.json
python -m client.kokbot --local ./runtime/team get PACK_ID --out runtime/pack.json
python scripts/export_offline.py runtime/kokbot-offline.html
```

`kokbot-offline.html`을 브라우저에서 열고 학습팩 파일을 불러오면 서버 없이 학습한다. 풀이 기록 JSON을 저장해 일정 Bot에게 전달한다. 보드 담당자는 `python -m device.bridge --pack runtime/pack.json --attempts runtime/attempts.jsonl`을 USB/시리얼 어댑터와 연결한다.

로컬 모드는 HTTP 서버·도메인·서버 인증 키·외부 LLM API 키가 필요 없다. Python 공통 검증/저장 라이브러리와 하나의 SQLite 파일을 직접 사용한다. 역할 인자는 협업 규칙이며, 같은 OS 사용자로 실행되는 Bot 사이의 보안 격리를 제공하지 않는다. OS 파일 권한과 신뢰하는 Bot 구성을 전제로 한다. 네트워크 파일시스템에 SQLite 파일을 놓지 않는다.

## 템플릿/마켓플레이스 준비

각 Bot은 역할 지침, 입력/출력 Schema, 도구 요구사항, 예시 작업, 실패 시 동작을 독립적으로 공유할 수 있다. 공유 템플릿의 기본 모드는 `local`로 설정한다. 우리 도메인·팀 키·팀 자료·개인 경로를 템플릿에 내장하지 않는다. 새 사용자는 자신의 폴더를 선택하고 자신의 소스/도구에 로그인한다.

공식 문서상 Bot 상세 → Share → Create a copy → Publish로 공개 템플릿 링크를 만들 수 있다. 공유본은 받는 사람 계정의 별도 Bot이며 작성자의 로그인·컴퓨터·대화 기록을 받지 않는다. 마켓플레이스 노출 및 팀 공개 정책은 계정에서 실제 확인한다. **이 저장소에 템플릿을 준비한 것과 Grok Bot 앱에서 게시·등록을 완료한 것은 다르다.**

공식 참고: https://docs.x.ai/grok-bot/bots · https://docs.x.ai/grok-bot/computer-and-apps · https://docs.x.ai/grok-bot/chat-and-collaboration

## 3인 협업

| 담당 | 우선 작업 | 인계 완료 기준 |
|---|---|---|
| 백엔드/공통 연결 담당 | API 계약·키 발급·CI/CD·수집/정리/출제 Bot 연결 지원 | 실제 Bot 결과가 강의→학습팩까지 저장되고 다른 담당자가 조회 |
| 최용철 · 웹/일정 | 기존 콕 화면 연결·학습팩 UI·일정 Bot | 튜터 응답 및 실제 학습팩 표시, 풀이 기록이 일정 Bot에 전달 |
| 류제무 · 기기/연출 | 디스플레이 컨트롤러/폰트 확정·포맷 Bot·연출 Bot·버튼/소리 어댑터 | 실물 256×64에서 잘림 없이 표시, 버튼 2개·정답 반응·재연결 검증 |

분업 단위는 사람별 별도 서버가 아니라 같은 계약을 사용하는 기능 브랜치다. Bot별 입력/출력 테스트 파일을 PR에 넣고, 키·실제 학생 자료는 제외한다. 하드웨어 없는 날에는 웹/NDJSON 모의 입력으로 검증하고 실물 검증 완료로 표기하지 않는다.
