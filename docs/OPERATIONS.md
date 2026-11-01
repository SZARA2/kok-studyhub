# 운영과 배포

## 로컬 API 실행

Python 3.12 가상환경에서 `pip install -r requirements-dev.txt`.
비공개 키 파일에는 다음 형식의 배열을 둔다. 키마다 무작위 32바이트 이상을 권장한다.

```json
[{"name":"team-operator","role":"operator","key":"REPLACE_WITH_A_RANDOM_SECRET_OF_AT_LEAST_32_CHARACTERS"}]
```

`KOKBOT_KEYS_FILE`을 이 파일 절대 경로로, `KOKBOT_DB`를 데이터 파일 경로로 설정한다.

```sh
uvicorn backend.main:create_app --factory --host 127.0.0.1 --port 8080
python -m pytest -q
```

키 파일이 없으면 서버는 시작하지 않는다. 기본 관리자 키/공개 쓰기 권한은 없다.
운영 키 교체 후 컨테이너를 다시 생성해야 한다. UI 키는 현재 탭의 sessionStorage만 사용한다.
풀이 전송 실패는 로컬 저장 후 재전송하며, 예시 데이터는 서버에 풀이로 저장하지 않는다.

## CI/CD

GitHub-hosted CI가 테스트, JS 구문 확인, 단일 HTML 생성, Docker 이미지 빌드를 수행한다.
공개 PR 코드를 집 서버의 self-hosted runner에서 실행하지 않는다.

서버의 별도 운영 디렉터리에 설치한 `scripts/deploy.py`를 systemd 사용자 타이머가 실행한다.
배포기는 origin/main의 **해당 커밋에 대한 push CI 성공**을 GitHub API로 확인하고 배포한다.
실패/대기 중인 커밋, PR 검사용 커밋, 다른 브랜치는 배포하지 않는다.
배포기 자체는 자동 업데이트하지 않는다. 배포기 변경은 운영자가 검토 후 설치한다.

새 컨테이너를 먼저 만들고 내부 health를 확인한다. 공유 Caddy의 `kokbot-public-route`만 교체한다.
설정을 검증한 후 reload하며 기존 서비스 컨테이너를 재시작하지 않는다.
공개 `/healthz`의 커밋까지 확인한 뒤 기존 콕봇 컨테이너를 멈춘다.
실패하면 해당 경로를 이전 대상으로 복원한다. 데이터 디렉터리는 릴리스와 분리되어 있다.

운영 디렉터리의 `config.json` 예시 (서버 실제 경로는 운영 기록에서 관리):

```json
{
  "repository": "SZARA2/kok-studyhub",
  "network": "YOUR_EXISTING_PROXY_NETWORK",
  "host": "YOUR_PUBLIC_HOST",
  "prefix": "/kokbot",
  "caddy_config": "/path/to/active/caddy.json",
  "caddy_container": "YOUR_CADDY_CONTAINER",
  "caddy_container_config": "/etc/caddy/caddy.json",
  "caddy_server": "srv0"
}
```

동일 디렉터리 `keys.json`(600), `data/`(700), `deploy.py`, `state.json`, 배포 로그를 관리한다.
설정/키/DB/로그/프록시 백업을 공개 저장소에 넣지 않는다.
DB 백업은 SQLite backup API로 일관된 스냅샷을 만든다. WAL 파일을 무시한 단순 복사는 사용하지 않는다.
복구는 컨테이너 정지→검증된 백업 복원→재시작→API 읽기 검증 순서다.

## 협업

누구나 공개 저장소를 fork하고 Pull Request를 보낼 수 있다.
GitHub 공개 저장소는 익명 직접 push 권한을 제공하지 않는다.
직접 커밋할 팀원은 관리자가 GitHub 아이디로 collaborator에 초대한다.
main에 반영된 변경은 CI 통과 후 자동 배포되므로 리뷰와 테스트를 거쳐 합친다.
원본에 라이선스가 명시되지 않아 원본의 권리/출처를 유지한다. 임의로 전체 저장소에 오픈소스 라이선스를 부여하지 않는다.

## 현재 범위

작업 중계, 자료 저장, 근거 참조/화면 길이 검증, 웹 학습팩 표시와 풀이 기록을 제공한다.
실제 Grok Bot 계정에서의 작업 수행, 외부 강의 로그인, 실제 NU40 보드, 녹음/STT,
원격 lab 실행, 사용자별 서비스 격리와 마켓플레이스 등재는 별도 검증 항목이다.
