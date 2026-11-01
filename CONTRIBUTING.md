# 콕봇에 기여하기

누구나 fork → 브랜치 → Pull Request로 수정 제안을 보낼 수 있습니다.
직접 push가 필요한 팀원은 GitHub 아이디를 관리자에게 전달해 collaborator 초대를 받으세요.

1. Python 3.12로 `pip install -r requirements-dev.txt`.
2. `codex/설명` 또는 팀에서 합의한 브랜치에서 수정.
3. `python -m pytest -q`, `node --check web/app.js` 실행.
4. PR에 변경한 사용자 동작과 확인한 내용을 적기.

main은 실제 서버에 배포됩니다. 개인 강의 원문/계정/키/DB/학습 기록은 커밋하지 마세요.
서버에 AI 기능을 넣지 마세요. 해당 Grok Bot의 역할 지침과 결과 규격을 고치고,
서버에는 필요한 저장/전달/기계적 검증만 추가합니다.

`backend/models.py`의 출력 규격을 바꾸면 봇 지침, 클라이언트, 웹/기기 계약과 호환성을 함께 검토하세요.
최용철님의 원본 `kok/`, `hub/` 화면과 작성자 표기를 유지하세요.
