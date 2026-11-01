# 콕 통합 스킬 버전표 (2026-11-01, v1.2.1)
| 스킬 | 버전 | 담당자 | 유래 원본 | 입력 | 출력 |
|---|---|---|---|---|---|
| kok-onboarding | v1.2.3 | 공동(인수·용철) | kok-getting-started | 첫 메시지 / 스킬 업데이트 요청 | 소개·바로 처리 / 업데이트 보고 |
| kok-router | v1.2.3 | 공동(인수·용철) | kok-button-router | lecture.md + 번호 1~4 | 선택 스킬 출력(채팅 첨부) |
| kok-lecture-collector | v1.2.3 | 인수 | lecture-collector-v2 | 링크·파일·입력 글 | lecture.md, collect.log, review_images.log |
| kok-problem-drill | v1.2.3 | 용철 | problem-drill (+temp-drill-web-v1 참고) | lecture.md | spec.json, drill.html |
| kok-podcast | v1.2.3 | 용철 | notebooklm-studio-pack | lecture.md | 대본, source.md, 실제 음원, status.json |
| kok-concept-lab | v1.2.3 | 용철 | concept-lab-visualizer | lecture.md | lab.json, 실험실 화면 |
| kok-schedule | v1.2.3 | 용철 | klas-deadline-cards | 시간표 이미지·PDF·텍스트 + 사용자 일정 (+선택 lecture.md) | timetable.json, schedule.json, 웹 4번 |

추후 누코드 연동 담당 = 제무 (이번 버전 미구현). 원본 sha256은 각 SKILL.md 머리표와 originals/SHA256SUMS 참조.

## 변경 기록
- v1.2.1 (2026-11-01): originals/upstream-latest 6개를 같은 7개 kok-* 스킬에 병합(새 스킬·봇·루틴·로그인·키·웹훅·백엔드 없음). 상세 originals/upstream-latest/MERGE_NOTES.md.
  드릴 하트/아쉬움 팝업·KaTeX(trust:false)·textContent/escape, 팟캐스트 mp3 mono 64k·5~8분 기본·중간 안내, 3D 실험실(safe_expr 허용목록, eval/new Function 없음, 2D 대체), 일정 D-day/카드는 날짜 명시 항목만·LMS 거부, 라우터 중복 방지·두 경로, 온보딩 피드백 기반 업데이트 7단계·환경 점검. 엄격 하네스(=== true, FAIL 시 종료코드 1)·음성 대조.
- v1.1.0 (2026-11-01): kok-schedule·kok-onboarding·kok-router만 갱신(나머지 4개 v1.0.0 유지, 스킬 이름 7개 그대로).
  일정 계약 변경: 입력 = 시간표 이미지·PDF·텍스트, 출력 = timetable.json + schedule.json, 애매한 값 needs_review, 마감 추측 없음, KLAS/LMS 수집 제거, 시간표가 없으면 4번에서만 요청.
  회귀 테스트: `tests/regress.py timetable`, `tests/regress.py privacy`, 익명 샘플 `tests/samples/timetable_anon.json`.
- v1.2.1 보완 (2026-11-01): 수집기 이미지 전수 열람·review_images.log 필수(collector v2 퇴행 수정). 팩 MANIFEST.json + tools/verify_pack.py, 온보딩 처음 한 번 리소스 준비 경로.

- v1.2.2: 지정 화면·부분 생성·ZIP 전달·topic_generated 출처 보존·팟캐스트 전용 로그인.

- v1.2.3: HTML 내장 오디오·3D와 개별 미디어 첨부. ZIP 압축 해제는 기본 절차에서 제거.
