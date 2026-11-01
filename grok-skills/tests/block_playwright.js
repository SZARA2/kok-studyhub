// node -r ./tests/block_playwright.js <test> : playwright를 불러오려 하면 즉시 실패시켜, 순수 node 테스트가 브라우저 의존이 없음을 증명한다.
const M=require('module'),o=M._resolveFilename;M._resolveFilename=function(r,...a){if(/^playwright(-core)?(\/|$)/.test(r))throw new Error('BLOCKED playwright: 이 테스트는 브라우저 없이 돌아야 함');return o.call(this,r,...a)};
