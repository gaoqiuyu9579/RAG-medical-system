"""合成真实浏览器片段、普通话配音、字幕和讲解页，输出 1080p MP4。"""

import json
import re
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "output/video"
TEMP = ROOT / "tmp/video"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FONT = Path("C:/Windows/Fonts/msyh.ttc")
BOLD = Path("C:/Windows/Fonts/msyhbd.ttc")


def font(size, bold=False):
    return ImageFont.truetype(str(BOLD if bold else FONT), size)


def execute(arguments):
    result = subprocess.run(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode:
        raise RuntimeError(result.stderr[-4000:])


def slide(chapter):
    image = Image.new("RGB", (1920, 1080), "#102a40")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 24, 1080), fill="#31c4be")
    draw.rounded_rectangle((1440, -130, 2150, 580), radius=210, fill="#143a50")
    draw.text((110, 84), "RAG MEDICAL SYSTEM  /  PROJECT REVIEW", font=font(24), fill="#67d9d1")
    draw.text((105, 167), chapter["title"], font=font(62, True), fill="#ffffff")
    draw.line((110, 274, 465, 274), fill="#31c4be", width=5)
    start = 345 if len(chapter["lines"]) <= 4 else 323
    for index, line in enumerate(chapter["lines"]):
        y = start + index * 108
        draw.rounded_rectangle((113, y + 12, 123, y + 46), radius=3, fill="#31c4be")
        draw.text((154, y), line, font=font(39), fill="#e3eef5")
    draw.text(
        (110, 924),
        "智慧医疗问诊平台  |  合成数据演示  |  2026-10-22",
        font=font(24),
        fill="#92afc0",
    )
    draw.text((1735, 916), chapter["id"] + " / 12", font=font(30), fill="#67d9d1")
    path = TEMP / (chapter["id"] + ".png")
    image.save(path)
    return path


def header(chapter):
    image = Image.new("RGBA", (1920, 64), "#102a40")
    draw = ImageDraw.Draw(image)
    draw.text(
        (28, 12), chapter["id"] + "  " + chapter["title"], font=font(29, True), fill="#ffffff"
    )
    draw.text(
        (1335, 18), "本机隔离演示  |  合成资料  |  真实 AI 服务", font=font(21), fill="#67d9d1"
    )
    path = TEMP / (chapter["id"] + "-header.png")
    image.save(path)
    return path


def phrases(text):
    parts = re.findall(r"[^，。；！？：]+[，。；！？：]?", text)
    output = []
    current = ""
    for part in parts:
        if len(current) + len(part) <= 38:
            current += part
        else:
            if current:
                output.append(current)
            while len(part) > 38:
                output.append(part[:38])
                part = part[38:]
            current = part
    if current:
        output.append(current)
    return output


def stamp(seconds, ass=False):
    hour = int(seconds // 3600)
    minute = int(seconds % 3600 // 60)
    second = seconds % 60
    return (
        f"{hour}:{minute:02d}:{second:05.2f}"
        if ass
        else f"{hour:02d}:{minute:02d}:{int(second):02d},{int(second % 1 * 1000):03d}"
    )


def subtitles(chapter, speech_seconds, offset, srt_entries):
    parts = phrases(chapter["narration"])
    characters = sum(map(len, parts))
    position = 0.05
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1920",
        "PlayResY: 1080",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Microsoft YaHei,34,&H00FFFFFF,&H00FFFFFF,&H00102030,&H80102030,0,0,0,0,100,100,0,0,1,1,0,2,70,70,18,1",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for part in parts:
        end = min(speech_seconds, position + (speech_seconds - 0.05) * len(part) / characters)
        lines.append(
            f"Dialogue: 0,{stamp(position, True)},{stamp(end, True)},Default,,0,0,0,,{part}"
        )
        srt_entries.append((offset + position, offset + end, part))
        position = end
    path = TEMP / (chapter["id"] + ".ass")
    path.write_text("\n".join(lines), encoding="utf-8-sig")
    return path.relative_to(ROOT).as_posix()


def main():
    TEMP.mkdir(parents=True, exist_ok=True)
    segments = VIDEO / "segments"
    segments.mkdir(parents=True, exist_ok=True)
    chapters = json.loads((ROOT / "docs/video_storyboard.json").read_text(encoding="utf-8"))
    offset = 0.0
    srt = []
    chapters_metadata = []
    for chapter in chapters:
        identifier = chapter["id"]
        audio = VIDEO / "audio" / (identifier + ".wav")
        with wave.open(str(audio)) as wav:
            speech_seconds = wav.getnframes() / wav.getframerate()
        duration = round(max(float(chapter["duration"]), speech_seconds + 1.2), 2)
        subtitle_path = subtitles(chapter, speech_seconds, offset, srt)
        destination = segments / (identifier + ".mp4")
        common_filter = (
            f"drawbox=x=0:y=1000:w=1920:h=80:color=0x102a40:t=fill,ass='{subtitle_path}'"
        )
        if chapter["kind"] == "slide":
            picture = slide(chapter)
            arguments = [
                "-loop",
                "1",
                "-framerate",
                "25",
                "-i",
                str(picture),
                "-i",
                str(audio),
                "-vf",
                common_filter,
                "-map",
                "0:v",
                "-map",
                "1:a",
            ]
        else:
            clip = VIDEO / "raw" / (identifier + ".webm")
            banner = header(chapter)
            filters = (
                f"[0:v]fps=25,scale=1920:936,pad=1920:1080:0:64:color=0x102a40,"
                f"tpad=stop_mode=clone:stop_duration=120[v];[v][2:v]overlay=0:0,"
                f"{common_filter}[out]"
            )
            arguments = [
                "-i",
                str(clip),
                "-i",
                str(audio),
                "-i",
                str(banner),
                "-filter_complex",
                filters,
                "-map",
                "[out]",
                "-map",
                "1:a",
            ]
        arguments += [
            "-af",
            "apad",
            "-t",
            str(duration),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "25",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(destination),
        ]
        execute(arguments)
        chapters_metadata.append(
            {
                "id": identifier,
                "title": chapter["title"],
                "start": round(offset, 2),
                "duration": duration,
                "speech_seconds": round(speech_seconds, 2),
                "footage": "real-browser-capture"
                if chapter["kind"] == "capture"
                else "explanation-slide",
            }
        )
        offset += duration
        print(f"Rendered chapter {identifier}: {duration:.2f}s", flush=True)
    if not 300 <= offset <= 480:
        raise ValueError(f"Video duration outside 5-8 minutes: {offset:.2f}s")
    playlist = TEMP / "concat.txt"
    playlist.write_text(
        "\n".join(
            "file '" + (segments / (item["id"] + ".mp4")).as_posix() + "'" for item in chapters
        ),
        encoding="utf-8",
    )
    destination = VIDEO / "智慧医疗系统演示.mp4"
    execute(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(playlist),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(destination),
        ]
    )
    if destination.stat().st_size >= 100_000_000:
        raise ValueError("Video exceeds conservative GitHub single-file size budget")
    srt_text = "\n\n".join(
        f"{i}\n{stamp(start)} --> {stamp(end)}\n{text}"
        for i, (start, end, text) in enumerate(srt, 1)
    )
    (VIDEO / "智慧医疗系统演示.srt").write_text(srt_text + "\n", encoding="utf-8-sig")
    metadata = {
        "duration_seconds": round(offset, 2),
        "width": 1920,
        "height": 1080,
        "fps": 25,
        "video_codec": "H.264",
        "audio_codec": "AAC",
        "language": "zh-CN",
        "narration": "Microsoft Huihui Desktop / Mandarin synthetic speech",
        "subtitles": "burned-in and external UTF-8 SRT",
        "size_bytes": destination.stat().st_size,
        "editing": "Browser actions followed by held final frames for narration; no mocked API responses",
        "chapters": chapters_metadata,
    }
    (VIDEO / "video-metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    execute(["-ss", "5", "-i", str(destination), "-frames:v", "1", str(VIDEO / "演示封面.png")])
    print(
        json.dumps(
            {"duration_seconds": offset, "size_bytes": destination.stat().st_size},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
