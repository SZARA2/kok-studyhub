#!/bin/bash
# 사용: bash tests/run_all.sh  (kok-integrated 루트에서). 각 스위트 원시 로그+종료코드를 tests/logs/*.log에 저장
cd "$(dirname "$0")/.."; L=tests/logs; mkdir -p $L; F=0
D=${KOK_DEMO_DIR:-demo-mit6004}; export KOK_DEMO_DIR=$D  # 데모 폴더 바꾸기: KOK_DEMO_DIR=<폴더> bash tests/run_all.sh
[ -d tests/node_modules/playwright ] || { echo "tests/node_modules 없음: (cd tests && npm ci) 먼저"; exit 2; }
r(){ n=$1; shift; echo "# $(date '+%F %T %Z') \$ $*" > $L/$n.log; "$@" >> $L/$n.log 2>&1; e=$?; echo "exit=$e" >> $L/$n.log; echo "$n exit=$e"; [ $e -eq 0 ] || F=$((F+1)); }
r build_lab3d python3 skills/kok-concept-lab/resources/make_lab3d.py $D/lab/lab.json $D/lab/lab3d.html
r build_lab3d_bad_rejected bash -c 'rm -f /tmp/should_not_exist.html; python3 skills/kok-concept-lab/resources/make_lab3d.py tests/samples/lab_bad_expr.json /tmp/should_not_exist.html; e=$?; echo "make_lab3d exit=$e (기대 2)"; [ $e -eq 2 ] && [ ! -e /tmp/should_not_exist.html ] && echo "PASS 잘못된 식 거부, 파일 생성 안 됨"'
r build_web_demo python3 tools/build_web.py $D
r build_web_public python3 tools/build_web.py $D --out kok-web.html
r build_web_nott python3 tools/build_web.py $D --tt none --out $D/tests/no-timetable.html
r regress_all python3 tests/regress.py all $D
r negative_control node -r ./tests/block_playwright.js tests/negative_control.js
r test_safe_expr node -r ./tests/block_playwright.js tests/test_safe_expr.js
r build_web_tt_only python3 tools/build_web.py /tmp --tt-only --tt tests/samples/timetable_anon.json --sch tests/samples/schedule_tt_only.json --out tests/out/tt-only/index.html --key kok-sch-ttonly
r e2e_lab3d node tests/e2e_lab3d.js
r e2e_drill node tests/e2e_drill.js
r e2e_web_public node tests/e2e_web.js kok-web.html public
r e2e_schedule_public node tests/e2e_schedule.js kok-web.html $D/tests/no-timetable.html tests/screenshots $D/tests/expect_public.json tests/logs/e2e_schedule_public public
r e2e_tt_only node tests/e2e_tt_only.js tests/out/tt-only/index.html tests/screenshots
r partial_web python3 -m unittest discover -s tests -p test_partial_web.py -v
r verify_pack python3 tools/verify_pack.py .
r verify_pack_tamper_rejected bash -c 'T=$(mktemp -d); mkdir -p $T/p; cp -r MANIFEST.json ATTRIBUTION.md CHANGELOG.md README.md skills tools tests/*.js tests/*.py tests/*.sh tests/package*.json $T/p/ 2>/dev/null; mkdir -p $T/p/tests && cp -r tests/samples tests/*.js tests/*.py tests/*.sh tests/package*.json $T/p/tests/; rm -f $T/p/*.js $T/p/*.py $T/p/*.sh $T/p/package*.json; python3 tools/verify_pack.py $T/p >/dev/null; e0=$?; echo "// tamper" >> $T/p/skills/kok-concept-lab/resources/safe_expr.js; python3 tools/verify_pack.py $T/p | grep FAIL; e1=$?; python3 -c "import shutil,sys;shutil.make_archive(sys.argv[1],\"zip\",sys.argv[2])" $T/b $T/p; [ -f $T/b.zip ] || { echo zip 생성 실패; exit 1; }; python3 tools/verify_pack.py $T/p --zip $T/b.zip --zip-sha256 $(printf 0%.0s {1..64}) > $T/z.txt; e2=$?; cat $T/z.txt | grep "zip"; grep -q "^FAIL zip sha256" $T/z.txt || e2=99; H=$(sha256sum $T/b.zip|cut -c1-64); python3 tools/verify_pack.py $T/p --zip $T/b.zip --zip-sha256 $H >/dev/null; e3=$?; echo "zip 올바른 해시 exit=$e3(기대 1: 변조 파일 때문)"; echo "원본 사본 exit=$e0(기대 0) 변조 exit-grep=$e1 zip불일치 exit=$e2(기대 1)"; rm -rf $T; [ $e0 -eq 0 ] && [ $e1 -eq 0 ] && [ $e2 -eq 1 ] && [ $e3 -eq 1 ] && echo "PASS 변조·zip 해시 불일치 거부"'
echo "실패 스위트 $F개"; exit $((F>0))
