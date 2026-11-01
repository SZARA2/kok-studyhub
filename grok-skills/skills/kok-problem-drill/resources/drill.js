/* KokDrill v1.2.0: 모든 강의 글·보기·힌트·해설은 textContent로만 넣는다(HTML 해석 안 함).
   수식은 KaTeX auto-render(trust:false)가 텍스트 노드의 \( \)만 바꾼다. root=요소, spec=spec.json */
function KokDrill(root,spec){
  var Q=spec.questions,i=0,st=Q.map(function(){return{tried:[],done:false,first:null}}),popT=null;
  var secs=[];Q.forEach(function(q,k){if(q.s)secs.push({s:q.s,k:k})});
  function sec(k){var r=null;secs.forEach(function(x){if(x.k<=k)r=x});return r}
  function el(tag,cls,txt,attrs){var e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=String(txt);if(attrs)for(var a in attrs)e.setAttribute(a,attrs[a]);return e}
  function math(n){if(window.renderMathInElement)try{renderMathInElement(n||root,{delimiters:[{left:'\\(',right:'\\)',display:false}],throwOnError:false,trust:false})}catch(e){}}
  function btn(txt,act,dis,tid){var b=el('button',null,txt,{'data-act':act});if(tid)b.setAttribute('data-testid',tid);if(dis)b.disabled=true;b.onclick=function(){act==='next'?next():act==='prev'?prev():restart()};return b}
  function popup(ok,msg){var o=el('div','dpop '+(ok?'heart':'sorry'),null,{'data-testid':ok?'heart':'sorry',role:'status'});
    o.appendChild(el('div','ic',ok?'\u2665':'\u2026'));o.appendChild(el('div','tt',ok?'정답':'아쉬움'));o.appendChild(el('div','mm',msg));
    root.appendChild(o);math(o);clearTimeout(popT);popT=setTimeout(function(){o.classList.add('gone')},1400)}
  function render(){root.textContent='';var w=el('div','dr');root.appendChild(w);
    if(i>=Q.length){var sc=st.filter(function(x){return x.first===true}).length,c=el('div','card',null,{'data-testid':'score'});
      c.appendChild(el('div','q','점수 카드'));c.appendChild(el('p',null,'첫 시도 정답 '+sc+' / '+Q.length));var n=el('div','nav');n.appendChild(btn('이전','prev'));n.appendChild(btn('다시 시작','restart'));c.appendChild(n);w.appendChild(c);return}
    var q=Q[i],s=st[i],cs=sec(i),bar=el('div','bar'),bi=el('i');bi.style.width=(i/Q.length*100)+'%';bar.appendChild(bi);w.appendChild(bar);
    var ch=el('div','chips');secs.forEach(function(x){ch.appendChild(el('span','chip'+(cs&&cs.k===x.k?' on':''),x.s))});w.appendChild(ch);
    var c=el('div','card');c.appendChild(el('div','meta',(i+1)+' / '+Q.length+' · 출처종류: '+(q.src||'')+' · 정답출처: '+(q.ans_src||'')));
    c.appendChild(el('div','meta','원문위치: '+(q.loc||'')));c.appendChild(el('div','q',q.q,{'data-testid':'q'}));
    q.o.forEach(function(o,k){var cl=s.tried.indexOf(k)>=0?' wrong':'';if(s.done&&k===q.a)cl=' right';var b=el('button','opt'+cl,(k+1)+'. '+o,{'data-opt':k,'data-testid':'opt-'+k});b.onclick=function(){pick(k)};c.appendChild(b)});
    if(s.done)c.appendChild(el('div','pop ok','정답! '+q.ok,{'data-testid':'pop-ok'}));else if(s.tried.length)c.appendChild(el('div','pop no','오답. 힌트: '+q.no,{'data-testid':'pop-no'}));
    var n=el('div','nav');n.appendChild(btn('이전','prev',!i));n.appendChild(btn('다음','next',!s.done,'next'));c.appendChild(n);w.appendChild(c);math(w)}
  function pick(k){var q=Q[i],s=st[i];if(!q||s.done)return;var ok=k===q.a;if(ok){s.done=true;if(s.first===null)s.first=true}else{if(s.tried.indexOf(k)<0)s.tried.push(k);if(s.first===null)s.first=false}render();popup(ok,ok?q.ok:q.no)}
  function next(){if(i<Q.length&&st[i].done){i++;render()}}
  function prev(){if(i>0){i--;render()}}
  function restart(){i=0;st=Q.map(function(){return{tried:[],done:false,first:null}});render()}
  var x0=null;root.addEventListener('touchstart',function(e){x0=e.touches[0].clientX});root.addEventListener('touchend',function(e){if(x0===null)return;var d=e.changedTouches[0].clientX-x0;if(d<-50)next();if(d>50)prev();x0=null});
  render();
  return{key:function(e){var t=e.target;if(t&&(t.tagName==='INPUT'||t.tagName==='TEXTAREA'||t.tagName==='SELECT'||t.isContentEditable))return false;
    if(/^[1-4]$/.test(e.key)){pick(+e.key-1);return true}if(e.key==='ArrowRight'){next();return true}if(e.key==='ArrowLeft'){prev();return true}return false},
    state:function(){return{i:i,n:Q.length,st:st}},remath:function(){math()}}
}
