import json, subprocess, urllib.request, urllib.parse, re
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
content = json.loads((ROOT / "content/latest.json").read_text(encoding="utf-8"))
script = content["script"].strip()
title = content["title"].strip()

work = ROOT / "build"
work.mkdir(exist_ok=True)
imgdir = work / "news_images"
imgdir.mkdir(exist_ok=True)
txt = work / "narration.txt"
wav = work / "narration.mp3"
slideshow = work / "slideshow.mp4"
mp4 = work / "latest.mp4"
txt.write_text(script, encoding="utf-8")

subprocess.run(["edge-tts", "--voice", "ko-KR-SunHiNeural", "--file", str(txt), "--write-media", str(wav)], check=True)

probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(wav)], capture_output=True, text=True, check=True)
duration = float(probe.stdout.strip())

raw = re.sub(r"([.!?])", r"\1|", script)
sentences = [s.strip() for s in raw.split("|") if s.strip()]
font = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

class ImgParser(HTMLParser):
    def __init__(self, base):
        super().__init__()
        self.base, self.urls = base, []
    def handle_starttag(self, tag, attrs):
        if tag.lower() != "img": return
        a = dict(attrs)
        src = a.get("src") or a.get("data-src") or a.get("data-original")
        if src: self.urls.append(urllib.parse.urljoin(self.base, src))

pages = [
    "https://www.kari.re.kr/kor/article/ATCL87374b48c/18726",
    "https://www.kari.re.kr/kor/article/ATCL87374b48c/18705",
    "https://www.kari.re.kr/kor/article/ATCL87374b48c/18717",
]
urls, seen = [], set()
for page in pages:
    try:
        req = urllib.request.Request(page, headers={"User-Agent":"Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
        p = ImgParser(page); p.feed(html)
        for u in p.urls:
            if u not in seen and re.search(r"\.(jpg|jpeg|png|webp)(?:\?|$)", u, re.I):
                seen.add(u); urls.append(u)
    except Exception as e:
        print("image page skip:", page, e)

images = []
for i, u in enumerate(urls[:24]):
    try:
        ext = "." + re.search(r"\.(jpg|jpeg|png|webp)", u, re.I).group(1).lower().replace("jpeg","jpg")
        path = imgdir / f"img_{i:02d}{ext}"
        req = urllib.request.Request(u, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r, open(path, "wb") as f: f.write(r.read())
        if path.stat().st_size > 15000: images.append(path)
    except Exception as e:
        print("image skip:", u, e)

if not images:
    raise RuntimeError("No KARI images could be downloaded; refusing to create a blank video.")
if len(images) < len(sentences):
    images = (images * ((len(sentences) // len(images)) + 1))[:len(sentences)]
else:
    images = images[:len(sentences)]

segment = duration / len(images)
parts = []
for i, image in enumerate(images):
    clip = work / f"scene_{i:02d}.mp4"
    fadeout = max(0.2, segment - 0.35)
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image), "-t", f"{segment:.3f}",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,eq=contrast=1.04:saturation=1.08,fade=t=in:st=0:d=.35,fade=t=out:st=" + f"{fadeout:.3f}:d=.35",
        "-r","30","-an","-c:v","libx264","-preset","veryfast","-crf","22","-pix_fmt","yuv420p",str(clip)
    ], check=True)
    parts.append(clip)

concat = work / "concat.txt"
concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(slideshow)], check=True)

filters = [
    "drawbox=x=0:y=0:w=1080:h=1920:color=black@0.14:t=fill",
    "drawbox=x=55:y=55:w=970:h=180:color=0x061426@0.88:t=fill",
    "drawbox=x=55:y=55:w=15:h=180:color=0xe22b2b:t=fill",
    f"drawtext=fontfile='{font}':text='오늘핫뉴스':fontcolor=white:fontsize=42:x=90:y=82",
    f"drawtext=fontfile='{font}':text='누리호 5차 발사 D-1':fontcolor=white:fontsize=52:x=90:y=137",
    f"drawtext=fontfile='{font}':text='내일 발사 예정 · 최종 시각은 내일 결정':fontcolor=0xd9e4f2:fontsize=25:x=90:y=205",
    f"drawtext=fontfile='{font}':text='자료: 한국항공우주연구원':fontcolor=white@0.72:fontsize=22:x=70:y=1845",
]
for i, sentence in enumerate(sentences):
    start, end = duration*i/len(sentences), duration*(i+1)/len(sentences)
    cap = work / f"caption_{i:02d}.txt"; cap.write_text(sentence, encoding="utf-8")
    filters.append(
        f"drawtext=fontfile='{font}':textfile='{cap}':fontcolor=white:fontsize=45:x=(w-text_w)/2:y=1610:"
        f"box=1:boxcolor=0x061426@0.88:boxborderw=28:enable='between(t,{start:.3f},{end:.3f})'"
    )

subprocess.run([
    "ffmpeg","-y","-i",str(slideshow),"-i",str(wav),"-vf",",".join(filters),"-t",str(duration),
    "-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-b:a","128k","-pix_fmt","yuv420p",
    "-movflags","+faststart",str(mp4)
], check=True)

out = ROOT / "public"; out.mkdir(exist_ok=True)
(out / "latest.mp4").write_bytes(mp4.read_bytes())
(out / "latest.json").write_text(json.dumps({
    "title": title, "duration": duration, "source_urls": content.get("source_urls", []),
    "visual_mode": "official_news_photo_slideshow"
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"built {mp4} duration={duration:.1f}s images={len(images)}")
