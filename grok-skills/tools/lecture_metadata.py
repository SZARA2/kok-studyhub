"""Read display metadata from the current lecture, preserving unknown fields."""
from pathlib import Path
import re


def read_metadata(path):
    text = Path(path).read_text(encoding="utf-8")
    lines = text.splitlines()
    heading = next((s.lstrip("# ").strip() for s in lines if s.startswith("# ")), "강의 자료")
    heading = re.sub(r"^lecture\.md\s*[—–:-]\s*", "", heading)
    urls = re.findall(r"https?://[^\s<>)\]]+", text)
    coverage = re.search(r"coverage:\s*([a-z_]+)", text)
    missing = []
    in_missing = False
    for line in lines:
        if line.startswith("## "):
            in_missing = "누락" in line or "제외" in line
        elif in_missing and line.startswith("- "):
            missing.append(line[2:])
    observed = next((s[2:] for s in lines[:15] if s.startswith("- ") and ("확인 시각" in s or "수집 시각" in s)), "collect.log 참조")
    return {"title": heading, "url": urls[0] if urls else "", "coverage": coverage.group(1) if coverage else "unknown", "collected": observed, "missing": missing}
