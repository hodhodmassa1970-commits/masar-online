#!/usr/bin/env python3
"""
غلاف حزمة ستيكرات "هيا" — 1024×1024

Usage: python tools/make_cover.py
Output: preview/cover.png
"""
import os
import math
import random
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ar_text import ArabicText

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AR = ArabicText(os.path.join(ROOT, "fonts", "Cairo-ExtraBold.ttf"))
PLUM = (74, 32, 61, 255)
PINK = (232, 85, 155, 255)
W = H = 1024


def vgrad(size, c1, c2):
    w, h = size
    g = np.zeros((h, w, 4), dtype=np.uint8)
    for y in range(h):
        t = y / max(1, h - 1)
        for i in range(3):
            g[y, :, i] = int(c1[i] + (c2[i] - c1[i]) * t)
    g[..., 3] = 255
    return Image.fromarray(g, "RGBA")


def heart(size, color, angle=0):
    k = 3
    im = Image.new("L", (size * k, size * k), 0)
    d = ImageDraw.Draw(im)
    w = size * k
    pts = []
    for i in range(361):
        t = math.radians(i)
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((w / 2 + x * w / 38, w / 2 - y * w / 38 + w * 0.06))
    d.polygon(pts, fill=255)
    im = im.resize((size, size), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), color)
    out.putalpha(im)
    if angle:
        out = out.rotate(angle, resample=Image.BICUBIC, expand=True)
    return out


def row_with_heart(parts, size, color, heart_size, heart_color, gap=22):
    """يرسم عدة نصوص عربية في سطر واحد مع قلب بينها (بدل النقاط غير المتوفرة بالخط)"""
    imgs = [AR.render(p, size, fill=color)[0] for p in parts]
    total = sum(i.width for i in imgs) + heart_size * (len(imgs) - 1) + gap * 2 * (len(imgs) - 1)
    h = max(max(i.height for i in imgs), heart_size)
    line = Image.new("RGBA", (total, h), (0, 0, 0, 0))
    x = total
    for k, im in enumerate(imgs):
        x -= im.width
        line.alpha_composite(im, (x, (h - im.height) // 2))
        if k < len(imgs) - 1:
            x -= heart_size + gap
            line.alpha_composite(heart(heart_size, heart_color), (x, (h - heart_size) // 2))
            x -= gap
    return line


def main():
    canvas = vgrad((W, H), (255, 234, 244), (255, 196, 224)).convert("RGBA")

    # بوكيه ناعم
    random.seed(7)
    bokeh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bokeh)
    for _ in range(26):
        r = random.randint(40, 150)
        x, y = random.randint(-60, W + 60), random.randint(-60, H + 60)
        bd.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, random.randint(16, 44)))
    canvas.alpha_composite(bokeh.filter(ImageFilter.GaussianBlur(18)))

    canvas.alpha_composite(heart(250, (255, 255, 255, 120), angle=-18), (40, 26))
    canvas.alpha_composite(heart(190, (255, 255, 255, 110), angle=16), (W - 190, 40))
    canvas.alpha_composite(heart(74, (232, 85, 155, 175), angle=12), (W - 118, 300))
    canvas.alpha_composite(heart(52, (232, 85, 155, 150), angle=-14), (58, 300))

    # العنوان
    t1, _ = AR.render("ستيكرات هيا", 126, fill=PLUM)
    canvas.alpha_composite(t1, ((W - t1.width) // 2, 96))
    sub = row_with_heart(["معكم هيا", "كونوا مع هيا"], 56, PINK, 34, (255, 255, 255, 240))
    canvas.alpha_composite(sub, ((W - sub.width) // 2, 268))

    # هالة خلف الشخصية
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([W / 2 - 330, 400, W / 2 + 330, H + 120], fill=(255, 255, 255, 120))
    canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(70)))

    # الستيكر الرئيسي (يظهر بارزًا في وسط الغلاف)
    st = Image.open(os.path.join(ROOT, "png", "01-wave.png")).convert("RGBA")
    th = 600
    st = st.resize((max(1, round(st.width * th / st.height)), th), Image.LANCZOS)
    canvas.alpha_composite(st, ((W - st.width) // 2, H - st.height - 6))

    canvas.convert("RGB").save(os.path.join(ROOT, "preview", "cover.png"), quality=95)
    print("preview/cover.png", canvas.size)


if __name__ == "__main__":
    main()
