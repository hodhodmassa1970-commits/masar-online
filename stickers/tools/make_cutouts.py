#!/usr/bin/env python3
"""
قص شخصية "هيا" من صور الخلفية الخضراء (chroma key) وإنتاج PNG شفاف
بحواف ناعمة وإطار أبيض (die-cut) نظيف.

Usage:  python tools/make_cutouts.py
Input : raw/*.png      (صور AI بخلفية خضراء)
Output: cut/*.png      (شخصية بقصّ شفاف + إطار أبيض، ارتفاع 1024)
"""
import os
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "raw")
CUT = os.path.join(ROOT, "cut")
os.makedirs(CUT, exist_ok=True)

ERODE = 7          # إزالة الإطار/الظل القديم من الصورة المولّدة
BORDER = 15        # سماكة الإطار الأبيض الجديد
BOTTOM_RADIUS = 26  # تدوير الزوايا السفلية


def cutout(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]

    # مقدار "اخضرار" البكسل — الخلفية الخضراء أعلى بكثير من 0
    greenness = g - np.maximum(r, b)
    bg = (greenness > 24) & (g > 80)
    bg = ndimage.binary_opening(bg, structure=np.ones((5, 5)))

    fg = ~bg
    lbl, n = ndimage.label(fg)
    if n > 1:
        sizes = ndimage.sum(fg, lbl, range(1, n + 1))
        fg = lbl == (int(np.argmax(sizes)) + 1)

    # سدّ الثقوب الصغيرة (انعكاسات خضراء) دون المساس بالفراغات الحقيقية
    holes = ndimage.binary_fill_holes(fg) & ~fg
    hlbl, hn = ndimage.label(holes)
    if hn:
        hs = ndimage.sum(holes, hlbl, range(1, hn + 1))
        for i, s in enumerate(hs, start=1):
            if s < 2500:
                fg |= hlbl == i

    # تقليص بسيط لإزالة الإطار والظل المولّدين
    fg = ndimage.binary_erosion(fg, structure=np.ones((ERODE, ERODE)))

    # تنعيم الحافة
    soft = ndimage.gaussian_filter(fg.astype(np.float32), 1.0)
    alpha = np.clip((soft - 0.3) / 0.4, 0.0, 1.0)

    # إزالة تسرّب الأخضر (despill)
    max_rb = np.maximum(r, b)
    g2 = np.where(g > max_rb + 3, max_rb + 3, g)
    rgb = np.stack([r, g2, b], axis=-1)

    rgba = np.dstack([rgb, alpha * 255.0]).astype(np.uint8)
    img = Image.fromarray(rgba, "RGBA")

    ys, xs = np.where(alpha > 0.5)
    img = img.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))

    # ===== الإطار الأبيض =====
    w, h = img.size
    pad = BORDER * 3
    canvas = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    canvas.alpha_composite(img, (pad, pad))
    al = canvas.split()[3]

    # تدوير الأزوايا السفلية لتبدو قصّة مقصودة
    rmask = Image.new("L", canvas.size, 255)
    d = ImageDraw.Draw(rmask)
    r = BOTTOM_RADIUS * 2
    d.rectangle([0, canvas.height - r, r, canvas.height], fill=0)
    d.rectangle([canvas.width - r, canvas.height - r, canvas.width, canvas.height], fill=0)
    d.ellipse([0, canvas.height - r, r, canvas.height], fill=255)
    d.ellipse([canvas.width - r, canvas.height - r, canvas.width, canvas.height], fill=255)
    al = Image.fromarray((np.asarray(al).astype(np.float32) *
                         (np.asarray(rmask).astype(np.float32) / 255.0)).astype(np.uint8))
    canvas.putalpha(al)

    white_mask = al.filter(ImageFilter.MaxFilter(BORDER * 2 + 1))
    white = Image.new("RGBA", canvas.size, (255, 255, 255, 255))
    white.putalpha(white_mask)
    out = Image.alpha_composite(white, canvas)

    bbox = out.split()[3].getbbox()
    return out.crop(bbox)


def main():
    files = sorted(f for f in os.listdir(RAW) if f.lower().endswith(".png"))
    for f in files:
        out = cutout(os.path.join(RAW, f))
        ratio = 1024 / out.height
        out = out.resize((max(1, round(out.width * ratio)), 1024), Image.LANCZOS)
        out.save(os.path.join(CUT, f))
        print("cut:", f, out.size)


if __name__ == "__main__":
    main()
