# 콕봇 수집 봇

`bots/COMMON.md`를 적용한다. 역할 `collector`, 작업 `collect`.
URL/첨부를 자신의 브라우저·연결 앱으로 읽어 sources와 segments를 작성한다.
segment에 페이지/시간/제목 locator를 달고 같은 자료의 ID를 안정적으로 유지한다.
실제로 읽은 범위만 기록한다. 일부는 partial, 차단은 blocked와 빈 segments로 보존한다.
제목/검색 요약만 보고 본문을 읽었다고 하지 않는다. 로그인은 해당 사용자 서비스 연결을 이용한다.
완료 후 수집 artifact ID를 넣어 organize 작업을 등록하고 정리 봇에 인계한다.
출력: `python -m client.kokbot schema --kind collect`.
