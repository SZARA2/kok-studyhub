/* Same-origin transport only. No model keys and no calls to an AI provider. */
(()=>{'use strict';
 const base=new URL('../',document.currentScript.src).pathname;
 const original=window.fetch.bind(window);
 window.fetch=(input,options={})=>{
   const raw=typeof input==='string'?input:input instanceof URL?input.href:null;
   if(raw!==null){let url=new URL(raw,location.href);
     if(url.origin===location.origin&&(url.pathname.startsWith('/api/')||url.pathname.startsWith(base+'api/'))){
       if(url.pathname.startsWith('/api/'))url.pathname=base+url.pathname.slice(1);
       const headers=new Headers(options.headers||{}), key=sessionStorage.getItem('kokbot.key');
       if(key)headers.set('Authorization','Bearer '+key);
       return original(url,{...options,headers});
     }
   }
   return original(input,options);
 };
 window.addEventListener('DOMContentLoaded',()=>{
   const banner=document.createElement('div');banner.style.cssText='position:fixed;bottom:0;left:0;right:0;z-index:99999;background:#263a30;color:white;padding:8px 12px;font:12px sans-serif;text-align:center;';
   const link=document.createElement('a');link.href=base;link.textContent='콕봇 작업 공간 · 팀 키 연결';link.style.color='#cce2b8';
   banner.append(link,document.createTextNode(' | '+(location.pathname.includes('/hub/')?'기존 공부판 예시 · 개인 강의 파일과 저장 서버는 포함되지 않습니다.':'실제 답변은 튜터 Grok Bot이 제출한 뒤 표시됩니다. 시연 모드는 예시입니다.')));document.body.append(banner);
 });
})();
