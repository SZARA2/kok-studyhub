"""Create a browser-openable learning desk that needs no backend or HTTP server."""
from pathlib import Path
import argparse


def export(target):
    root = Path(__file__).resolve().parent.parent / 'web'
    html = (root / 'index.html').read_text(encoding='utf-8')
    css = (root / 'style.css').read_text(encoding='utf-8').replace("@import url('data:text/css,');", '')
    js = (root / 'app.js').read_text(encoding='utf-8')
    js = js.replace("sessionStorage.getItem('kokbot.key') || ''", "''")
    # Disable remote collaboration controls in the standalone artifact.
    js += "\n['connectForm','courseForm','refresh','retryAttempts'].forEach(id=>{document.getElementById(id).hidden=true;}); document.getElementById('identity').textContent='서버 없는 로컬 학습';\n"
    html = html.replace('<link rel="stylesheet" href="assets/style.css">', '<style>'+css+'</style>')
    html = html.replace('<script defer src="assets/app.js"></script>', '')
    html = html.replace('</body>', '<script>'+js.replace('</script>', '<\\/script>')+'</script></body>')
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    Path(target).write_text(html,encoding='utf-8')


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('output')
    export(parser.parse_args().output)
