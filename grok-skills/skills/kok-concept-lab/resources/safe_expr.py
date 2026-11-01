"""lab expr 안전 계산기(AST 허용목록). 실행 전에 모든 노드를 검사하고, 허용 밖이면 ValueError로 거부(실행하지 않음).
허용: 숫자 상수, 선언된 변수 이름(+t 등 넘겨준 이름), + - * / ** %, 단항 + -, 괄호, Math.<허용 함수/상수>(...).
eval/exec/compile을 쓰지 않는다."""
import ast,math
LIMITS={'len':300,'depth':32,'nodes':200,'exp':64}
def _fin(x,w):
    if not isinstance(x,(int,float)) or not math.isfinite(x):raise ValueError(f'유한하지 않은 {w} ({x})')
    return float(x)
def _pow(a,b):
    if abs(b)>LIMITS['exp']:raise ValueError(f'지수 상한 초과 |{b}|>{LIMITS["exp"]}')
    return math.pow(a,b)
FUNCS={'log2':math.log2,'log':math.log,'log10':math.log10,'exp':math.exp,'sqrt':math.sqrt,'pow':_pow,'abs':abs,'ceil':math.ceil,'floor':math.floor,
       'round':lambda x:math.floor(x+0.5),'min':min,'max':max,'sin':math.sin,'cos':math.cos,'tan':math.tan,'atan':math.atan,'atan2':math.atan2}
CONSTS={'PI':math.pi,'E':math.e}
BIN={ast.Add:lambda a,b:a+b,ast.Sub:lambda a,b:a-b,ast.Mult:lambda a,b:a*b,ast.Div:lambda a,b:a/b,ast.Pow:_pow,ast.Mod:lambda a,b:math.fmod(a,b)}
UN={ast.UAdd:lambda a:+a,ast.USub:lambda a:-a}
def _js2py(e):
    if not isinstance(e,str) or not e.strip():raise ValueError('빈 식')
    if any(s in e for s in ('=>','=','__',';','[',']','{','}','"',"'",'`','\\','lambda')):
        # 비교(<=,>=,==)·대입·화살표·문자열·첨자 모두 거부
        raise ValueError('허용되지 않은 기호')
    return e
def compile_expr(e,names):
    """names: 허용 변수 이름 집합. 반환: env->float 함수. 허용 밖이면 ValueError."""
    if isinstance(e,str) and len(e)>LIMITS['len']:raise ValueError(f"식 길이 상한 초과 {len(e)}>{LIMITS['len']}")
    try:tree=ast.parse(_js2py(e),mode='eval')
    except (SyntaxError,RecursionError,MemoryError) as x:raise ValueError(f'구문 오류 {type(x).__name__}')
    cnt=[0]
    def walk(n,d):
        if d>LIMITS['depth']:raise ValueError(f"깊이 상한 초과 >{LIMITS['depth']}")
        if not isinstance(n,(ast.Load,ast.operator,ast.unaryop,ast.Expression)):
            cnt[0]+=1
            if cnt[0]>LIMITS['nodes']:raise ValueError(f"노드 수 상한 초과 >{LIMITS['nodes']}")
        for c in ast.iter_child_nodes(n):walk(c,d+1)
    walk(tree,0)
    def chk(n):
        if isinstance(n,ast.Expression):return chk(n.body)
        if isinstance(n,ast.Constant) and type(n.value) in(int,float):v=float(n.value);return lambda env:v
        if isinstance(n,ast.Name):
            if n.id not in names:raise ValueError(f'선언 안 된 이름 {n.id}')
            k=n.id;return lambda env:_fin(env[k],'입력 '+k)
        if isinstance(n,ast.BinOp) and type(n.op) in BIN:
            f=BIN[type(n.op)];a=chk(n.left);b=chk(n.right);return lambda env:f(a(env),b(env))
        if isinstance(n,ast.UnaryOp) and type(n.op) in UN:
            f=UN[type(n.op)];a=chk(n.operand);return lambda env:f(a(env))
        if isinstance(n,ast.Attribute) and isinstance(n.value,ast.Name) and n.value.id=='Math' and n.attr in CONSTS:
            v=CONSTS[n.attr];return lambda env:v
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='Math' and n.func.attr in FUNCS and not n.keywords:
            f=FUNCS[n.func.attr];args=[chk(x) for x in n.args];return lambda env:float(f(*[x(env) for x in args]))
        raise ValueError(f'허용되지 않은 구문 {type(n).__name__}')
    f=chk(tree)
    def run(env):
        try:r=f(env)
        except (OverflowError,ZeroDivisionError) as x:raise ValueError(f'계산 오류 {type(x).__name__}')
        return _fin(r,'결과')
    return run
def evaluate(e,env):return compile_expr(e,set(env))(env)
