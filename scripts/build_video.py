import json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
content = json.loads((ROOT / "content/latest.json").read_text(encoding="utf-8"))
script = content["script"].strip()
title = content["title"].strip()

work = ROOT / "build"
work.mkdir(exist_ok=True)
txt = work / "narration.txt"
wav = work / "narration.mp3"
mp4 = work / "latest.mp4"
txt.write_text(script, encoding="utf-8")

subprocess.run([
    "edge-tts", "--voice", "ko-KR-SunHiNeural",
    "--file", str(txt), "--write-media", str(wav)
], check=True)

probe = subprocess.run([
    "ffprobe", "-v", "error", "-show_entries", "format=duration",
    "-of", "default=nw=1:nk=1", str(wav)
], capture_output=True, text=True, check=True)
duration = float(probe.stdout.strip())

raw = script.replace("!", "!|").replace("?", "?|").replace(".", ".|")
sentences = [s.strip() for s in raw.split("|") if s.strip()]
n = max(1, len(sentences))
font = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

filters = [
    "scale=1080:1920",
    "drawbox=x=0:y=0:w=1080:h=1920:color=0x071426:t=fill",
    "drawbox=x=0:y=260:w=1080:h=6:color=0x294b73:t=fill",
    "drawbox=x=0:y=720:w=1080:h=4:color=0x294b73:t=fill",
    "drawbox=x=0:y=1180:w=1080:h=4:color=0x294b73:t=fill",
    "drawbox=x=105:y=1510:w=870:h=14:color=0x91a8bd:t=fill",
    "drawbox=x=205:y=1510:w=20:h=300:color=0x60788f:t=fill",
    "drawbox=x=855:y=1510:w=20:h=300:color=0x60788f:t=fill",
    "drawbox=x=465:y=560:w=150:h=760:color=0xe9edf2:t=fill",
    "drawbox=x=505:y=470:w=70:h=100:color=0xe9edf2:t=fill",
    "drawbox=x=465:y=820:w=150:h=45:color=0xc72f35:t=fill",
    "drawbox=x=415:y=1070:w=70:h=210:color=0xc72f35:t=fill",
    "drawbox=x=595:y=1070:w=70:h=210:color=0xc72f35:t=fill",
    "drawbox=x=490:y=1320:w=45:h=190:color=0xffb52e:t=fill",
    "drawbox=x=545:y=1320:w=45:h=190:color=0xff7a22:t=fill",
    "drawbox=x=70:y=90:w=940:h=205:color=0x0d223d:t=fill",
    f"drawtext=fontfile='{font}':text='오늘핫뉴스':fontcolor=0x6f8cff:fontsize=48:x=105:y=125",
    f"drawtext=fontfile='{font}':text='누리호 5차 발사 D-1':fontcolor=white:fontsize=50:x=105:y=195",
    "drawbox=x=70:y=315:w=190:h=8:color=0xe33a3a:t=fill",
]

for i, sentence in enumerate(sentences):
    start = duration * i / n
    end = duration * (i + 1) / n
    cap = work / f"caption_{i:02d}.txt"
    cap.write_text(sentence, encoding="utf-8")
    filters.append(
        f"drawtext=fontfile='{font}':textfile='{cap}':fontcolor=white:fontsize=46:"
        f"x=(w-text_w)/2:y=1640:box=1:boxcolor=0x071426:boxborderw=24:"
        f"enable='between(t,{start:.3f},{end:.3f})'"
    )

vf = ",".join(filters)

subprocess.run([
    "ffmpeg", "-y",
    "-f", "lavfi", "-i", "color=c=0x071426:s=1080x1920:r=30",
    "-i", str(wav),
    "-vf", vf,
    "-t", str(duration),
    "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
    "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p",
    "-movflags", "+faststart", str(mp4)
], check=True)

out = ROOT / "public"
out.mkdir(exist_ok=True)
(out / "latest.mp4").write_bytes(mp4.read_bytes())
meta = {
    "title": title,
    "duration": duration,
    "source_urls": content.get("source_urls", []),
    "visual_mode": "vertical_news_motion_graphic"
}
(out / "latest.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"built {mp4} duration={duration:.1f}s")
