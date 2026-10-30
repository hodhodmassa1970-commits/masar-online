#!/usr/bin/env python3
"""
توليد ستيكرات شخصية "هيا" — نصوص عربية على خلفية باستيل بشكل ستيكر بقصّة بيضاء.

Usage:  python tools/make_stickers.py
Input : cut/*.png     (شخصية بقصّ شفاف)
Output: png/*.png     512×512 شفافة
        webp/*.webp   512×512 (واتساب)
        preview/sheet.png
"""
import os
import math
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ar_text import ArabicText

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CUT = os.path.join(ROOT, "cut")
OUT = os.path.join(ROOT, "png")
WEBP = os.path.join(ROOT, "webp")
PREV = os.path.join(ROOT, "preview")
for d in (OUT, WEBP, PREV):
    os.makedirs(d, exist_ok=True)

S = 512
AR = ArabicText(os.path.join(ROOT, "fonts", "Cairo-ExtraBold.ttf"))
PLUM = (74, 32, 61, 255)

THEMES = {
    "pink":     ((255, 231, 243), (255, 170, 208), (232, 85, 155, 255)),
    "rose":     ((255, 238, 238), (255, 180, 190), (224, 82, 106, 255)),
    "lavender": ((242, 234, 255), (200, 178, 255), (139, 92, 246, 255)),
    "mint":     ((224, 249, 242), (155, 227, 206), (17, 158, 129, 255)),
    "cream":    ((255, 247, 227), (255, 211, 158), (222, 133, 40, 255)),
    "blue":     ((228, 243, 255), (160, 208, 255), (40, 122, 206, 255)),
}

# (المِلف, النص, الثيم, النمط)
STICKERS = [
    ("01-wave",       "معكم هيا",            "pink",     "bubble"),
    ("02-hearthands", "كونوا مع هيا",        "lavender", "bubble"),
    ("03-presenting", "هيا معكم",            "mint",     "bubble"),
    ("04-coffee",     "صباح الخير مع هيا",   "cream",    "bubble"),
    ("05-thumbsup",   "هيا معكم دائمًا",     "blue",     "bubble"),
    ("07-laugh",      "أهلًا بكم مع هيا",    "rose",     "bubble"),
    ("08-kiss",       "معكم هيا",            "pink",     "bubble"),
    ("09-selfpoint",  "هيا في خدمتكم",       "lavender", "bubble"),
    ("06-card",       "كونوا مع هيا",        "pink",     "card"),
]

PILL_MAX_W = 436      # عرض الكبسولة (بدون الهامش)
PILL_M = 36           # هامش الطبقة (للظل والحد)
CHAR_BOTTOM = 512
PILL_TOP = 10


# ---------------------------------------------------------------- أدوات رسم
def vgrad(size, c1, c2):
    w, h = size
    g = np.zeros((h, w, 4), dtype=np.uint8)
    for y in range(h):
        t = y / max(1, h - 1)
        for i in range(3):
            g[y, :, i] = int(c1[i] + (c2[i] - c1[i]) * t)
    g[..., 3] = 255
    return Image.fromarray(g, "RGBA")


def gradient_mask(size, c1, c2, mask):
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(vgrad(size, c1, c2), (0, 0), mask)
    return out


def heart(size, color, angle=0):
    """قلب مرسوم رياضيًا"""
    k = 4
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


def sparkle(size, color):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c, r = size / 2, size * 0.48
    pts = []
    for i in range(8):
        a = math.pi / 4 * i
        rr = r if i % 2 == 0 else r * 0.20
        pts.append((c + rr * math.cos(a), c + rr * math.sin(a)))
    d.polygon(pts, fill=color)
    return im


# ---------------------------------------------------------------- الشخصية
def character(name, height, bottom=CHAR_BOTTOM, cx=None):
    ch = Image.open(os.path.join(CUT, name + ".png")).convert("RGBA")
    r = height / ch.height
    ch = ch.resize((max(1, round(ch.width * r)), height), Image.LANCZOS)
    x = (S - ch.width) // 2 if cx is None else cx - ch.width // 2
    return ch, x, bottom - height


def paste_character(canvas, name, height, bottom=CHAR_BOTTOM):
    ch, x, y = character(name, height, bottom)
    a = ch.split()[3].point(lambda v: int(v * 0.30))
    sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sh.paste((96, 52, 86), (x, y + 9), a.filter(ImageFilter.GaussianBlur(13)))
    canvas.alpha_composite(sh)
    canvas.alpha_composite(ch, (x, y))


# ---------------------------------------------------------------- الكبسولة
def pill_layer(text, theme):
    """يرجع (الطبقة، مقاس الخط، عرض الكبسولة، ارتفاعها الشفاف، إزاحة الهامش)"""
    c1, c2, accent = THEMES[theme]
    size = AR.fit(text, 72, PILL_MAX_W - 104)
    timg, _ = AR.render(text, size, fill=PLUM)
    w = min(PILL_MAX_W, timg.width + 88)
    h = timg.height + 52
    radius = h / 2
    m = PILL_M

    layer = Image.new("RGBA", (w + 2 * m, h + 2 * m), (0, 0, 0, 0))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)

    shadow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    shadow.paste((120, 60, 105, 95), (m, m + 5), mask.filter(ImageFilter.GaussianBlur(10)))
    layer.alpha_composite(shadow)

    border = mask.filter(ImageFilter.MaxFilter(15))
    white = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    white.putalpha(border)
    layer.alpha_composite(white, (m, m))

    layer.alpha_composite(gradient_mask((w, h), c1, c2, mask), (m, m))

    gloss = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    ImageDraw.Draw(gloss).rounded_rectangle(
        [5, 4, w - 6, int(h * 0.50)], radius=radius, fill=(255, 255, 255, 78))
    gl = np.asarray(gloss.split()[3]).astype(np.float32)
    mk = np.asarray(mask).astype(np.float32) / 255.0
    gloss.putalpha(Image.fromarray((gl * mk).astype(np.uint8)))
    layer.alpha_composite(gloss, (m, m))

    layer.alpha_composite(timg, (m + (w - timg.width) // 2, m + (h - timg.height) // 2))

    hs = int(h * 0.44)
    layer.alpha_composite(heart(hs, accent), (m - hs // 2 - 2, m + h // 2 - hs // 2 - 5))
    hs2 = int(hs * 0.66)
    layer.alpha_composite(heart(hs2, accent, angle=16),
                          (m + w - hs2 // 2 + 2, m + h // 2 - hs2 // 2 + 2))
    return layer, size, w, h + 14, m   # +14 لسماكة الحد الأبيض


def make_bubble_sticker(name, text, theme):
    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    pill, size, pw, ph, m = pill_layer(text, theme)

    # الشخصية تبدأ أسفل الكبسولة بقليل (تداخل بسيط مع الشعر فقط)
    char_top = PILL_TOP + ph - 18
    char_h = min(430, CHAR_BOTTOM + 4 - char_top)
    paste_character(canvas, name, char_h, CHAR_BOTTOM + 4)

    py = PILL_TOP - m
    canvas.alpha_composite(pill, ((S - pill.width) // 2, py))
    canvas.alpha_composite(sparkle(22, (255, 255, 255, 242)), (S - 60, PILL_TOP + ph - 34))
    canvas.alpha_composite(sparkle(13, (255, 255, 255, 220)), (34, PILL_TOP + 22))
    return canvas, size


def card_sticker(name, text, theme):
    """هيا تحمل لوحة مكتوب عليها اسمها وقلب — بدون شريط فوق الرأس"""
    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ch = Image.open(os.path.join(CUT, name + ".png")).convert("RGBA")

    # إيجاد اللوحة البيضاء داخل الشخصية
    a = np.asarray(ch).astype(np.int16)
    inner = ndimage.binary_erosion(a[..., 3] > 200, structure=np.ones((61, 61)))
    white = ((a[..., :3].min(axis=2) > 225) &
             ((a[..., :3].max(axis=2) - a[..., :3].min(axis=2)) < 14) & inner)
    lbl, n = ndimage.label(white)
    sizes = ndimage.sum(white, lbl, range(1, n + 1))
    mm = lbl == (int(np.argmax(sizes)) + 1)
    ys, xs = np.where(mm)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

    ch_h = 488
    ch2, ox, oy = character(name, ch_h)
    a2 = ch2.split()[3].point(lambda v: int(v * 0.30))
    sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sh.paste((96, 52, 86), (ox, oy + 9), a2.filter(ImageFilter.GaussianBlur(13)))
    canvas.alpha_composite(sh)
    canvas.alpha_composite(ch2, (ox, oy))

    r = ch_h / ch.height
    cw = (x1 - x0) * r          # عرض اللوحة بعد التحجيم
    chh = (y1 - y0) * r         # ارتفاع اللوحة

    # محتوى اللوحة: قلب + "هيا" بحيث يدخل كاملًا داخل اللوحة
    scale = min(cw * 0.62, chh * 0.70)
    hrt = heart(int(scale * 0.42), (232, 85, 155, 255), angle=-10)
    name_img, _ = AR.render("هيا", int(scale * 0.52), fill=PLUM)
    gap = int(scale * 0.06)
    gw = max(hrt.width, name_img.width)
    gh = hrt.height + gap + name_img.height
    sub = Image.new("RGBA", (gw, gh), (0, 0, 0, 0))
    sub.alpha_composite(hrt, ((gw - hrt.width) // 2, 0))
    sub.alpha_composite(name_img, ((gw - name_img.width) // 2, hrt.height + gap))
    sub = sub.rotate(-4.2, resample=Image.BICUBIC, expand=True)
    canvas.alpha_composite(sub, (int(ox + cx * r - sub.width / 2), int(oy + cy * r - sub.height / 2)))

    canvas.alpha_composite(heart(40, (232, 85, 155, 255), angle=-16), (S - 78, 18))
    canvas.alpha_composite(sparkle(22, (255, 255, 255, 240)), (40, 44))
    canvas.alpha_composite(sparkle(15, (255, 255, 255, 225)), (S - 104, 118))
    return canvas, 0


def main():
    items = []
    for name, text, theme, mode in STICKERS:
        if mode == "card":
            st, size = card_sticker(name, text, theme)
        else:
            st, size = make_bubble_sticker(name, text, theme)
        st.save(os.path.join(OUT, name + ".png"))
        st.save(os.path.join(WEBP, name + ".webp"), "WEBP", quality=92, method=6)
        items.append((name, st))
        print(f"sticker: {name:16s} text={size}px")

    cols, cell = 3, 340
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell + 40, rows * cell + 40), (255, 240, 247))
    sd = ImageDraw.Draw(sheet)
    for i in range(rows * cols):
        x, y = 20 + (i % cols) * cell, 20 + (i // cols) * cell
        sd.rounded_rectangle([x + 4, y + 4, x + cell - 14, y + cell - 14], 34,
                             fill=(255, 255, 255), outline=(255, 205, 226), width=3)
        if i < len(items):
            im = items[i][1].resize((cell - 42, cell - 42), Image.LANCZOS)
            sheet.paste(im, (x + 12, y + 12), im)
    sheet.save(os.path.join(PREV, "sheet.png"))
    print("preview: preview/sheet.png")


if __name__ == "__main__":
    main()
