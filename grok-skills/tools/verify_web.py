"""Verify the actual common UI, selected mode and complete downloadable package."""
import argparse
import base64
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
import zipfile


def verify_preview(html):
    """Check a lone main HTML without requiring its job folder or archive."""
    page = Path(html).read_text(encoding="utf-8")
    match = re.search(r'var DATA=(.*?);</script>', page, re.S)
    if not match or 'data-kok-template="study-web-v1"' not in page:
        raise ValueError("common UI payload missing")
    data = json.loads(match.group(1))
    if data.get("lab3d") and (not data.get("lab3d_html") or "f.srcdoc=DATA.lab3d_html" not in page):
        raise ValueError("3D still requires a sidecar file")
    podcast = data.get("podcast")
    if podcast and podcast.get("audio"):
        inline = podcast.get("audio_inline")
        if inline:
            if not re.match(r'^data:audio/(mpeg|mp4|wav|ogg);base64,', inline):
                raise ValueError("unsupported embedded audio")
            content = base64.b64decode(inline.split(',', 1)[1], validate=True)
            if hashlib.sha256(content).hexdigest() != podcast.get("audio_sha256"):
                raise ValueError("embedded audio does not match original")
        elif podcast.get("delivery") != "separate_audio" or 'data-testid="separate-audio"' not in page:
            raise ValueError("audio still requires an unannounced sidecar")
    return data


def verify(html, package=None, require_mode=None):
    html = Path(html).resolve()
    root = html.parent
    receipt_path = root / "build-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("builder") != "kok-study-web" or receipt.get("entry") != html.name:
        raise ValueError("unknown builder or entry")
    page = html.read_text(encoding="utf-8")
    data = verify_preview(html)
    if 'data-kok-template="study-web-v1"' not in page:
        raise ValueError("common UI template missing")
    if require_mode and receipt["modes"][str(require_mode)]["status"] != "완료":
        raise ValueError("requested mode is not complete: " + str(require_mode))
    package = Path(package).resolve() if package else root / "kok-study-web.zip"
    expected = {item["path"]: item for item in receipt["files"]}
    with zipfile.ZipFile(package) as archive:
        if archive.testzip() is not None:
            raise ValueError("corrupt ZIP")
        if set(archive.namelist()) != set(expected) | {"build-receipt.json", "OPEN.txt"}:
            raise ValueError("package has missing or unexpected files")
        if archive.read("build-receipt.json") != receipt_path.read_bytes():
            raise ValueError("package receipt mismatch")
        for relative, item in expected.items():
            path = PurePosixPath(relative)
            if path.is_absolute() or ".." in path.parts or "\\" in relative:
                raise ValueError("invalid package path")
            content = (root / relative).read_bytes()
            if len(content) != item["bytes"] or hashlib.sha256(content).hexdigest() != item["sha256"]:
                raise ValueError("output changed after build: " + relative)
            if archive.read(relative) != content:
                raise ValueError("package asset mismatch: " + relative)
    if receipt["modes"]["1"]["status"] == "완료":
        if "drill/drill.html" not in expected or "drill/spec.json" not in expected or "KokDrill" not in page:
            raise ValueError("standard drill output missing")
    if receipt["modes"]["3"]["status"] == "완료" and "lab/lab3d.html" not in expected:
        raise ValueError("3D asset missing")
    if receipt["modes"]["3"]["status"] == "완료" and "lab/lab3d.html" not in {item["path"] for item in receipt.get("attachments", [])}:
        raise ValueError("direct 3D attachment missing")
    if data.get("podcast") and data["podcast"].get("audio"):
        direct = data["podcast"]["audio"]
        if direct not in {item["path"] for item in receipt.get("attachments", [])}:
            raise ValueError("direct audio attachment missing")
    print("PASS common UI, selected mode, file hashes and complete ZIP")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html")
    parser.add_argument("--package")
    parser.add_argument("--require-mode", choices=["1", "2", "3", "4"])
    parser.add_argument("--preview-only", action="store_true")
    args = parser.parse_args()
    if args.preview_only:
        verify_preview(args.html)
        print("PASS standalone HTML preview has embedded media or direct-audio delivery")
    else:
        verify(args.html, args.package, args.require_mode)
