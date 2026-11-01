"""Create a browser-openable learning desk that needs no backend or HTTP server."""
from pathlib import Path
import argparse


def export(target):
    root = Path(__file__).resolve().parent.parent / 'web'
    html = (root / 'workspace.html').read_text(encoding='utf-8')
    css = (root / 'style.css').read_text(encoding='utf-8').replace("@import url('data:text/css,');", '')
    js = (root / 'app.js').read_text(encoding='utf-8')
    js = js.replace("sessionStorage.getItem('kokbot.key') || ''", "''")
    # Remove remote collaboration controls, including flex/grid elements whose
    # author CSS overrides the browser's default [hidden] style.
    css += '\n.grid{grid-template-columns:1fr;max-width:700px;margin:auto}[hidden]{display:none!important}\n'
    js += """
document.getElementById('courseForm').closest('.panel').remove();
['connectForm','retryAttempts'].forEach(id=>document.getElementById(id).remove());
document.getElementById('packSelect').closest('label').remove();
document.getElementById('identity').textContent='서버 없는 로컬 학습';
document.querySelector('.connection p').textContent='봇이 만든 학습팩 파일을 열고, 풀이 기록을 저장해 일정 봇에게 전달하세요.';
document.querySelector('nav').replaceChildren();
const sourceLink=document.createElement('a'); sourceLink.href='https://github.com/SZARA2/kok-studyhub'; sourceLink.textContent='봇 연결 안내 · GitHub ↗'; document.querySelector('nav').append(sourceLink);
document.querySelector('.brand').href='#';
"""
    html = html.replace('<link rel="stylesheet" href="assets/style.css">', '<style>'+css+'</style>')
    html = html.replace('<script defer src="assets/app.js"></script>', '')
    html = html.replace('</body>', '<script>'+js.replace('</script>', '<\\/script>')+'</script></body>')
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    Path(target).write_text(html,encoding='utf-8')


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('output')
    export(parser.parse_args().output)
