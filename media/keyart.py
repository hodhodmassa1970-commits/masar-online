#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Builds a key-art board for the Haya series from whatever frames exist.
   python media/keyart.py  ->  media/series/keyart.png (+ .jpg)"""
import os, glob
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

M = os.path.dirname(os.path.abspath(__file__))
FR = os.path.join(M, "frames")
KUF = os.path.join(M, "NotoKufi.ttf")
AMI = os.path.join(M, "Amiri-Bold.ttf")
GOLD = (243, 198, 75)

LABELS = [
    ("e1_kitchen.png",   "E1", "الدفتر الأول", "٦ سنوات · سقف البيت والدفتر القديم"),
    ("e1_terrace.png",   "E1", "الدفتر الأول", "طفولة على شط البحر"),
    ("e1_classroom.png", "E1", "الدفتر الأول", "أول جمهور: صف مدرسي"),
    ("e2_night.png",     "E2", "السنة الصعبة", "٢٢ سنة · ٤٤ رسالة رفض"),
    ("e3_studio.png",    "E3", "البناء", "٢٧ سنة · استوديو مستأجر"),
    ("e4_hall.png",      "E4", "اثنا عشر شخصاً", "٢٩ سنة · أول لقاء حقيقي"),
    ("e5_after.png",     "E5", "بعد أن خرج الضوء", "ليلة الانطلاقة · القاعة الفارغة"),
    ("e6_school.png",    "E6", "العودة", "ساحة مدرستها القديمة"),
    ("s2_wave.png",      "—",  "الانطلاقة", "١٢ ألف شخص · المسرح"),
]


def shp(t):
    return get_display(arabic_reshaper.reshape(t))


def main():
    items = [(f, e, t, s) for (f, e, t, s) in LABELS if os.path.exists(os.path.join(FR, f))]
    if not items:
        print("no frames yet"); return
    pw, ph = 360, 640                       # 9:16 panels
    cols = min(5, len(items))
    rows = (len(items) + cols - 1) // cols
    head, foot = 108, 46
    sheet = Image.new("RGB", (cols * pw, rows * (ph + 54) + head + foot), (9, 11, 16))
    d = ImageDraw.Draw(sheet)
    d.rectangle([0, 0, sheet.size[0], head], fill=(12, 15, 22))
    tf = ImageFont.truetype(AMI, 46)
    d.text((24, 18), shp("هيا — لوحات المفاتيح لكل حلقة"), font=tf, fill=GOLD)
    sf = ImageFont.truetype(KUF, 17)
    d.text((26, 74), shp("نفس الوجه · نفس القلادة · نفس الصوت (voice-03) · تدرّج Teal & Gold"),
           font=sf, fill=(190, 200, 216))
    ef = ImageFont.truetype(KUF, 22)
    ff = ImageFont.truetype(KUF, 14)
    for i, (fn, ep, ttl, sub) in enumerate(items):
        im = Image.open(os.path.join(FR, fn)).convert("RGB")
        sw, sh = im.size
        bw = int(round(sh * 9 / 16))
        x0 = (sw - bw) // 2
        im = im.crop((x0, 0, x0 + bw, sh)).resize((pw, ph), Image.LANCZOS)
        gx, gy = (i % cols) * pw, head + (i // cols) * (ph + 54)
        sheet.paste(im, (gx, gy))
        d.rectangle([gx, gy, gx + pw, gy + 3], fill=GOLD)
        d.rectangle([gx, gy + ph, gx + pw, gy + ph + 54], fill=(12, 15, 22))
        d.text((gx + 12, gy + ph + 6), shp("%s · %s" % (ep, ttl)), font=ef, fill=(240, 240, 245))
        d.text((gx + 12, gy + ph + 32), shp(sub), font=ff, fill=(150, 162, 182))
    d.text((24, sheet.size[1] - 32), shp("اللوحات الناقصة تُولَّد في الجولة القادمة (حصة توليد الصور)"),
           font=ff, fill=(120, 132, 152))
    out = os.path.join(M, "series", "keyart.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sheet.save(out)
    sheet.convert("RGB").resize((int(sheet.size[0] * .72), int(sheet.size[1] * .72)),
                                Image.LANCZOS).save(out.replace(".png", ".jpg"), quality=88)
    print("wrote", out, sheet.size, "panels:", len(items))


if __name__ == "__main__":
    main()
