# 수동 운영

사용자의 범위 교정에 따라 GitHub Actions workflow와 서버 자동 배포 timer를 제거/비활성화했다. 코드 병합이 서버를 자동 배포하지 않는다.

실행 앱은 `backend.handoff:create_app`이다. 참고용 `kok/`, `hub/` 파일이나 개인 드라이브 서버는 배포 이미지에 넣지 않는다. 서버가 수행하는 일은 결과 저장·조회·수신 확인뿐이다.

```bash
pip install -r requirements-dev.txt
python -m pytest -q
# 비공개 KOKBOT_KEYS_FILE과 KOKBOT_DB 환경변수 설정 후
uvicorn backend.handoff:create_app --factory --host 127.0.0.1 --port 8080
```

키 파일은 `[{"name":"my-collector","role":"collector","key":"32자 이상의 임의 비밀값"}, ...]` 형식이다. 허용 역할은 collector, questioner, operator. 운영 파일은 저장소 밖에 두며 기본 비밀번호는 없다.

Docker 이미지는 비루트 사용자로 실행한다. 데이터 디렉터리는 실행 UID에 쓰기 권한, 키 파일에는 읽기 권한이 필요하다. 공개 접근은 기존 HTTPS 프록시의 `/kokbot` 경로만 사용한다. 컨테이너 DB는 이미지 밖의 `handoff.sqlite3`에 보관한다.

배포/업데이트는 필요할 때 수동 수행하고 내부·공개 health와 데이터 API를 확인한다. 업그레이드 전 SQLite backup API로 일관된 스냅샷을 만든다. 키·DB·원문·운영 설정을 공개 Git에 넣지 않는다. API를 통한 실제 두 Bot의 왕복과 실제 강의 수집은 각각 별도 검증이다.
