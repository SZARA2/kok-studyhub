/* 공부판에서 가져온 수식 변환기 (10/23) */
(function (g) {
  // TeX-lite -> MathML (공수 공부판용). 지원: \frac \dfrac \sqrt \int \lim \sum ^ _ \left \right \langle \rangle \text 그리스문자 등
  const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const SYM = {
    pi: ['mi', 'π'], theta: ['mi', 'θ'], alpha: ['mi', 'α'], beta: ['mi', 'β'], omega: ['mi', 'ω'], lambda: ['mi', 'λ'], mu: ['mi', 'μ'], phi: ['mi', 'φ'], Delta: ['mi', 'Δ'],
    cdot: ['mo', '·'], times: ['mo', '×'], to: ['mo', '→'], infty: ['mi', '∞'], le: ['mo', '≤'], ge: ['mo', '≥'], ne: ['mo', '≠'], pm: ['mo', '±'], approx: ['mo', '≈'],
    partial: ['mi', '∂'], Rightarrow: ['mo', '⇒'], therefore: ['mo', '∴'], langle: ['mo', '⟨'], rangle: ['mo', '⟩'], prime: ['mo', '′'], cdots: ['mo', '⋯'], ldots: ['mo', '…'],
    in: ['mo', '∈'], mid: ['mo', '|'], vert: ['mo', '|'], circ: ['mo', '∘'], checkmark: ['mo', '✓'], neq: ['mo', '≠'], leq: ['mo', '≤'], geq: ['mo', '≥'], lbrace: ['mo', '{'], rbrace: ['mo', '}'], equiv: ['mo', '≡'], sim: ['mo', '∼']
  };
  const FN = ['sin', 'cos', 'tan', 'ln', 'log', 'exp', 'sec', 'csc', 'cot'];
  function tok(s) {
    const T = []; let i = 0;
    while (i < s.length) {
      const c = s[i];
      if (c === '\\') {
        const m = /^\\([A-Za-z]+|.)/.exec(s.slice(i)); T.push({ t: 'cmd', v: m[1] }); i += m[0].length;
        if (m[1] === 'text') { // \text{...}
          let j = s.indexOf('{', i); let d = 0, k = j; for (; k < s.length; k++) { if (s[k] === '{') d++; else if (s[k] === '}') { d--; if (!d) break; } }
          T[T.length - 1] = { t: 'text', v: s.slice(j + 1, k) }; i = k + 1;
        }
        continue;
      }
      if (/\s/.test(c)) { i++; continue; }
      if (/[0-9.]/.test(c)) { const m = /^[0-9]+(\.[0-9]+)?|^\./.exec(s.slice(i)); T.push({ t: 'num', v: m[0] }); i += m[0].length; continue; }
      if (/[A-Za-z]/.test(c)) { T.push({ t: 'id', v: c }); i++; continue; }
      if ('{}^_'.includes(c)) { T.push({ t: c }); i++; continue; }
      if (c === "'") { T.push({ t: 'op', v: '′' }); i++; continue; }
      T.push({ t: /[가-힣]/.test(c) ? 'kor' : 'op', v: c }); i++;
    }
    return T;
  }
  function parse(T) {
    let p = 0;
    const group = () => { // { ... } or single atom
      if (T[p] && T[p].t === '{') { p++; const r = seq('}'); p++; return '<mrow>' + r + '</mrow>'; }
      return atom() || '<mrow></mrow>';
    };
    const atom = () => {
      const k = T[p]; if (!k) return '';
      p++;
      if (k.t === 'num') return '<mn>' + k.v + '</mn>';
      if (k.t === 'id') return '<mi>' + k.v + '</mi>';
      if (k.t === 'kor') { let v = k.v; while (T[p] && T[p].t === 'kor') v += T[p++].v; return '<mtext>' + esc(v) + '</mtext>'; }
      if (k.t === 'text') return '<mtext>' + esc(k.v).replace(/ /g, '\u00a0') + '</mtext>';
      if (k.t === 'op') { const v = k.v === '-' ? '−' : k.v;
        if (k.v === '-' || k.v === '+') { const pv = T[p - 2]; const pre = !pv || pv.t === '{' || pv.t === '^' || pv.t === '_' || (pv.t === 'op' && '([,=<>:|'.includes(pv.v)) || (pv.t === 'cmd' && ['left', 'le', 'ge', 'leq', 'geq', 'to', 'Rightarrow', 'quad', 'qquad', 'langle', ',', 'approx', 'big', 'Big'].includes(pv.v)); if (pre) return '<mo form="prefix" lspace="0" rspace="0.05em">' + v + '</mo>'; } if (v === '(' || v === ')' || v === '[' || v === ']' || v === '|') return '<mo stretchy="false" lspace="0" rspace="0">' + esc(v) + '</mo>'; return '<mo>' + esc(v) + '</mo>'; }
      if (k.t === '{') { const r = seq('}'); p++; return '<mrow>' + r + '</mrow>'; }
      if (k.t === 'cmd') {
        const v = k.v;
        if (v === 'frac' || v === 'dfrac' || v === 'tfrac') { const a = group(), b = group(); const f = '<mfrac>' + a + b + '</mfrac>'; return v === 'dfrac' ? '<mstyle displaystyle="true">' + f + '</mstyle>' : f; }
        if (v === 'sqrt') { return '<msqrt>' + group() + '</msqrt>'; }
        if (v === 'int') return '<mo largeop="true" movablelimits="false" class="mm-int">∫</mo>';
        if (v === 'sum') return '<mo largeop="true">∑</mo>';
        if (v === 'lim') return '<mo movablelimits="false">lim</mo>';
        if (FN.includes(v)) return '<mi mathvariant="normal">' + v + '</mi>' + (T[p] && T[p].t === '^' ? '' : '<mspace width="0.17em"/>');
        if (v === 'left') { const n = T[p++]; const o = n.t === 'cmd' ? (SYM[n.v] ? SYM[n.v][1] : '') : n.v; const inner = seq('RIGHT'); p++; const n2 = T[p++]; const c = n2 ? (n2.t === 'cmd' ? (SYM[n2.v] ? SYM[n2.v][1] : '') : n2.v) : ''; const F = s => (s && s !== '.') ? '<mo stretchy="true" symmetric="true" lspace="0" rspace="0">' + esc(s) + '</mo>' : ''; return '<mrow>' + F(o) + inner + F(c) + '</mrow>'; }
        if (v === 'right') { const n = T[p++]; let s = n.t === 'cmd' ? (SYM[n.v] ? SYM[n.v][1] : '') : n.v; if (s === '.') return ''; return '<mo stretchy="true" symmetric="true">' + esc(s) + '</mo>'; }
        if (v === 'big' || v === 'Big' || v === 'bigg' || v === 'Bigg') { const n = T[p++]; let s = n.t === 'cmd' ? (SYM[n.v] ? SYM[n.v][1] : '') : n.v; const sz = { big: '1.2em', Big: '1.6em', bigg: '2.1em', Bigg: '2.6em' }[v]; return '<mo stretchy="true" minsize="' + sz + '" maxsize="' + sz + '">' + esc(s) + '</mo>'; }
        if (v === 'mathbf' || v === 'vec') { const a = group(); return v === 'vec' ? '<mover accent="true">' + a + '<mo>→</mo></mover>' : a.replace(/<mi>/g, '<mi mathvariant="normal" style="font-weight:bold">'); }
        if (v === ' ' || v === '!') return v === ' ' ? '<mspace width="0.3em"/>' : '';
        if (v === 'quad') return '<mspace width="1em"/>';
        if (v === 'qquad') return '<mspace width="2em"/>';
        if (v === ',' || v === ';') return '<mspace width="0.2em"/>';
        if (v === '{' || v === '}' || v === '|' || v === '%') return '<mo>' + v + '</mo>';
        if (v === 'boxed') return '<menclose notation="box">' + group() + '</menclose>';
        if (v === 'color') { const n = T[p] && T[p].t === '{' ? (p++, T[p++]) : null; return ''; }
        if (v === 'vert' || v === 'mid') return v === 'mid' ? '<mo lspace="0.3em" rspace="0.3em">|</mo>' : '<mo stretchy="false" lspace="0.04em" rspace="0.04em">|</mo>';
        if (SYM[v]) return '<' + SYM[v][0] + '>' + SYM[v][1] + '</' + SYM[v][0] + '>';
        return '<mi>' + esc(v) + '</mi>';
      }
      if (k.t === '^' || k.t === '_') return '';
      if (k.t === '}') { p--; return ''; }
      return '';
    };
    const seq = end => {
      let out = '';
      while (p < T.length && !(end && (end === 'RIGHT' ? (T[p].t === 'cmd' && T[p].v === 'right') : T[p].t === end))) {
        let base = atom();
        // postfix scripts
        let sub = null, sup = null;
        while (T[p] && (T[p].t === '^' || T[p].t === '_')) { const w = T[p++].t; const gg = group(); if (w === '^') sup = gg; else sub = gg; }
        if (sub !== null || sup !== null) {
          const isLim = /lim<\/mo>$/.test(base);
          if (isLim) base = '<munder>' + base + (sub || '<mrow></mrow>') + '</munder>';
          else if (sub !== null && sup !== null) base = '<msubsup>' + wrap(base) + sub + sup + '</msubsup>';
          else if (sup !== null) base = '<msup>' + wrap(base) + sup + '</msup>';
          else base = '<msub>' + wrap(base) + sub + '</msub>';
        }
        if (sup !== null && /^<msup><mi mathvariant="normal">(sin|cos|tan|ln|log|sec|csc|cot)</.test(base)) base += '<mspace width="0.17em"/>';
        out += base;
      }
      return out;
    };
    const wrap = b => (/^<(mi|mn|mo|mrow|mtext)[ >][^]*<\/\1>$/.test(b) && (b.match(/<(mi|mn|mo|mrow|mtext)[ >]/g) || []).length === 1) ? b : '<mrow>' + b + '</mrow>';
    return seq(null);
  }
  g.__tex2mml = function (src, block) {
    try { return '<math' + (block === true ? ' display="block"' : ' displaystyle="true"') + '><mrow>' + parse(tok(String(src))) + '</mrow></math>'; }
    catch (e) { return '<code>' + esc(src) + '</code>'; }
  };
  // 문자열 안의 $...$ 를 수식으로 (문제판 html 만들 때)
  g.__texInline = function (s) {
    return String(s).split(/(\$[^$]+\$)/).map(seg => /^\$[^$]+\$$/.test(seg) ? g.__tex2mml(seg.slice(1, -1), false) : seg).join('');
  };
})(typeof window !== 'undefined' ? window : globalThis);

;
(g=>{ const orig=g.__tex2mml; if(!orig||orig.__w) return; const ups=s=>s.replace(/<mi>/g,'<mi mathvariant="normal">'); const inner=s=>{ const m=orig(s,false); const b=m.indexOf('<mrow>'); const e=m.lastIndexOf('</mrow></math>'); return (b<0||e<0)? '<mtext>'+s+'</mtext>' : m.slice(b+6,e); }; const W=function(src,block){ src=String(src); const re=/\\(mathrm|text|textrm|rm|operatorname|mathbf)\s*\{([^{}]*)\}/g; if(!re.test(src)) return orig(src,block); re.lastIndex=0; const parts=[]; const s2=src.replace(re,(m,cmd,body)=>{ parts.push([cmd,body]); return ' '+String.fromCharCode(0xE000+parts.length-1)+' '; }); let out=orig(s2,block); parts.forEach(([cmd,body],k)=>{ const ch=String.fromCharCode(0xE000+k); const rep= /text/.test(cmd) ? '<mtext>'+body.replace(/&/g,'&amp;').replace(/</g,'&lt;')+'</mtext>' : '<mrow>'+ups(inner(body))+'</mrow>'; out=out.replace(new RegExp('<m[ino]>'+ch+'</m[ino]>'),rep).replace(ch,rep); }); return out; }; W.__w=1; g.__tex2mml=W; })(window);

/* hub-tex-extra 10/23: 공부판 변환기에 없는 명령 보강 */
(g=>{ const o=g.__tex2mml; if(!o||o.__x) return;
  const R=[[/\\varepsilon(?![A-Za-z])/g,'ε'],[/\\epsilon(?![A-Za-z])/g,'ε'],[/\\sigma(?![A-Za-z])/g,'σ'],[/\\kappa(?![A-Za-z])/g,'κ'],[/\\iint(?![A-Za-z])/g,'∬'],[/\\(?:dots|ldots)(?![A-Za-z])/g,'…'],[/\\cdots(?![A-Za-z])/g,'⋯'],[/\\neg(?![A-Za-z])/g,'¬'],[/\\wedge(?![A-Za-z])/g,'∧'],[/\\vee(?![A-Za-z])/g,'∨'],[/\\oplus(?![A-Za-z])/g,'⊕'],[/\\Leftrightarrow(?![A-Za-z])/g,'⇔'],[/\\leftrightarrow(?![A-Za-z])/g,'↔'],[/\\bar\{([^{}]*)\}/g,'$1\u0304'],[/\\bar\s*([A-Za-z])/g,'$1\u0304']];
  const W=(s,b)=>{ s=String(s); R.forEach(([a,c])=>{ s=s.replace(a,c); }); return o(s,b); }; W.__x=1; W.__w=o.__w; g.__tex2mml=W; })(typeof window!=='undefined'?window:globalThis);
