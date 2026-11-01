"""Verify the actual common UI, selected mode and complete downloadable package."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


def verify(html, package=None, require_mode=None):
    html = Path(html).resolve()
    root = html.parent
    receipt_path = root / "build-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("builder") != "kok-study-web" or receipt.get("entry") != html.name:
        raise ValueError("unknown builder or entry")
    page = html.read_text(encoding="utf-8")
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
    print("PASS common UI, selected mode, file hashes and complete ZIP")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html")
    parser.add_argument("--package")
    parser.add_argument("--require-mode", choices=["1", "2", "3", "4"])
    args = parser.parse_args()
    verify(args.html, args.package, args.require_mode)
