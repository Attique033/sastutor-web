"""Builds assets/video/founder.mp4: stock scenes + slow zoom + burned-in captions + TTS voiceover.

Placeholder until the founder records the real video. Edit SCENES, then:
    python build.py            (needs: pip install imageio-ffmpeg pillow; macOS `say`)
"""
import os, wave, subprocess, tempfile
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "..", "assets", "img")
OUT = os.path.join(HERE, "..", "assets", "video")
FF = imageio_ffmpeg.get_ffmpeg_exe()
VOICE, RATE = "Karen", 172  # ponytail: system TTS voice, swap for the founder's own recording
W, H, FPS = 1280, 720, 30
INK, PAPER, ACCENT = (16, 33, 58), (251, 248, 243), (255, 210, 63)

# (image or None for a title card, narration line, on-screen caption or None to reuse the line)
SCENES = [
    (None, "Hi. I'm the founder of SAS Tutors.", "A message from our founder"),
    ("student-writing", "I started SAS Tutors because I kept seeing bright students fall behind.", None),
    ("student-focus", "Not because they weren't capable, but because no one had fixed their fundamentals.", None),
    ("calculator", "So that's what we do. We rebuild the fundamentals first, and the grades follow.", None),
    ("student-smile", "Every student gets an expert tutor, hand-picked for their subject and their exam.", None),
    ("writing", "Every tutor passes a rigorous hiring process before they ever teach.", None),
    ("exam", "After every lesson, you get notes on what was covered, and what to practise next.", None),
    ("family", "Whether it's Year 4 maths, IGCSE physics or A-Level chemistry, we meet your child where they are,", None),
    ("hero", "and take them where they want to be.", None),
    (None, "Your first lesson is free. Book a trial, and we'll message you on WhatsApp within a few hours. I can't wait to meet you.",
     "Your first lesson is free"),
]


def font(size, style="Bold"):
    for i in range(12):
        try:
            f = ImageFont.truetype("/System/Library/Fonts/Avenir Next.ttc", size, index=i)
        except OSError:
            break
        if f.getname()[1] == style:
            return f
    return ImageFont.truetype("/System/Library/Fonts/Avenir Next.ttc", size)


def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=fnt) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line]


def caption_png(text, path):
    """Transparent lower-third: soft dark gradient + white caption."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    grad = Image.new("L", (1, H))
    for y in range(H):
        grad.putpixel((0, y), int(max(0, (y - H * 0.45) / (H * 0.55)) * 200))
    im.paste((10, 18, 32, 255), (0, 0, W, H), grad.resize((W, H)))
    d = ImageDraw.Draw(im)
    f = font(40, "Demi Bold")
    lines = wrap(d, text, f, W - 200)
    y = H - 70 - len(lines) * 52
    for ln in lines:
        d.text(((W - d.textlength(ln, font=f)) / 2, y), ln, font=f, fill=(255, 255, 255))
        y += 52
    im.save(path)


def card_png(title, sub, path):
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)
    f, fs = font(76, "Bold"), font(34, "Medium")
    lines = wrap(d, title, f, W - 200)
    subs = wrap(d, sub, fs, W - 200) if sub else []
    y = (H - (60 + len(lines) * 92 + (30 + len(subs) * 46 if subs else 0))) // 2  # centre the block
    d.text((100, y), "SAS TUTORS", font=font(30, "Bold"), fill=ACCENT)
    y += 60
    for ln in lines:
        d.text((100, y), ln, font=f, fill=PAPER)
        y += 92
    y += 30
    for ln in subs:
        d.text((100, y), ln, font=fs, fill=(190, 200, 215))
        y += 46
    im.save(path)


def run(*args):
    subprocess.run([FF, "-y", "-loglevel", "error", *args], check=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    tmp = tempfile.mkdtemp()
    parts = []
    for i, (img, line, cap) in enumerate(SCENES):
        aiff = f"{tmp}/{i}.wav"
        subprocess.run(["say", "-v", VOICE, "-r", str(RATE), "--file-format=WAVE", "--data-format=LEI16@22050", "-o", aiff, line], check=True)
        with wave.open(aiff) as a:
            dur = a.getnframes() / a.getframerate() + 0.6  # breath between lines
        frames = int(dur * FPS)
        clip = f"{tmp}/{i}.mp4"
        fade = f"fade=t=in:st=0:d=0.35,fade=t=out:st={dur - 0.35:.2f}:d=0.35"
        if img is None:
            png = f"{tmp}/card{i}.png"
            card_png(cap, None if i == 0 else "Book a free trial at sastutors.com.au", png)
            run("-loop", "1", "-i", png, "-i", aiff, "-t", f"{dur:.2f}", "-vf", f"format=yuv420p,{fade}",
                "-af", "apad", "-r", str(FPS), "-c:v", "libx264", "-c:a", "aac", "-shortest", clip)
        else:
            png = f"{tmp}/cap{i}.png"
            caption_png(cap or line, png)
            # slow push-in on a 2x canvas so the zoom stays smooth
            zoom = (f"[0:v]scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2},"
                    f"zoompan=z='1+0.08*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}[bg];"
                    f"[bg][1:v]overlay=0:0,format=yuv420p,{fade}[v]")
            run("-loop", "1", "-i", f"{IMG}/{img}.webp", "-loop", "1", "-i", png, "-i", aiff,
                "-filter_complex", zoom, "-map", "[v]", "-map", "2:a", "-af", "apad", "-t", f"{dur:.2f}",
                "-r", str(FPS), "-c:v", "libx264", "-c:a", "aac", clip)
        parts.append(clip)
    with open(f"{tmp}/list.txt", "w") as fh:
        fh.writelines(f"file '{p}'\n" for p in parts)
    run("-f", "concat", "-safe", "0", "-i", f"{tmp}/list.txt", "-c:v", "libx264", "-crf", "26", "-preset", "slow",
        "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", f"{OUT}/founder.mp4")
    run("-ss", "1", "-i", f"{OUT}/founder.mp4", "-frames:v", "1", f"{tmp}/poster.png")
    Image.open(f"{tmp}/poster.png").save(f"{OUT}/founder-poster.webp", "WEBP", quality=75)
    print("wrote", f"{OUT}/founder.mp4")


if __name__ == "__main__":
    main()
