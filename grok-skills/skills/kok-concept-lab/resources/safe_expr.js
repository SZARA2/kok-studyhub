/* SafeExpr: lab expr 전용 토크나이저·파서. 문자열을 코드로 실행하지 않는다.
   허용: 숫자, 선언된 변수 이름, + - * / % **(^ 아님), 단항 + -, 괄호, Math.<허용 함수>(...)/Math.PI/Math.E, 쉼표(함수 인자).
   그 밖(문자열, 대입, =>, [], {}, ., 다른 이름 호출, window/document/constructor 등)은 Error로 거부하고 실행하지 않는다.
   결과는 클로저로 컴파일되어 (식,이름집합) 단위로 캐시된다. */
(function(G){
var F={pow:pw2,log2:Math.log2,log:Math.log,log10:Math.log10,exp:Math.exp,sqrt:Math.sqrt,abs:Math.abs,ceil:Math.ceil,floor:Math.floor,round:Math.round,min:Math.min,max:Math.max,sin:Math.sin,cos:Math.cos,tan:Math.tan,atan:Math.atan,atan2:Math.atan2};
var K={PI:Math.PI,E:Math.E},cache=Object.create(null);
var LIM={len:300,depth:32,nodes:200,exp:64};
function fin(x,w){if(typeof x!=='number'||!isFinite(x))throw Error('유한하지 않은 '+w+' ('+x+')');return x}
function pw2(a,b){if(Math.abs(b)>LIM.exp)throw Error('지수 상한 초과 |'+b+'|>'+LIM.exp);return Math.pow(a,b)}
function own(o,k){return Object.prototype.hasOwnProperty.call(o,k)}
function lex(s){var t=[],i=0,m;if(typeof s!=='string'||!s.trim())throw Error('빈 식');if(s.length>LIM.len)throw Error('식 길이 상한 초과 '+s.length+'>'+LIM.len);
 while(i<s.length){var c=s[i];if(c===' '||c==='\t'){i++;continue}
  if((m=/^(\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)/.exec(s.slice(i)))){t.push({k:'n',v:parseFloat(m[1])});i+=m[1].length;continue}
  if((m=/^Math\.([A-Za-z0-9]+)/.exec(s.slice(i)))){t.push({k:'m',v:m[1]});i+=m[0].length;continue}
  if((m=/^[A-Za-z_][A-Za-z0-9_]*/.exec(s.slice(i)))){t.push({k:'id',v:m[0]});i+=m[0].length;continue}
  if(s.substr(i,2)==='**'){t.push({k:'op',v:'**'});i+=2;continue}
  if('+-*/%(),'.indexOf(c)>=0){t.push({k:'op',v:c});i++;continue}
  throw Error('허용되지 않은 문자 '+JSON.stringify(c)+' (위치 '+i+')')}
 return t}
function parse(src,names){var T=lex(src),p=0,dep=0,nodes=0;
 function nd(){if(++nodes>LIM.nodes)throw Error('노드 수 상한 초과 >'+LIM.nodes)}
 function pk(v){return T[p]&&T[p].k==='op'&&T[p].v===v}
 function ex(v){if(!pk(v))throw Error("'"+v+"' 필요");p++}
 function bin(o,x,y){nd();return o==='+'?function(e){return x(e)+y(e)}:o==='-'?function(e){return x(e)-y(e)}:o==='*'?function(e){return x(e)*y(e)}:o==='/'?function(e){return x(e)/y(e)}:function(e){return x(e)%y(e)}}
 function add(){var a=mul();while(pk('+')||pk('-')){var o=T[p++].v;a=bin(o,a,mul())}return a}
 function mul(){var a=un();while(pk('*')||pk('/')||pk('%')){var o=T[p++].v;a=bin(o,a,un())}return a}
 function un(){if(++dep>LIM.depth)throw Error('깊이 상한 초과 >'+LIM.depth);try{if(pk('-')){p++;nd();var a=un();return function(e){return -a(e)}}if(pk('+')){p++;return un()}return pw()}finally{dep--}}
 function pw(){var a=at();if(pk('**')){p++;var b=un();nd();return function(e){return pw2(a(e),b(e))}}return a}
 function at(){var t=T[p];if(!t)throw Error('식이 덜 끝남');nd();
  if(t.k==='n'){p++;var v=t.v;return function(){return v}}
  if(t.k==='id'){if(!own(names,t.v))throw Error('선언 안 된 이름 '+t.v);p++;var k=t.v;if(pk('('))throw Error('허용되지 않은 호출 '+k);return function(e){return fin(+e[k],'입력 '+k)}}
  if(t.k==='m'){p++;if(own(K,t.v)&&!pk('(')){var c=K[t.v];return function(){return c}}
   if(!own(F,t.v))throw Error('허용되지 않은 Math.'+t.v);var f=F[t.v],args=[];ex('(');if(!pk(')')){args.push(add());while(pk(',')){p++;args.push(add())}}ex(')');
   return function(e){var a=[];for(var i=0;i<args.length;i++)a.push(args[i](e));return f.apply(null,a)}}
  if(pk('(')){p++;var a=add();ex(')');return a}
  throw Error('예상 밖 기호 '+t.v)}
 var r=add();if(p!==T.length)throw Error('남은 기호 '+(T[p].v));return function(e){return fin(r(e),'결과')}}
function compile(src,nameList){var names=Object.create(null);(nameList||[]).forEach(function(n){names[n]=1});
 var key=src+'\u0000'+(nameList||[]).join(',');if(cache[key])return cache[key];var f=parse(src,names);cache[key]=f;return f}
var API={LIMITS:LIM,compile:compile,check:function(src,n){try{compile(src,n);return null}catch(e){return e.message}},cacheSize:function(){return Object.keys(cache).length}};
if(typeof module!=='undefined'&&module.exports)module.exports=API;else G.SafeExpr=API;
})(this);
