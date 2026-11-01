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
