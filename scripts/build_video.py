import json, os, re, subprocess, textwrap
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
content=json.loads((ROOT/"content/latest.json").read_text(encoding="utf-8"))
script=content["script"].strip()
title=content["title"].strip()

work=ROOT/"build"
work.mkdir(exist_ok=True)
txt=work/"narration.txt"
wav=work/"narration.mp3"
srt=work/"captions.srt"
mp4=work/"latest.mp4"
txt.write_text(script, encoding="utf-8")

# edge-tts is free to use from the runner and does not require an API key.
subprocess.run(["edge-tts","--voice","ko-KR-SunHiNeural","--file",str(txt),"--write-media",str(wav)],check=True)

# Use ffmpeg's drawtext for readable Korean captions. The font is installed by the workflow.
# Create a simple dark background with subtle motion plus synced subtitles.
safe_script=script.replace("\\","\\\\").replace("'","\\'")
font="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
caption_filter=(
    f"drawtext=fontfile='{font}':textfile='{srt}':"
    "fontcolor=white:fontsize=58:line_spacing=12:"
    "x=(w-text_w)/2:y=h-420:box=1:boxcolor=black@0.62:boxborderw=28"
)

# Generate a subtitle file using ffmpeg's speech duration as one timed block.
probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(wav)],capture_output=True,text=True,check=True)
duration=float(probe.stdout.strip())
end=f"{int(duration//3600):02d}:{int(duration%3600//60):02d}:{duration%60:06.3f}".replace(".",",")
srt.write_text(f"1\n00:00:00,000 --> {end}\n{script}\n",encoding="utf-8")

# 1080x1920 vertical, lightweight animated background, narration and captions.
subprocess.run([
    "ffmpeg","-y","-f","lavfi","-i",
    "color=c=0x101827:s=1080x1920:r=30",
    "-i",str(wav),
    "-vf",caption_filter,
    "-t",str(duration),
    "-c:v","libx264","-preset","veryfast","-crf","28",
    "-c:a","aac","-b:a","128k","-pix_fmt","yuv420p",
    "-movflags","+faststart",str(mp4)
],check=True)

out=ROOT/"public"
out.mkdir(exist_ok=True)
(out/"latest.mp4").write_bytes(mp4.read_bytes())
meta={"title":title,"duration":duration,"source_urls":content.get("source_urls",[])}
(out/"latest.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
print(f"built {mp4} duration={duration:.1f}s")
