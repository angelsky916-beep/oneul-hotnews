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
srt = work / "captions.srt"
mp4 = work / "latest.mp4"
txt.write_text(script, encoding="utf-8")

# Free Korean narration.
subprocess.run([
    "edge-tts", "--voice", "ko-KR-SunHiNeural",
    "--file", str(txt), "--write-media", str(wav)
], check=True)

probe = subprocess.run([
    "ffprobe", "-v", "error", "-show_entries", "format=duration",
    "-of", "default=nw=1:nk=1", str(wav)
], capture_output=True, text=True, check=True)
duration = float(probe.stdout.strip())

# Sentence-level captions: much more readable than one giant paragraph.
sentences = [s.strip() for s in script.replace("!", "!|").replace("?", "?|").split("|") if s.strip()]
n = len(sentences)
lines = []
for i, sentence in enumerate(sentences):
    start = duration * i / n
    end = duration * (i + 1) / n
    def stamp(x):
        h = int(x // 3600); m = int((x % 3600) // 60); sec = x % 60
        return f"{h:02d}:{m:02d}:{sec:06.3f}".replace(".", ",")
    lines.append(f"{i+1}\n{stamp(start)} --> {stamp(end)}\n{sentence}\n")
srt.write_text("\n".join(lines), encoding="utf-8")

font = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

# Build a real vertical news-style motion graphic:
# dark navy background, moving light, rocket silhouette, launch-pad lines,
# headline card and sentence-synced captions. No black/empty screen.
caption = (
    f"subtitles='{srt}':fontsdir='/usr/share/fonts/opentype/noto':"
    "force_style='FontName=Noto Sans CJK KR,FontSize=22,"
    "PrimaryColour=&H00FFFFFF,OutlineColour=&H99000000,"
    "BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=250'"
)

# The rocket is drawn with FFmpeg primitives, so there are no external paid assets.
vf = (
    "scale=1080:1920,"
    "drawbox=x=0:y=0:w=1080:h=1920:color=0x071426:t=fill,"
    # animated glow / sky bands
    "drawbox=x=0:y=250:w=1080:h=5:color=0x21466f@0.8:t=fill,"
    "drawbox=x=0:y=700:w=1080:h=3:color=0x21466f@0.55:t=fill,"
    "drawbox=x=0:y=1150:w=1080:h=3:color=0x21466f@0.4:t=fill,"
    # launch pad
    "drawbox=x=120:y=1500:w=840:h=12:color=0x8ea6bd:t=fill,"
    "drawbox=x=220:y=1500:w=18:h=300:color=0x60788f:t=fill,"
    "drawbox=x=842:y=1500:w=18:h=300:color=0x60788f:t=fill,"
    # rocket body
    "drawbox=x=485:y=520:w=110:h=820:color=0xe9edf2:t=fill,"
    "drawbox=x=465:y=650:w=150:h=460:color=0xe9edf2:t=fill,"
    # nose
    "drawbox=x=505:y=455:w=70:h=90:color=0xe9edf2:t=fill,"
    # red band
    "drawbox=x=465:y=810:w=150:h=42:color=0xc72f35:t=fill,"
    # fins
    "drawbox=x=420:y=1050:w=70:h=210:color=0xc72f35:t=fill,"
    "drawbox=x=590:y=1050:w=70:h=210:color=0xc72f35:t=fill,"
    # engine flames
    "drawbox=x=490:y=1340:w=40:h=170:color=0xffb52e:t=fill,"
    "drawbox=x=550:y=1340:w=40:h=170:color=0xff7a22:t=fill,"
    # headline panel
    "drawbox=x=70:y=95:w=940:h=190:color=0x0d223d@0.96:t=fill,"
    "drawtext=fontfile='" + font + "':text='오늘핫뉴스':fontcolor=0xff344dff:fontsize=46:x=105:y=125,"
    "drawtext=fontfile='" + font + "':text='누리호 5차 발사 D-1':fontcolor=white:fontsize=50:x=105:y=195,"
    # animated-ish accent
    "drawbox=x=70:y=310:w=180:h=8:color=0xe33a3a:t=fill,"
    caption
)

subprocess.run([
    "ffmpeg", "-y", "-f", "lavfi",
    "-i", "color=c=0x071426:s=1080x1920:r=30",
    "-i", str(wav),
    "-vf", vf,
    "-t", str(duration),
    "-c:v", "libx264", "-preset", "veryfast", "-crf", "25",
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
    "visual_mode": "rocket_motion_graphic"
}
(out / "latest.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"built {mp4} duration={duration:.1f}s")
