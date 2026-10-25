#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Builds the series recap: a poster wall (PNG) and an animated recap strip (GIF)
   that samples two frames from every finished episode.
   python media/recap.py"""
import os, subprocess, glob
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
import imageio_ffmpeg

M = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(M)
FF = imageio_ffmpeg.get_ffmpeg_exe()
AMI = os.path.join(M, "Amiri-Bold.ttf")
KUF = os.path.join(M, "NotoKufi.ttf")
GOLD = (243, 198, 75)
PW, PH, LAB = 240, 427, 40

# (slug, episode tag, title, duration s) in life order
EPS = [
    ("e1", "E1", "الدفتر الأول", 37.0),
    ("e2", "E2", "السنة الصعبة", 35.6),
    ("e3", "E3", "البناء", 31.7),
    ("e4", "E4", "اثنا عشر شخصاً", 37.6),
    ("e5", "E5", "بعد أن خرج الضوء", 33.1),
    ("e6", "E6", "العودة", 33.6),
    ("e0", "E0", "البداية · الإعلانات", 36.9),
    ("g1", "G1", "مسا الخير حبايبي", 19.4),
]
# where to sample the two frames from, as a share of the runtime
FRACS = [0.30, 0.74]


def shp(t):
    return get_display(arabic_reshaper.reshape(t))


def grab(slug, dur):
    out = []
    for j, fr in enumerate(FRACS):
        d = "/tmp/recap/%s_%d.png" % (slug, j)
        os.makedirs("/tmp/recap", exist_ok=True)
        src = os.path.join(ROOT, "media", "series", slug, "out", "haya_%s_hd.mp4" % slug)
        if not os.path.exists(src):
            return None
        subprocess.run([FF, "-loglevel", "error", "-y", "-ss", "%.2f" % (dur * fr),
                        "-i", src, "-frames:v", "1", "/tmp/recap/tmp.png"], check=True)
        Image.open("/tmp/recap/tmp.png").convert("RGB").resize((PW, PH), Image.LANCZOS).save(d)
        out.append(d)
    return out


def label(img, tag, ttl, extra=""):
    d = ImageDraw.Draw(img)
    d.rectangle([0, PH, PW, PH + LAB], fill=(12, 15, 22))
    d.text((PW // 2, PH + 13), shp("%s · %s" % (tag, ttl)),
           font=ImageFont.truetype(KUF, 15), fill=GOLD, anchor="mm")
    if extra:
        d.text((PW // 2, PH + 30), extra, font=ImageFont.truetype(KUF, 11),
               fill=(150, 162, 182), anchor="mm")
    return img


def main():
    rows, cols = 2, 4
    wall = Image.new("RGB", (cols * PW, rows * (PH + LAB)), (9, 11, 16))
    frames = []
    for i, (slug, tag, ttl, dur) in enumerate(EPS):
        fs = grab(slug, dur)
        if not fs:
            print("skip", slug, "(not rendered yet)"); continue
        for j, f in enumerate(fs):
            im = Image.open(f).convert("RGB")
            panel = Image.new("RGB", (PW, PH + LAB), (9, 11, 16))
            panel.paste(im, (0, 0))
            label(panel, tag, ttl, "%.1f ث · 9:16 · voice-03" % dur)
            if i < cols * rows:
                wall.paste(panel, ((i % cols) * PW, (i // cols) * (PH + LAB)))
            p2 = Image.new("RGB", (PW, PH + LAB), (9, 11, 16))
            p2.paste(Image.open(f).convert("RGB"), (0, 0))
            label(p2, tag, ttl)
            frames.append(p2)
    out_png = os.path.join(M, "series", "poster_wall.png")
    wall.save(out_png)
    wall.convert("RGB").save(out_png.replace(".png", ".jpg"), quality=90)
    g = [f.quantize(colors=150, method=Image.MEDIANCUT) for f in frames]
    out_gif = os.path.join(M, "series", "haya_series_recap.gif")
    g[0].save(out_gif, save_all=True, append_images=g[1:], duration=520, loop=0, optimize=True)
    print("wall:", wall.size, "%.2f MB" % (os.path.getsize(out_png) / 1e6))
    print("recap:", len(g), "frames", "%.2f MB" % (os.path.getsize(out_gif) / 1e6))


if __name__ == "__main__":
    main()
