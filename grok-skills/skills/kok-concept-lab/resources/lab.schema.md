lab.json 필수 키: title, concept, formula, scene, variables[], outputs[] (expr, expected), graph(논리게이트 제외), objects[], predict, challenge, loc.
검산: python3 tests/regress.py lab lab.json (기본값에서 expr 계산값 == expected, 허용오차 1e-6)
