"""Build the common study UI from available results and package its local assets."""
import argparse
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from lecture_metadata import read_metadata

ROOT = Path(__file__).resolve().parents[1]
INLINE_AUDIO_LIMIT = 16 * 1024 * 1024


def payload(value):
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def read_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def build(job, out, timetable=None, schedule=None, key=None, tt_only=False, package=None):
    job, out = Path(job).resolve(), Path(out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    version = read_json(ROOT / "MANIFEST.json")["pack_version"]
    source = read_metadata(job / "lecture.md") if (job / "lecture.md").is_file() and not tt_only else None
    log = (job / "gen.log").read_text(encoding="utf-8").splitlines() if (job / "gen.log").is_file() else []
    assets = {out.name: out}
    attachments = {}

    def time(skill):
        matches = [line for line in log if skill in line]
        return matches[-1][:23] + " (Asia/Seoul)" if matches else "로그 없음"

    def mode(name, skill, status="미생성", label=None):
        return {"name": name, "skill": skill + " " + version, "status": status,
                "status_label": label or status, "time": time(skill)}

    def copy_asset(path, relative):
        destination = out.parent / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if path.resolve() != destination.resolve():
            shutil.copy2(path, destination)
        assets[relative] = destination
        return relative

    tt_path = Path(timetable) if timetable and timetable != "none" else job / "schedule/timetable.json"
    tt = None if timetable == "none" else read_json(tt_path)
    sch = read_json(Path(schedule) if schedule else job / "schedule/schedule.json", {"items": [], "materials": [], "note": "일정 미생성"})
    review = sum(bool(c.get("needs_review")) and not c.get("confirmed") for c in (tt or {}).get("classes", []))
    m4 = mode("일정 관리(시간표)", "kok-schedule", "완료" if tt else "시간표 필요",
              f"완료 · 확인 필요 {review}건" if tt else "시간표 필요 (이미지/PDF/텍스트 보내기)")
    missing = "자료 필요" if not source else "미생성"
    modes = {"1": mode("문제 드릴", "kok-problem-drill", missing),
             "2": mode("팟캐스트(NotebookLM)", "kok-podcast", missing),
             "3": mode("개념 실험실", "kok-concept-lab", missing), "4": m4}
    drill = lab = lab3d = lab3d_html = podcast = None

    if source:
        spec_path = job / "drill/spec.json"
        if spec_path.is_file():
            builder_path = ROOT / "skills/kok-problem-drill/resources/build.py"
            module_spec = importlib.util.spec_from_file_location("kok_drill_builder", builder_path)
            builder = importlib.util.module_from_spec(module_spec)
            module_spec.loader.exec_module(builder)
            builder.build(str(spec_path), str(out.parent / "drill"))
            drill = read_json(spec_path)
            modes["1"] = mode("문제 드릴", "kok-problem-drill", "완료")
            assets["drill/drill.html"] = out.parent / "drill/drill.html"
            copy_asset(spec_path, "drill/spec.json")

        lab_path = job / "lab/lab.json"
        if lab_path.is_file():
            lab3d_path = out.parent / "lab/lab3d.html"
            lab3d_path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run([sys.executable, str(ROOT / "skills/kok-concept-lab/resources/make_lab3d.py"),
                            str(lab_path), str(lab3d_path)], check=True)
            lab, lab3d = read_json(lab_path), "lab/lab3d.html"
            lab3d_html = lab3d_path.read_text(encoding="utf-8")
            assets[lab3d] = lab3d_path
            attachments[lab3d] = lab3d_path
            copy_asset(lab_path, "lab/lab.json")
            modes["3"] = mode("개념 실험실", "kok-concept-lab", "완료")

        status = read_json(job / "podcast/status.json")
        audio_files = sorted((job / "podcast").glob("audio.*"), key=lambda p: (p.suffix != ".mp3", p.name))
        audio_files = [p for p in audio_files if p.suffix.lower() in {".mp3", ".m4a", ".wav", ".ogg"} and p.stat().st_size]
        if status or audio_files or (job / "podcast_script.md").is_file():
            status = status or {"status": "진행중", "reason": "음원 완료 상태가 아직 확인되지 않았습니다."}
            audio = None
            audio_inline = None
            audio_digest = None
            if audio_files:
                original = audio_files[0]
                audio = copy_asset(original, "podcast/" + original.name)
                attachments[audio] = assets[audio]
                content = original.read_bytes()
                audio_digest = hashlib.sha256(content).hexdigest()
                if len(content) <= INLINE_AUDIO_LIMIT:
                    mime = {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".wav": "audio/wav", ".ogg": "audio/ogg"}[original.suffix.lower()]
                    audio_inline = "data:" + mime + ";base64," + base64.b64encode(content).decode("ascii")
                    # The single-file main HTML already carries this media in the archive.
                    assets.pop(audio)
            if status.get("status") == "완료" and not audio:
                status = dict(status, status="실패", label="실패", reason="완료 상태이나 실제 음원 파일이 없습니다.")
            status.setdefault("label", status.get("status", "진행중"))
            if not audio and status.get("label") == "완료":
                status["label"] = status["status"]
            script_path = job / "podcast_script.md"
            podcast = {"status": status, "audio": audio, "audio_inline": audio_inline,
                       "audio_sha256": audio_digest, "delivery": "embedded" if audio_inline else "separate_audio",
                       "script": script_path.read_text(encoding="utf-8") if script_path.is_file() else ""}
            if audio_inline:
                podcast_page = out.parent / "podcast.html"
                podcast_page.write_text((ROOT / "tools/podcast_template.html").read_text(encoding="utf-8").replace(
                    "/*__PODCAST__*/null", payload(podcast)), encoding="utf-8")
                attachments["podcast.html"] = podcast_page
            modes["2"] = mode("팟캐스트(NotebookLM)", "kok-podcast", status.get("status", "진행중"), status["label"])

    if source:
        copy_asset(job / "lecture.md", "lecture.md")
    if tt:
        copy_asset(tt_path, "schedule/timetable.json")
    schedule_path = Path(schedule) if schedule else job / "schedule/schedule.json"
    if schedule_path.is_file():
        copy_asset(schedule_path, "schedule/schedule.json")

    data = {"source": source, "modes": modes, "drill": drill, "lab": lab, "lab3d": lab3d,
            "lab3d_html": lab3d_html,
            "podcast": podcast, "schedule": sch, "timetable": tt,
            "storeKey": key or "kok-sch-" + hashlib.sha256(str(job).encode()).hexdigest()[:12]}
    template = (ROOT / "tools/web_template.html").read_text(encoding="utf-8")
    resources = ROOT / "skills/kok-problem-drill/resources"
    for marker, path in [("/*__MODE4CSS__*/", ROOT / "tools/mode4.css"),
                         ("/*__MODE4JS__*/", ROOT / "tools/mode4.js"),
                         ("/*__DRILLCSS__*/", resources / "drill.css"),
                         ("/*__DRILLJS__*/", resources / "drill.js")]:
        template = template.replace(marker, path.read_text(encoding="utf-8"))
    out.write_text(template.replace("/*__DATA__*/null", payload(data)), encoding="utf-8")
    receipt = {"builder": "kok-study-web", "version": version, "entry": out.name,
               "source_mode": source.get("source_mode") if source else None,
               "modes": modes, "delivery": {"lab": "srcdoc" if lab3d_html else "not_created",
                                             "audio": podcast["delivery"] if podcast and podcast["audio"] else "not_created"},
               "attachments": [{"path": rel, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                 "bytes": path.stat().st_size} for rel, path in sorted(attachments.items())],
               "files": [{"path": rel, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                            "bytes": path.stat().st_size} for rel, path in sorted(assets.items())]}
    receipt_path = out.parent / "build-receipt.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    assets[receipt_path.name] = receipt_path
    guide = out.parent / "OPEN.txt"
    guide.write_text(out.name + "은 그대로 열어 학습합니다. 3D는 HTML에 포함되고, 16MB 이하 음원도 내장됩니다.\n"
                     "별도로 제공된 lab3d.html·podcast.html·음원도 각각 바로 열 수 있습니다. ZIP은 보관용입니다.\n"
                     "16MB 초과 음원은 첨부한 음원 파일에서 바로 재생하세요. 3D와 수식은 인터넷이 필요할 수 있습니다.\n"
                     "개인 학습 자료가 포함될 수 있으므로 이 실행 묶음을 공개 템플릿에 올리지 마세요.\n", encoding="utf-8")
    assets[guide.name] = guide
    package = Path(package).resolve() if package else out.parent / "kok-study-web.zip"
    package.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        for rel, path in sorted(assets.items()):
            archive.write(path, rel)
    print("html", out)
    print("package", package)
    for relative, path in sorted(attachments.items()):
        print("direct_attachment", path)
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("d")
    parser.add_argument("--tt")
    parser.add_argument("--sch")
    parser.add_argument("--out")
    parser.add_argument("--key")
    parser.add_argument("--tt-only", action="store_true")
    parser.add_argument("--package")
    args = parser.parse_args()
    build(args.d, args.out or str(Path(args.d) / "web/index.html"), args.tt, args.sch,
          args.key, args.tt_only, args.package)
