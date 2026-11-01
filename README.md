# 콕봇 · 각 Grok Bot이 만드는 작은 공부 친구

공개 협업 저장소: https://github.com/SZARA2/kok-studyhub

- 학습 데스크/API: https://knowledge.openakashic.com/kokbot/ (배포 상태는 healthz의 revision 확인)
- [각 봇 연결 지침](docs/BOTS.md) · [API 계약](docs/API.md)
- [프론트·템플릿 공유와 서버 없는 개인 모드](docs/SHARING.md)
- [개발·배포 운영](docs/OPERATIONS.md) · [기여하기](CONTRIBUTING.md)

수집 → 정리 → 출제 → 기기 포맷 → 연출/복습 판단은 **각 Grok Bot이 수행**합니다.
서버는 역할별 작업 인계, 결과 저장·검증, 웹/기기 전달만 담당합니다. 서버에 모델 API 키를 넣지 않습니다.

`backend/`는 협업용 FastAPI + SQLite 장부, `client/`는 HTTPS/로컬 전송 클라이언트,
`web/`는 학습팩 미리보기·두 버튼 복습 화면입니다.
`--local` 모드는 중앙 서버 없이 Grok 계정 내 같은 디렉터리에서 봇들이 작업을 이어갑니다.
`python scripts/export_offline.py dist/kokbot-offline.html`로 파일만 열어 쓰는 화면을 만들 수 있습니다.

실제 Grok Bot 계정 실행·공개 템플릿/Marketplace 게시·NU40 하드웨어 동작은 별도 현장 검증이 필요합니다.
기존 `kok/`, `hub/`와 작성자 이력은 아래 원본을 보존합니다. 기존 hub의 개인 드라이브 서버를 공개하지 않습니다.

---

# 콕 + 통합공부판

Grok Bot 빌드데이(해커톤)용 공개 저장소. 누구나 보고, 포크해서 고칠 수 있어요.

- 바로 열기 (GitHub Pages): https://cyc53233-coder.github.io/kok-studyhub/
- `kok/` 콕: 수업 중 보드 키 1~4를 누르면 그 구간(앞 60초)을 그록에게 보내고 답을 받는 화면. `lab.html`은 실험실(three.js).
  - 정적 호스팅에서는 실시간 그록 연결 없이 **예시 답**(`example_result.json`)으로 동작해요.
  - 실시간 그록 답은 원래 개인 드라이브(Cloudflare Workers + R2)의 요청/결과 폴더를 거쳐요. 직접 쓰려면 자기 백엔드에 `/api/list`, `/api/dl`, `/api/presign/put`, `/api/done`를 만들고 그록 API 키는 **서버 비밀값**으로 두세요(코드에 넣지 말 것).
  - `spec*.json`, `spec_schema.md`: 실험실 장면 정의 예시.
- `hub/` 통합공부판: 과목별 공부판을 모아 보는 대시보드.
  - 서버 있으면 `server.py`(로컬, `python server.py` → http://localhost:8626)로, 없으면 `meta.json` 스냅숏으로 동작해요.
  - 과목·시험·링크는 `config.json`에서 고쳐요. 과목별 원본 공부판 파일(교재·강의 자료)은 저작권 때문에 포함하지 않았어요.

## 고치는 법
1. 이 저장소를 Fork 하거나, 협업자로 초대받아 바로 수정
2. 파일 수정 후 커밋하면 GitHub Pages가 1~2분 안에 자동 반영

빌드 없이 HTML/JS/CSS 그대로예요.
