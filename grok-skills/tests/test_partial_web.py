"""Independent-mode and portable-output regression scenarios. No browser required."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import wave
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_web import build
from verify_web import verify


class PartialWebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="kok-partial-")
        self.addCleanup(self.temp.cleanup)
        self.job = Path(self.temp.name) / "job"
        self.job.mkdir()
        self.out = self.job / "web/index.html"

    def put(self, relative, content):
        path = self.job / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(content, ensure_ascii=False) if isinstance(content, dict) else content, encoding="utf-8")

    def lecture(self):
        self.put("lecture.md", "# Topic\nsource_mode: topic_generated\ncoverage: complete\nhttps://example.com/not-a-collected-source\n")

    def drill(self):
        self.lecture()
        self.put("drill/spec.json", {"title": "Topic", "questions": [
            {"q": "2 + 2?", "o": ["1", "2", "3", "4"], "a": 3, "ok": "2 + 2 = 4",
             "no": "Add two pairs", "src": "주제 기반 Bot 작성", "ans_src": "Bot 풀이", "loc": "lecture.md C1"}]})

    def run_build(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return build(self.job, self.out, **kwargs)

    def test_quiz_only_does_not_need_other_mode_files_or_gen_log(self):
        self.drill()
        data = self.run_build()
        self.assertEqual(data["modes"]["1"]["status"], "완료")
        self.assertEqual(data["modes"]["2"]["status"], "미생성")
        self.assertEqual(data["modes"]["3"]["status"], "미생성")
        self.assertIsNone(data["podcast"])
        self.assertIsNone(data["lab3d"])
        verify(self.out, require_mode=1)

    def test_topic_provenance_survives_and_does_not_invent_source_link(self):
        self.drill()
        data = self.run_build()
        self.assertEqual(data["source"]["source_mode"], "topic_generated")
        self.assertIn("강의 원문 미제공", data["source"]["source_label"])
        self.assertEqual(data["source"]["url"], "")

    def test_schedule_only_without_lecture(self):
        timetable = json.loads((ROOT / "tests/samples/timetable_anon.json").read_text(encoding="utf-8"))
        self.put("schedule/timetable.json", timetable)
        data = self.run_build()
        self.assertIsNone(data["source"])
        self.assertEqual(data["modes"]["4"]["status"], "완료")
        self.assertEqual(data["modes"]["1"]["status"], "자료 필요")
        verify(self.out, require_mode=4)

    def test_podcast_login_state_without_quiz_or_lab(self):
        self.lecture()
        self.put("podcast/status.json", {"status": "미연결", "reason": "Login required for audio only"})
        data = self.run_build()
        self.assertEqual(data["modes"]["2"]["status"], "미연결")
        self.assertEqual(data["modes"]["1"]["status"], "미생성")
        verify(self.out)

    def test_complete_podcast_without_audio_is_not_success(self):
        self.lecture()
        self.put("podcast/status.json", {"status": "완료", "label": "완료 · 생성됨"})
        data = self.run_build()
        self.assertEqual(data["modes"]["2"]["status"], "실패")
        self.assertEqual(data["modes"]["2"]["status_label"], "실패")
        with self.assertRaises(ValueError):
            verify(self.out, require_mode=2)

    def test_audio_is_packaged_and_survives_moving_extracted_folder(self):
        self.lecture()
        self.put("podcast/status.json", {"status": "완료", "title": "Synthetic test tone"})
        with wave.open(str(self.job / "podcast/audio.wav"), "wb") as audio:
            audio.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
            audio.writeframes(b"\0\0" * 800)
        self.run_build()
        destination = Path(self.temp.name) / "moved"
        with zipfile.ZipFile(self.out.parent / "kok-study-web.zip") as archive:
            archive.extractall(destination)
        shutil.copy2(self.out.parent / "kok-study-web.zip", destination / "kok-study-web.zip")
        verify(destination / "index.html", require_mode=2)
        self.assertGreater((destination / "podcast/audio.wav").stat().st_size, 44)

    def test_lab_only_uses_standard_builder_and_packages_3d(self):
        self.lecture()
        self.put("lab/lab.json", json.loads((ROOT / "skills/kok-concept-lab/resources/examples/generic_info_bars.json").read_text(encoding="utf-8")))
        data = self.run_build()
        self.assertEqual(data["modes"]["3"]["status"], "완료")
        self.assertEqual(data["modes"]["1"]["status"], "미생성")
        verify(self.out, require_mode=3)

    def test_missing_packaged_asset_is_rejected(self):
        self.drill()
        self.run_build()
        package = self.out.parent / "kok-study-web.zip"
        with zipfile.ZipFile(package) as archive:
            contents = {n: archive.read(n) for n in archive.namelist() if n != "drill/drill.html"}
        with zipfile.ZipFile(package, "w") as archive:
            for name, content in contents.items():
                archive.writestr(name, content)
        with self.assertRaises(ValueError):
            verify(self.out)

    def test_changed_html_is_rejected(self):
        self.drill()
        self.run_build()
        self.out.write_text("<!doctype html><p>Arbitrary quiz</p>", encoding="utf-8")
        with self.assertRaises(ValueError):
            verify(self.out)

    def test_hintless_quiz_is_rejected(self):
        self.drill()
        spec = json.loads((self.job / "drill/spec.json").read_text(encoding="utf-8"))
        del spec["questions"][0]["no"]
        self.put("drill/spec.json", spec)
        with self.assertRaises(ValueError):
            self.run_build()


if __name__ == "__main__":
    unittest.main()
