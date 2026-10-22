"""检查评审材料的实际格式、内容、时长和可选的 GitHub 公开访问。"""

import argparse
import json
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

import imageio_ffmpeg
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online", action="store_true", help="匿名检查 GitHub 公开交付文件")
    args = parser.parse_args()
    required = [
        "README.md",
        ".env.example",
        "requirements.txt",
        "requirements-docker.txt",
        "frontend/package-lock.json",
        "docs/交付检查清单.md",
        "docs/验收测试报告.md",
        "output/pdf/智慧医疗系统技术文档.pdf",
        "output/video/智慧医疗系统演示.mp4",
        "output/video/智慧医疗系统演示.srt",
        "output/video/demo-evidence.json",
    ]
    for relative in required:
        if not (ROOT / relative).is_file():
            raise FileNotFoundError(relative)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for name in ("高秋雨", "栾子璇", "郝崇泽"):
        if name not in readme:
            raise ValueError("README missing team member: " + name)
    pdf = PdfReader(ROOT / required[7])
    if not 1 <= len(pdf.pages) <= 30:
        raise ValueError("PDF page count exceeds requirement")
    text = re.sub(r"\s+", "", "".join(page.extract_text() for page in pdf.pages))
    for heading in (
        "项目概述",
        "需求分析",
        "系统架构设计",
        "选型理由",
        "集成流程",
        "优化策略",
        "核心功能实现",
        "测试验证",
        "部署与维护",
        "技术创新",
        "应用创新",
        "总结与展望",
    ):
        if heading not in text:
            raise ValueError("PDF missing required topic: " + heading)
    video_path = ROOT / required[8]
    reader = imageio_ffmpeg.read_frames(str(video_path))
    try:
        media = next(reader)
    finally:
        reader.close()
    if tuple(media["size"]) != (1920, 1080) or not 300 <= media["duration"] <= 480:
        raise ValueError("Video resolution or duration does not meet requirement")
    if video_path.stat().st_size >= 100_000_000:
        raise ValueError("Video too large for planned GitHub delivery")
    audio_info = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(video_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stderr
    if "Audio: aac" not in audio_info or "Video: h264" not in audio_info:
        raise ValueError("Expected H.264 video and AAC narration")
    evidence = json.loads((ROOT / required[10]).read_text(encoding="utf-8"))
    if evidence["ai_mode"] != "real-configured-clients" or len(evidence["events"]) != 8:
        raise ValueError("Real demo evidence incomplete")
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    risky = []
    for relative in filter(None, tracked):
        path = ROOT / relative
        if path.suffix.lower() in (".png", ".pdf", ".mp4", ".ico"):
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(
            r"sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}",
            content,
        ):
            risky.append(relative)
    if ".env" in tracked or risky:
        raise ValueError("Credential scan requires review: " + ", ".join(risky))
    result = {
        "pdf_pages": len(pdf.pages),
        "video_seconds": media["duration"],
        "video_resolution": list(media["size"]),
        "narration": "AAC / Mandarin synthetic speech",
        "subtitles": "burned-in + SRT",
        "synthetic_demo_events": len(evidence["events"]),
        "tracked_credential_patterns": 0,
        "online_demo": "omitted by user",
    }
    if args.online:
        base = "https://api.github.com/repos/gaoqiuyu9579/RAG-medical-system"
        with urllib.request.urlopen(base, timeout=20) as response:
            repository = json.load(response)
        if repository["private"]:
            raise ValueError("Repository is not public")
        for relative in (required[7], required[8], required[9]):
            with urllib.request.urlopen(
                base + "/contents/" + urllib.parse.quote(relative), timeout=20
            ) as response:
                info = json.load(response)
            if info["size"] != (ROOT / relative).stat().st_size or not info["download_url"]:
                raise ValueError("Public asset missing or out of date: " + relative)
        result["github"] = repository["html_url"]
        result["public_assets"] = "PDF / MP4 / SRT verified anonymously"
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
