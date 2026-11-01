# 실험실 설계서 JSON 형식 (lab.html 용)

설계서 하나 = 실험실 화면 하나. 흐름은 항상 1 상황 → 2 예측 → 3 실험 → 4 덮개(왜 그럴까) → 5 도전.
JSON만 쓴다. 앞뒤에 말이나 ```json 표시가 붙어도 lab.html이 { } 부분만 읽는다.
글은 한국어로, 이모지와 긴 줄표(em dash) 없이. 글 안의 `**굵게**`와 줄바꿈 `\n`은 그대로 보인다.

## 식(expr) 규칙
- 식은 JS 식 문자열. 쓸 수 있는 이름: 변수 symbol, 앞에서 정의한 formulas의 symbol, 가로축 symbol(보통 t), modes의 set 이름, `mode`(모드 번호 0부터), `playing`(재생 중이면 true).
- 수학: `Math.exp(x)`, `Math.sin(x)`, `Math.PI` 등 Math.* 전부. 짧게 `exp ln sqrt sin cos tan abs pow PI`도 된다.
- 슬라이더에 보이는 숫자가 그대로 들어간다. 단위 환산은 식 안에서 한다 (예: R이 kΩ, C가 μF이면 τ = `R*C/1000` 초).
- symbol은 영문자로 시작, 띄어쓰기 없이 (`R`, `C`, `E`, `tau`, `I0`). 그리스 글자는 `display`에 쓴다.
- 조건은 삼항식: `m==0 ? A : B`.

## 필드 (★ = 꼭 필요)
| 필드 | 형식 | 뜻 |
|---|---|---|
| ★title | 글 | 실험실 제목 |
| concept | 글 | 한 줄 개념 |
| source | {lecture, time} | 어느 강의 몇 분에서 왔는지 (머리와 맨 아래에 표시) |
| situation | 글 | 1 상황 설명 |
| ★variables | [{name, symbol, unit, min, max, step, default, display}] | 슬라이더. display는 보이는 기호(예: "ε") |
| modes | [{label, set:{이름:값}}] | 충전/방전 같은 전환 버튼. set 값이 식에 들어간다 |
| formulas | [{label, symbol, expr, unit, display, hide, digits}] | 위에서부터 차례로 계산. symbol을 주면 뒤 식에서 쓸 수 있다. display는 사람이 읽는 수식(유니코드). 실험 칸 표에 지금 값이 나온다 |
| ★plot.x | {symbol, label, unit, min, max} | 가로축. symbol이 "t"면 시간 슬라이더가 따로 생기고, 변수 symbol이면 그 슬라이더가 가로축 위치가 된다. min/max는 숫자 또는 식 |
| ★plot.y | [{label, expr, unit, color, axis}] | 곡선. axis:"right"면 오른쪽 눈금(단위가 다른 두 곡선용) |
| plot.playSeconds, plot.playLabel | 숫자, 글 | 재생 시간(초, 기본 8), 재생 버튼 글자 |
| plot.yMax, plot.y2Max, plot.ghost | 숫자/식, 식, true/false | 눈금 최댓값 고정(없으면 자동), 처음 값 곡선을 옅은 점선으로 같이 그릴지(기본 true) |
| markers | [{label, expr, color, axis}] | 점선 표시. 기본은 세로선(가로축 값, 예: τ). axis:"y"면 가로선(세로축 값) |
| bars | [{label, expr, max, unit, color}] | 병 모양 막대. 채움 = expr/max (max도 식 가능) |
| missions | [{text, check}] | 해 볼 것. check 식이 참이 되는 순간 자동 체크 |
| predict | [{question, options[], answer, why}] | 2 예측. answer는 "B"처럼 글자(A가 첫 보기). why는 덮개 안에 나온다 |
| cover | 글 또는 [글] | 4 덮개 안 설명 |
| challenge | [{question, options[], answer, hint, why}] | 5 도전. 보기형: answer "B". 숫자형: options 없이 answer 숫자, unit, tol(허용 비율, 기본 0.02) |

열리는 순서: 예측을 모두 골라 확정 → 실험 열림 → 재생하거나 값을 한 번 바꾸면 덮개 버튼 열림 → 덮개를 들추면 도전 열림.

## 가장 짧은 예시 (등가속도 운동)
```json
{
  "title": "자유낙하 실험실",
  "concept": "y = ½gt²",
  "source": {"lecture": "대학물리학1 2장", "time": "0:10:00"},
  "situation": "공을 가만히 놓으면 얼마나 떨어질까?",
  "variables": [{"name": "중력가속도", "symbol": "g", "unit": "m/s²", "min": 1, "max": 20, "step": 0.1, "default": 9.8}],
  "formulas": [{"label": "떨어진 거리", "symbol": "y", "display": "y = ½gt²", "expr": "0.5*g*t*t", "unit": "m"}],
  "plot": {"x": {"symbol": "t", "label": "시간 t", "unit": "s", "min": 0, "max": 3}, "y": [{"label": "거리 y", "expr": "y", "unit": "m"}]},
  "markers": [{"label": "1초", "expr": "1"}],
  "predict": [{"question": "시간이 2배면 거리는?", "options": ["2배", "4배", "그대로"], "answer": "B", "why": "y가 t²에 비례해서 4배."}],
  "cover": "속도가 계속 커지니까 같은 1초라도 나중 1초에 더 많이 간다.",
  "challenge": [{"question": "g = 9.8 m/s²에서 2초 동안 떨어진 거리는 몇 m?", "answer": 19.6, "unit": "m", "hint": "y = ½gt²에 t = 2"}]
}
```
긴 예시는 같은 폴더의 spec_rc.json(충전/방전 모드, 오른쪽 눈금, 미션), spec_bfield.json(가로축이 변수 r, 가로선 표시)을 본다.

## 보내는 법
1. 같은 폴더 spec.json으로 저장 (웹서버로 열 때 자동으로 읽음)
2. 주소 뒤에 `#spec=<UTF-8 JSON을 base64(또는 base64url)로 바꾼 것>`
3. 화면의 "설계서 붙여넣기" 칸에 붙이기
4. iframe으로 띄운 화면에서 `iframe.contentWindow.postMessage({type:'lab-spec', spec}, '*')` (spec은 객체나 JSON 글). 답으로 부모에게 `{type:'lab-ready'}`, `{type:'lab-rendered', ok, title 또는 error}`를 보낸다.

설계서가 틀리면 화면 위에 "설계서를 고쳐야 해:" 와 함께 어느 필드가 왜 틀렸는지 한국어로 나온다 (이전 화면은 그대로 유지).
