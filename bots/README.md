# 독립 Grok Bot 템플릿 원본

현재 기본 역할은 **3개**다. [세 Bot 흐름](../docs/THREE_BOTS.md)을 우선한다.

1. `curator.md`: 내 Grok Bot이 강의 수집·정리 → lesson.md
2. `questioner.md`: 용철님 Bot이 문제·해설·정적 웹 → study.html
3. `nu40-controller.md`: 제무님 Bot이 웹 상태를 읽고 버튼 1/2 전달

아래 collector/organizer/formatter/director/scheduler/tutor 파일은 선택형 분업·API 확장을 위한 지침이다. 기본 학습에 추가 Bot 여섯 개를 요구하지 않는다.

각 파일을 해당 역할 Bot의 첫 메시지로 사용한다. 기본은 같은 컴퓨터의 로컬 폴더를 쓰는 모드다. 협업 기간에만 사용자가 지정한 HTTPS API로 전송 방식을 바꾼다. 어떤 모드에서도 실제 수집·판단·작성은 Bot 자신이 수행한다.

- `collector.md` · 자료 수집
- `organizer.md` · 근거 기반 정리
- `questioner.md` · 이지선다 출제
- `formatter.md` · 256×64 학습팩
- `director.md` · 캐릭터/소리 반응
- `scheduler.md` · 복습 일정
- `tutor.md` · 수업 중 구간 질문

공통 계약과 CLI: [연결 안내](../docs/BOTS.md), [API](../docs/API.md). 템플릿에는 운영키·개인 자료가 포함되지 않는다. 이 파일들은 배포 준비용 지침이며, Grok Bot 앱의 공개 템플릿 링크가 아직 생성된 것은 아니다.
