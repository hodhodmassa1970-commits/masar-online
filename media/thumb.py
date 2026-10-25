#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Builds a 1280x720 YouTube thumbnail for the Haya series from the key art that already
   exists in the repo — same identity, same gold/teal grade, same Arabic type as the films.
   python media/thumb.py  ->  media/series/youtube_thumb.jpg (and .png)"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

M = os.path.dirname(os.path.abspath(__file__))
FR = os.path.join(M, "frames")
P = os.path.join(M, "..")
OUT = os.path.join(M, "series")
GOLD, GHI, GLO = (243, 198, 75), (255, 236, 170), (176, 118, 26)
AMI = os.path.join(M, "Amiri-Bold.ttf")
KUF = os.path.join(M, "NotoKufi.ttf")
W, H = 1280, 720


def shp(t):
    return get_display(arabic_reshaper.reshape(t))


def fit(img, w, h):
    """scale-to-cover then centre-crop"""
    s = max(w / img.width, h / img.height)
    im = img.resize((int(img.width * s + .5), int(img.height * s + .5)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def text(d, xy, s, font, fill, anchor="ls", shadow=True, glow=None, gs=0):
    x, y = xy
    if glow:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(lay).text((x, y), s, font=font, fill=glow, anchor=anchor)
        return lay
    if shadow:
        d.text((x + 3, y + 4), s, font=font, fill=(6, 8, 14, 235), anchor=anchor)
    d.text((x, y), s, font=font, fill=fill, anchor=anchor)


def main():
    base = fit(Image.open(os.path.join(FR, "s7_finale.png")).convert("RGB"), W, H)
    base = ImageEnhance.Brightness(base).enhance(.72)
    base = ImageEnhance.Color(base).enhance(1.12)
    base = base.filter(ImageFilter.UnsharpMask(3, 120, 2))

    # her portrait, gold-bordered, on the right (RTL reading: face first, headline at the left)
    pw, ph = 430, 620
    px, py = W - pw - 46, (H - ph) // 2
    por = fit(Image.open(os.path.join(M, "haya_portrait.png")).convert("RGB"), pw, ph)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle([px - 10, py - 10, px + pw + 10, py + ph + 10], 26,
                                           fill=(255, 206, 96, 150))
    base = Image.composite(Image.blend(base.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(26)), .85),
                           base.convert("RGBA"),
                           Image.new("L", (W, H), 255)).convert("RGB")
    d = ImageDraw.Draw(base, "RGBA")
    d.rounded_rectangle([px - 9, py - 9, px + pw + 9, py + ph + 9], 24, outline=GOLD, width=5)
    base.paste(por, (px, py))

    # scrim so the type always reads
    sc = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sc).rectangle([-40, -40, int(W * .62), H + 40], fill=(6, 9, 16, 165))
    sc = sc.filter(ImageFilter.GaussianBlur(34))
    base = Image.alpha_composite(base.convert("RGBA"), sc).convert("RGB")
    d = ImageDraw.Draw(base, "RGBA")

    tl = ImageFont.truetype(AMI, 112)
    t2 = ImageFont.truetype(AMI, 46)
    k1 = ImageFont.truetype(KUF, 27)
    k2 = ImageFont.truetype(KUF, 20)

    lay = text(d, (60, 150), shp("أميرة"), tl, GOLD + (255,), "ls", glow=(255, 200, 90, 210), gs=16)
    if lay:
        base = Image.alpha_composite(base.convert("RGBA"),
                                     lay.filter(ImageFilter.GaussianBlur(16))).convert("RGB")
        d = ImageDraw.Draw(base, "RGBA")
    d.text((60, 150), shp("أميرة"), font=tl, fill=(255, 240, 200, 255), anchor="ls")
    d.text((64, 262), shp("الجماهير"), font=tl, fill=GOLD + (255,), anchor="ls")

    d.rounded_rectangle([58, 306, 470, 312], 3, fill=GLO + (255,))
    d.text((60, 372), shp("قصة هيا · ثماني حلقات"), font=t2, fill=(246, 246, 250, 255), anchor="ls")
    d.text((60, 440), shp("من دفتر الطفولة إلى المسرح · 16:9"), font=k1,
           fill=(214, 224, 238, 240), anchor="ls")

    # corner badges
    d.rounded_rectangle([58, 44, 372, 92], 12, fill=(10, 13, 20, 210))
    d.text((76, 68), shp("مسلسل هيا · HD"), font=k2, fill=(255, 228, 170, 240), anchor="lm")
    d.ellipse([76, 62, 88, 74], fill=(255, 62, 62, 255))
    d.rounded_rectangle([58, H - 96, 250, H - 52], 12, fill=(243, 198, 75, 235))
    d.text((76, H - 74), "2026", font=k2, fill=(20, 16, 6, 255), anchor="lm")

    # film grain + vignette, same as the films
    import numpy as np
    a = np.asarray(base).astype(np.int16)
    n = np.random.default_rng(7).integers(-14, 15, a.shape[:2])
    a = np.clip(a + n[:, :, None], 0, 255).astype("uint8")
    out = Image.fromarray(a)
    v = Image.new("L", (W, H), 0)
    ImageDraw.Draw(v).ellipse([-140, -120, W + 140, H + 120], fill=255)
    v = v.filter(ImageFilter.GaussianBlur(180))
    dark = Image.new("RGB", (W, H), (4, 6, 10))
    out = Image.composite(out, dark, v.point(lambda p: int(120 + p * .55)))

    os.makedirs(OUT, exist_ok=True)
    out.save(os.path.join(OUT, "youtube_thumb.png"))
    out.convert("RGB").save(os.path.join(OUT, "youtube_thumb.jpg"), quality=92)
    print("wrote media/series/youtube_thumb.jpg · %.2f MB" %
          (os.path.getsize(os.path.join(OUT, "youtube_thumb.jpg")) / 1e6))


if __name__ == "__main__":
    main()
