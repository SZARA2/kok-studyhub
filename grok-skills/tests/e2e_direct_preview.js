// Native bot runtime QA: one main HTML copied alone, plus independently opened media pages.
// Usage: node tests/e2e_direct_preview.js main.html lab3d.html podcast.html output-directory
const {H,chromium,CHROME}=require('./harness');
const fs=require('fs'),path=require('path'),os=require('os');
const {pathToFileURL}=require('url');
const [main,lab,podcast,out]=process.argv.slice(2).map(p=>path.resolve(p));
fs.mkdirSync(out,{recursive:true});
const isolated=fs.mkdtempSync(path.join(os.tmpdir(),'kok-main-only-'));
const lone=path.join(isolated,'index.html');fs.copyFileSync(main,lone);
const h=H('direct-preview');
async function audioChecks(page,label){
  const selector='[data-testid=audio]';
  await page.waitForFunction(()=>{const a=document.querySelector('[data-testid=audio]');return a&&a.readyState>=1},null,{timeout:20000});
  await h.ck(label+' embedded audio metadata',async()=>page.$eval(selector,a=>a.src.startsWith('data:audio/')&&Number.isFinite(a.duration)&&a.duration>1));
  await h.ck(label+' muted playback advances',async()=>{
    await page.$eval(selector,async a=>{a.muted=true;a.currentTime=0;await a.play()});
    await page.waitForTimeout(800);
    const value=await page.$eval(selector,a=>{const t=a.currentTime;a.pause();return t});return value>0.2;
  });
}
async function labChecks(frame,label){
  await frame.waitForFunction(()=>window.LAB3D&&LAB3D.status!=='loading',null,{timeout:20000});
  await h.ck(label+' actual 3D',async()=>frame.evaluate(()=>LAB3D.status==='3d'&&document.querySelectorAll('canvas').length>0));
  await h.ck(label+' slider recalculates',async()=>{
    const before=await frame.evaluate(()=>LAB3D.recomputes);
    await frame.$eval('[data-testid=slider-M]',e=>{e.value=12;e.dispatchEvent(new Event('input'))});
    await frame.waitForTimeout(400);return frame.evaluate(n=>LAB3D.recomputes>n,before);
  });
}
(async()=>{
  const browser=await chromium.launch({executablePath:CHROME,args:['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist']});
  try{
    const p=await browser.newPage({viewport:{width:1000,height:1000}});const errors=[];p.on('pageerror',e=>errors.push(e.message));
    await p.goto(pathToFileURL(lone).href);
    await p.click('[data-testid=menu-2]');await audioChecks(p,'main only');
    await p.screenshot({path:path.join(out,'main-audio.png'),fullPage:true});
    await p.click('[data-testid=home]');await p.click('[data-testid=menu-3]');
    const f=await (await p.waitForSelector('[data-testid=lab-frame]')).contentFrame();
    await labChecks(f,'main srcdoc');
    await p.screenshot({path:path.join(out,'main-3d.png'),fullPage:true});
    await h.ck('no main JavaScript errors',async()=>errors.length===0);
    await p.goto(pathToFileURL(lab).href);await labChecks(p,'separate 3D HTML');
    await p.screenshot({path:path.join(out,'separate-3d.png'),fullPage:true});
    await p.goto(pathToFileURL(podcast).href);await audioChecks(p,'separate podcast HTML');
    await p.screenshot({path:path.join(out,'separate-audio.png'),fullPage:true});
  }finally{await browser.close();h.done(path.join(out,'checks'))}
})().catch(e=>{console.error(e);process.exitCode=1});
