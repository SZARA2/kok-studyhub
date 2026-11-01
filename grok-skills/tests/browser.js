// 브라우저 테스트 전용. playwright는 tests/package.json의 일반 의존성(npm ci로 설치).
// 브라우저 경로: KOK_CHROME(실행 파일) > playwright 기본 경로(PLAYWRIGHT_BROWSERS_PATH 존중, `npx playwright install chromium`).
// 데모 폴더: KOK_DEMO_DIR(기본 <repo>/demo-mit6004). 모든 경로는 repo 기준 상대 경로.
const path=require('path');
const {chromium}=require('playwright');
const fs=require('fs'),os=require('os');
// 순서: KOK_CHROME > playwright 기본 경로(있으면 undefined로 두어 playwright가 고름) > 같은 캐시 폴더의 다른 chromium-* 중 최신(버전 불일치 대비, 사용 경로를 로그에 출력)
function pick(){if(process.env.KOK_CHROME)return process.env.KOK_CHROME;
 try{if(fs.existsSync(chromium.executablePath()))return undefined}catch(e){}
 const base=process.env.PLAYWRIGHT_BROWSERS_PATH||path.join(os.homedir(),'.cache','ms-playwright');
 const c=(fs.existsSync(base)?fs.readdirSync(base):[]).filter(d=>/^chromium-\d+$/.test(d)).sort((a,b)=>+b.split('-')[1]- +a.split('-')[1]).map(d=>path.join(base,d,'chrome-linux64','chrome')).find(f=>fs.existsSync(f));
 if(!c)throw new Error('Chromium 없음: `npx playwright install chromium` 또는 KOK_CHROME=<chrome 경로>');return c}
const CHROME=pick();console.log('[browser] chromium='+(CHROME||chromium.executablePath()));
const REPO=path.resolve(__dirname,'..');
const DEMO=path.resolve(REPO,process.env.KOK_DEMO_DIR||'demo-mit6004');
module.exports={chromium,CHROME,REPO,DEMO};
