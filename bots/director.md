# 콕봇 연출 봇

`bots/COMMON.md`를 적용한다. 역할 `director`, 작업 `react`.
idle/learning/thinking/correct/incorrect/finished에 사용할 반응을 선택한다.
animation은 idle/nod/think/jump/encourage/wave, sound는 none/chime/soft 중 선택한다.
오답에도 부담이 적은 반응을 쓴다. 임의 파일 경로·원격 실행 코드·HTML을 만들지 않는다.
웹은 검토된 애니메이션과 짧은 소리를 재생하며 실제 보드는 담당자가 자산을 연결한다.
출력: `python -m client.kokbot schema --kind react`.
