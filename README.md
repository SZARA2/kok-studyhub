# 콕봇 · 수집·정리 결과물 전달

**내 Grok Bot은 링크의 문제·자료를 수집하고 정리하는 데까지만 담당합니다.**
용철님 Bot이 그 결과로 문제를 출제하고 정적 웹을 만듭니다. 이 저장소의 API는 두 Bot 사이에서 결과물을 보관·전달하는 역할만 합니다.

```text
강의/문제 링크
  → 내 Grok Bot: 실제 자료 수집 + 정리
  → 정리 결과물 (Markdown + 원본 URL + 읽은 범위)
  → 지금: API로 등록/조회
  → 나중: 같은 결과물을 용철님 Bot에 직접 전달
```

- API 주소: https://knowledge.openakashic.com/kokbot/
- [등록·조회·수신 확인 연결 안내](docs/API.md)
- [내 수집·정리 Bot의 지침](bots/collector.md)
- [수동 운영 안내](docs/OPERATIONS.md)

서버는 자료를 수집하거나 요약하지 않고, 모델을 호출하거나 출제/학습 웹을 만들지 않습니다. 작업 큐, 자동 후속 Bot 실행, CI/CD도 사용하지 않습니다. 웹·보드·출제 기능은 각각 담당자가 만든 Bot에 연결합니다.

최용철님의 [원본 저장소](https://github.com/cyc53233-coder/kok-studyhub)에서 fork했습니다. `kok/`, `hub/`는 참고용 원본으로 유지하며 개인 드라이브 서버를 공개 실행하지 않습니다. 원본 설명은 [docs/UPSTREAM.md](docs/UPSTREAM.md)에 보존했습니다.

```bash
pip install -r requirements-dev.txt
python -m pytest -q
# KOKBOT_URL 및 역할별 KOKBOT_KEY를 비공개 환경에 설정한 뒤:
python -m client.handoff send result.json
python -m client.handoff list
python -m client.handoff markdown RESULT_ID --out collected-notes.md
```

누구나 fork/PR로 수정할 수 있습니다. 직접 push는 초대한 협업자에게만 가능합니다. 커밋이나 병합이 운영 서버를 자동 변경하지 않습니다.
