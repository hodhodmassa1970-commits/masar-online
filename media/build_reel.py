#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
هيا — vertical 9:16 launch reel (Levantine).  Single-file, reproducible engine.
    /home/user/.venv/bin/python /home/user/masar-online/media/build_reel.py
Inputs : media/frames/*.png (AI keyframes) + media/audio/a?.mp3 (TTS, voice-03)
Outputs: media/haya_shami_vertical.mp4        (1080x1920, master)
         media/haya_shami_vertical_small.mp4  (540x960,  web/preview)
         media/haya_poster.jpg, media/haya_intro.gif
"""
import os, sys, json, math, wave, subprocess, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import arabic_reshaper
from bidi.algorithm import get_display
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
M = "/home/user/masar-online/media"
FR, AU, B = os.path.join(M, "frames"), os.path.join(M, "audio"), \
    os.environ.get("WORK") or os.path.join(M, "work")
os.makedirs(B, exist_ok=True)
SR, FPS, TFPS = 48000, 30, 12
AR = os.environ.get("AR", "9:16")                       # "9:16" (default) or "16:9"
LAND = AR.startswith("16")
W, H, TW, TH = (1920, 1080, 960, 540) if LAND else (1080, 1920, 540, 960)
TS = .72 if LAND else 1.0        # type sizes scale with the shorter edge of the frame


def ts(px):
    return max(11, int(round(px * TS)))

CUT, DISS, LEAD = 0.041, 0.85, 0.9
KUF = os.environ.get("KUF") or (os.path.join(M, "NotoKufi.ttf")
        if os.path.exists(os.path.join(M, "NotoKufi.ttf")) else "/home/user/fonts/NotoKufi.ttf")
AMI = os.environ.get("AMI") or (os.path.join(M, "Amiri-Bold.ttf")
        if os.path.exists(os.path.join(M, "Amiri-Bold.ttf")) else "/home/user/fonts/Amiri-Bold.ttf")
GOLD, GHI, GLO = (243, 198, 75), (255, 236, 170), (196, 138, 40)
PAL = [(243, 198, 75), (255, 236, 170), (222, 229, 236), (255, 255, 255),
       (228, 169, 63), (198, 138, 40), (255, 214, 120)]

SEG = [dict(a="a1.mp3", tail=1.7, minimum=4.6), dict(a="a2.mp3", tail=1.25, minimum=0),
       dict(a="a3.mp3", tail=1.05, minimum=0), dict(a="a4.mp3", tail=4.8, minimum=0)]
SHOTS = [
 dict(f="s1_run.png", seg=0, tin=0.0, cx=.50, rays=.55, conf=175, z=(1.00, 1.07), p=(.50, .55, .48, .47),
      lines=["هلا بالشباب!|أهلين فيكن كلّن!"],
      kicker=dict(t="المشهد الأول · قاعة الانطلاق", a=.3, b=4.2)),
 dict(f="s2_wave.png", seg=1, tin=DISS, cx=.49, rays=.90, conf=215, z=(1.07, 1.00), p=(.46, .50, .53, .55),
      lines=["مرحباً، أنا هيا!|ومِن سنين، كنت بسمع الناس بتقول:", "التغيير بيبلّش بخطة."],
      title=dict(t="مرحباً|أنا هيا", line=0, a=.2, hold=.55)),
 dict(f="s3_jump.png", seg=1, tin=CUT, cx=.50, rays=1.0, conf=265, z=(1.00, 1.09), p=(.50, .52, .50, .46),
      lines=["وأنا جاية اليوم بقّلكن:|التغيير الحقيقي بيبلّش بقفزة!"]),
 dict(f="s4_heart.png", seg=2, tin=DISS, cx=.50, rays=.38, conf=125, z=(1.01, 1.08), p=(.50, .45, .50, .55),
      lines=["ما جيت اليوم حكي|عن أفكار ونظريات."],
      motto=dict(t="«حوِّل الشغف لحركة،|والاحتفال لبناء»", a=.9)),
 dict(f="s5_crowd.png", seg=2, tin=CUT, cx=.50, rays=.50, conf=155, z=(1.08, 1.00), p=(.52, .50, .48, .52),
      lines=["جيت احكيلكن عن حلم:|مجتمع كل خطوة فيه لقدام سبب نحتفل."]),
 dict(f="s6_kneel.png", seg=2, tin=DISS, cx=.50, rays=.80, conf=235, z=(1.06, 1.00), p=(.53, .55, .50, .48),
      lines=["مستقبلنا مش شي نستناه…|مستقبلنا شي نركض إلّه بكل طاقتنا."]),
 dict(f="s7_finale.png", seg=3, tin=DISS, cx=.50, rays=1.0, conf=300, z=(1.00, 1.10), p=(.50, .47, .50, .55),
      lines=["أهلين فيكن بانطلاقة مجتمعنا!|هون ما في حدا يمشي لحاله…", "نركض سوا!|يلا نبلّش!"],
      endcard=dict(main="نركض سوا", sub="هيا · مجتمع بيبلّش بقفزة")),
]
for _i, _x in enumerate(SHOTS):
    _x["i"] = _i

# ---------------------------------------------------------------- plumbing
def run(c):
    p = subprocess.run(c, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if p.returncode:
        print(p.stdout.decode("utf8", "replace")[-2500:]); raise SystemExit("ffmpeg failed")
def wav(mp3, out):
    run([FF, "-y", "-loglevel", "error", "-i", mp3, "-ar", str(SR), "-ac", "1", out])
def read_wav(p):
    with wave.open(p, "rb") as w:
        n = w.getnframes(); d = np.frombuffer(w.readframes(n), dtype="<i2").astype(np.float32) / 32768.0
    return d, w.getframerate()
def write_wav(p, x, sr=SR, stereo=True):
    x = np.clip(x, -1, 1)
    if x.ndim == 1:
        x = np.stack([x, x], 1) if stereo else x[:, None]
    with wave.open(p, "wb") as w:
        w.setnchannels(x.shape[1]); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((x * 32767).astype("<i2").tobytes())
TASH = "".join(chr(c) for c in list(range(0x064B, 0x0653)) + [0x0670, 0x0640])
def shape(t):
    for c in TASH:
        t = t.replace(c, "")
    return "\n".join(get_display(arabic_reshaper.reshape(p)) for p in t.split("|"))

def text_layer(text, path, size, fill, max_w=None, stroke=0, sf=(0, 0, 0, 255), glow=None,
               gs=14, grad=None, pad=24, x=.5, y=.5):
    ln = text.split("\n"); s = size
    while s > 9:
        f = ImageFont.truetype(path, s)
        if not max_w or max(f.getbbox(p)[2] - f.getbbox(p)[0] for p in ln) <= max_w:
            break
        s -= 1
    f = ImageFont.truetype(path, s); sp = int(s * .34); a1, a2 = f.getmetrics()
    w0 = int(max(f.getbbox(p)[2] - f.getbbox(p)[0] for p in ln) + 2 * pad)
    h0 = int((a1 + a2 + sp) * len(ln) + 2 * pad)
    t = Image.new("RGBA", (max(4, w0), max(4, h0)), (0, 0, 0, 0))
    ImageDraw.Draw(t).multiline_text((pad, pad), text, font=f, fill=fill, stroke_width=stroke,
                                     stroke_fill=sf, align="center", spacing=sp)
    if grad:
        al = t.split()[3]; g = Image.new("RGBA", t.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
        for yy in range(g.size[1]):
            k = yy / max(1, g.size[1] - 1)
            gd.line([(0, yy), (g.size[0], yy)],
                    fill=tuple(int(grad[0][i] + (grad[1][i] - grad[0][i]) * k) for i in range(3)) + (255,))
        g.putalpha(al); t = g
    if glow:
        r1, r2, r3, al = t.split()
        halo = Image.new("RGBA", t.size, tuple(glow[:3]) + (0,))
        halo.putalpha(al.point(lambda v: min(255, int(v * .85))))
        halo = halo.filter(ImageFilter.GaussianBlur(gs))
        base = Image.new("RGBA", t.size, (0, 0, 0, 0))
        base.alpha_composite(halo); base.alpha_composite(t); t = base
    lay = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    lay.alpha_composite(t, (int(TW * x - t.size[0] / 2), int(TH * y - t.size[1] / 2)))
    return lay

_SC = {}
def scrims():
    if not _SC:
        g = Image.new("L", (1, TH), 0); d = ImageDraw.Draw(g)
        for y in range(TH):
            d.line([(0, y), (1, y)], fill=int(150 * max(0., (y - TH * .74) / (TH * .26)) ** 1.4))
        g2 = Image.new("L", (1, TH), 0); d = ImageDraw.Draw(g2)
        for y in range(TH):
            d.line([(0, y), (1, y)], fill=int(120 * max(0., 1 - y / (TH * .30)) ** 1.6))
        _SC["s"] = tuple(Image.merge("RGBA", [Image.new("L", (TW, TH), 0)] * 3 + [a.resize((TW, TH))])
                         for a in (g, g2))
    return _SC["s"]

def bugs():
    l = Image.new("RGBA", (TW, TH), (0, 0, 0, 0)); d = ImageDraw.Draw(l)
    f = 13; h = int(f * 2.1)
    d.rounded_rectangle([14, 14, 152, 14 + h], 7, fill=(10, 12, 18, 130))
    d.ellipse([22, 14 + h // 2 - 4, 30, 14 + h // 2 + 4], fill=(255, 62, 62, 255))
    d.text([38, 14 + int(h * .3)], "LIVE · REEL", font=ImageFont.truetype(KUF, f), fill=(242, 242, 246, 228))
    d.rounded_rectangle([TW - 118, 14, TW - 14, 14 + h], 7, fill=(10, 12, 18, 130))
    d.text([TW - 108, 14 + int(h * .3)], "%s · 1080" % AR, font=ImageFont.truetype(KUF, f),
           fill=(255, 228, 170, 230))
    return l

def parts(n, seed):
    r = np.random.default_rng(seed)
    return dict(x=r.random(n), y=r.random(n) * 1.6 - .6, sp=r.uniform(.04, .17, n),
                sz=r.uniform(1.4, 5.4, n), ar=r.uniform(1.4, 2.7, n), rot=r.uniform(0, 6.283, n),
                spin=r.uniform(-4.5, 4.5, n), fl=r.uniform(2, 6.5, n), sw=r.uniform(.008, .055, n),
                sf=r.uniform(.4, 1.7, n), al=r.uniform(.28, .95, n), col=r.integers(0, len(PAL), n),
                dep=r.uniform(.15, 1., n))
def confetti(cv, P, t):
    d = ImageDraw.Draw(cv)
    for i in range(len(P["x"])):
        y = (P["y"][i] + P["sp"][i] * t) % 1.55 - .27
        x = (P["x"][i] + math.sin(t * P["sf"][i] + P["rot"][i]) * P["sw"][i]) % 1.2 - .1
        s = P["sz"][i] * (.45 + .55 * P["dep"][i])
        fl = abs(math.cos(t * P["fl"][i] + P["rot"][i]))
        hx, hy = max(.6, s * P["ar"][i] * fl) / 2, max(.9, s) / 2
        a = P["rot"][i] + t * P["spin"][i] * .35; ca, sa = math.cos(a), math.sin(a)
        cx, cy = x * TW, y * TH
        d.polygon([(cx - hx * ca + hy * sa, cy - hx * sa - hy * ca),
                   (cx + hx * ca + hy * sa, cy + hx * sa - hy * ca),
                   (cx + hx * ca - hy * sa, cy + hx * sa + hy * ca),
                   (cx - hx * ca - hy * sa, cy - hx * sa + hy * ca)],
                  fill=PAL[P["col"][i]] + (int(255 * P["al"][i] * (.4 + .6 * P["dep"][i])),))
def bokeh(n, seed):
    r = np.random.default_rng(seed)
    return dict(x=r.random(n), y=r.random(n), rr=r.uniform(5, 20, n), sp=r.uniform(-.012, .02, n),
                ph=r.uniform(0, 6.283, n), fr=r.uniform(.25, .9, n), al=r.uniform(.05, .24, n))
def draw_bokeh(cv, K, t):
    d = ImageDraw.Draw(cv)
    for i in range(len(K["x"])):
        y = (K["y"][i] + K["sp"][i] * t) % 1.0
        x = K["x"][i] + .02 * math.sin(t * K["fr"][i] + K["ph"][i])
        rr = K["rr"][i] * (1 + .25 * math.sin(t * K["fr"][i] * 1.7 + K["ph"][i]))
        a = int(255 * K["al"][i] * (.6 + .4 * math.sin(t * K["fr"][i] + K["ph"][i])))
        if a > 2:
            d.ellipse([x * TW - rr, y * TH - rr * .72, x * TW + rr, y * TH + rr * .72], fill=(255, 232, 178, a))
def rays(strength=1., seed=7, n=4):
    img = Image.new("RGBA", (TW, TH), (0, 0, 0, 0)); d = ImageDraw.Draw(img); r = np.random.default_rng(seed)
    for _ in range(n):
        cx = r.uniform(.06, .94) * TW; wt = r.uniform(26, 80); wb = wt * r.uniform(3.2, 5.5)
        sl = r.uniform(-.2, .2) * TW
        d.polygon([(cx - wt / 2, -20), (cx + wt / 2, -20), (cx + sl + wb / 2, TH * 1.05),
                   (cx + sl - wb / 2, TH * 1.05)], fill=(255, 244, 214, int(255 * r.uniform(.05, .13) * strength)))
    return img.filter(ImageFilter.GaussianBlur(24))

# ---------------------------------------------------------------- stages
def prep():
    for x in SHOTS:
        im = Image.open(os.path.join(FR, x["f"])).convert("RGB")
        sw, sh = im.size
        if not LAND:                                   # 9:16: crop the vertical band
            bw = int(round(sh * 9 / 16))
            x0 = min(max(0, int(sw * x["cx"]) - bw // 2), sw - bw)
            im = im.crop((x0, 0, x0 + bw, sh)).resize((W * 2, H * 2), Image.LANCZOS)
        elif sw / sh >= 1.7:                           # 16:9 out of a wide plate: full width
            bw = min(sw, int(round(sh * 16 / 9)))
            x0 = min(max(0, int(sw * x["cx"]) - bw // 2), sw - bw)
            im = im.crop((x0, 0, x0 + bw, sh)).resize((W * 2, H * 2), Image.LANCZOS)
        elif x.get("fill") == "bleed":                 # wide venue/crowd shot: full-bleed crop
            bh = int(round(sw * 9 / 16))
            y0 = min(max(0, int(sh * x.get("cy", .45)) - bh // 2), sh - bh)
            im = im.crop((0, y0, sw, y0 + bh)).resize((W * 2, H * 2), Image.LANCZOS)
        else:                                          # tall plate: dominant panel + blurred fill
            sc = max(W * 2 / sw, H * 2 / sh)
            bg = im.resize((int(sw * sc), int(sh * sc)), Image.LANCZOS)
            bx, by = (bg.width - W * 2) // 2, (bg.height - H * 2) // 2
            bg = bg.crop((bx, by, bx + W * 2, by + H * 2)).filter(ImageFilter.GaussianBlur(38))
            bg = ImageEnhance.Brightness(bg).enhance(.52)
            bg = ImageEnhance.Color(bg).enhance(.92)
            ph = int(H * 2 * 1.18); pw = int(round(ph * sw / sh))
            pan = im.resize((pw, ph), Image.LANCZOS)
            oy = min(max(0, int((ph - H * 2) * x.get("cy", .5))), ph - H * 2)
            pan = pan.crop((0, oy, pw, oy + H * 2))
            px = min(max(0, int((W * 2 - pw) * (.5 + (x["cx"] - .5) * 2))), W * 2 - pw)
            layer = Image.new("RGB", (W * 2, H * 2))
            layer.paste(pan, (px, 0))
            mk = Image.new("L", (W * 2, H * 2), 0)
            ImageDraw.Draw(mk).rectangle([px, -30, px + pw, H * 2 + 30], fill=255)
            mk = mk.filter(ImageFilter.GaussianBlur(52))
            im = Image.composite(layer, bg, mk)
        im = im.filter(ImageFilter.UnsharpMask(radius=3.0, percent=115, threshold=2))
        x["master"] = os.path.join(B, "m%d.png" % x["i"]); im.save(x["master"])
    print("prep ok")

def timeline():
    for i, s in enumerate(SEG):
        s["w"] = os.path.join(B, "sp%d.wav" % i); wav(os.path.join(AU, s["a"]), s["w"])
        d, sr = read_wav(s["w"]); s["speech"] = len(d) / sr
    carry = 0.0; cum = 0.0
    for i, s in enumerate(SEG):
        sh = [x for x in SHOTS if x["seg"] == i]
        ls = [l for x in sh for l in x["lines"]]
        ws = np.array([max(6., len(l) + 4 * l.count(".") + 7 * l.count("!") + 6 * l.count("…")) for l in ls])
        dd = s["speech"] * ws / ws.sum(); k = 0
        for x in sh:
            x["_ld"] = list(dd[k:k + len(x["lines"])]); k += len(x["lines"])
        tot = sum(sum(x["_ld"]) for x in sh) + LEAD + s["tail"]
        if tot < s["minimum"]:
            sh[-1]["_ex"] = s["minimum"] - tot
        for j, x in enumerate(sh):
            dur = sum(x["_ld"]) + x.get("_ex", 0.) + (LEAD if j == 0 else 0.)
            if j == len(sh) - 1:
                dur += s["tail"]
            start = cum - (x["tin"] if cum > 0 else 0.); cum = start + dur
            x["dur"] = dur; x["start"] = start; x["end"] = start + dur
            if j == 0:
                s["t0"] = start; carry = start + LEAD
            x["lg"] = []
            for l, d2 in zip(x["lines"], x["_ld"]):
                x["lg"].append((shape(l), carry, carry + d2)); carry += d2
            x["send"] = carry
            json.dump({k2: v for k2, v in x.items() if not k2.startswith("_") and k2 != "master"},
                      open(os.path.join(B, "t%d.json" % x["i"]), "w"), ensure_ascii=False)
    T = cum
    json.dump(dict(total=T), open(os.path.join(B, "tl.json"), "w"))
    print("total %.2fs" % T)
    for x in SHOTS:
        print("  shot%d %-14s %5.2f..%5.2f (%4.2f)" % (x["i"], x["f"], x["start"], x["end"], x["dur"]))

def load():
    T = json.load(open(os.path.join(B, "tl.json")))["total"]
    for i, x in enumerate(SHOTS):
        x.update(json.load(open(os.path.join(B, "t%d.json" % i))))
        x["master"] = os.path.join(B, "m%d.png" % i)
    return T

def tiles():
    for x in SHOTS:
        d = os.path.join(B, "t%d" % x["i"]); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        nf = int(round(x["dur"] * TFPS)) + 1
        P = parts(x["conf"], 501 + 37 * x["i"]); K = bokeh(16, 17 + x["i"])
        R1 = rays(x["rays"], 31 + x["i"]); R2 = rays(x["rays"] * .8, 71 + x["i"], 3); LBL = bugs()
        SUB = {s: text_layer(s, KUF, ts(27), (255, 255, 255, 252), max_w=int(TW * .9), stroke=2,
                             sf=(4, 6, 12, 240), glow=(0, 0, 0, 150), gs=7, y=.815) for s, a, b in x["lg"]}
        ex = []
        if "kicker" in x:
            k = x["kicker"]
            ex.append((text_layer(shape(k["t"]), KUF, ts(15), (255, 238, 196, 240), max_w=int(TW * .84),
                                  stroke=1, sf=(0, 0, 0, 190), y=.935), k["a"], k["b"], .5))
        if "title" in x:
            t = x["title"]; ln = x["lg"][t["line"]]
            ex.append((text_layer(shape(t["t"]), AMI, ts(52), GOLD + (255,), max_w=int(TW * .82), stroke=2,
                                  sf=GLO + (255,), glow=(255, 205, 95, 220), gs=13, grad=(GHI, GLO), y=.125),
                       max(0., ln[1] - x["start"] - t["a"]), ln[2] - x["start"] + t["hold"], .55))
        if "motto" in x:
            m = x["motto"]
            ex.append((text_layer(shape(m["t"]), AMI, ts(22), GOLD + (238,), max_w=int(TW * .84), stroke=1,
                                  sf=(8, 8, 12, 215), glow=(255, 200, 90, 140), gs=10, y=.095),
                       m["a"], x["dur"] - .3, .8))
        if "endcard" in x:
            e = x["endcard"]; t0 = x["send"] - x["start"] + .5
            ex.append((text_layer(shape(e["main"]), AMI, ts(62), GOLD + (255,), max_w=int(TW * .82), stroke=2,
                                  sf=GLO + (255,), glow=(255, 208, 100, 235), gs=15, grad=(GHI, GLO), y=.36),
                       t0, x["dur"], .7))
            ex.append((text_layer(shape(e["sub"]), KUF, ts(17), (246, 246, 248, 242), max_w=int(TW * .8),
                                  stroke=1, sf=(0, 0, 0, 215), y=.455), t0 + .35, x["dur"], .7))
            rl = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
            ImageDraw.Draw(rl).rectangle([int(TW * .3), int(TH * .416), int(TW * .7), int(TH * .416) + 2],
                                         fill=GOLD + (215,))
            ex.append((rl, t0 + .18, x["dur"], .7))
        bot, top = scrims()
        for k in range(nf):
            t = k / TFPS
            base = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
            for img, ph in ((R1, 0.), (R2, 1.9)):
                m = .55 + .45 * math.sin(t * .55 + ph)
                if m > .03:
                    r = img.copy(); r.putalpha(r.split()[3].point(lambda v: int(v * m)))
                    base.alpha_composite(r)
            draw_bokeh(base, K, t); confetti(base, P, t)
            base.alpha_composite(bot); base.alpha_composite(top); base.alpha_composite(LBL)
            gt = x["start"] + t
            for s, a, b in x["lg"]:
                if a <= gt <= b:
                    base.alpha_composite(SUB[s]); break
            for lay, a, b, f in ex:
                m = 0. if (t < a or t > b) else max(0., min(1., (t - a) / f, (b - t) / f))
                if m > .01:
                    l2 = lay.copy(); l2.putalpha(l2.split()[3].point(lambda v: int(v * m)))
                    base.alpha_composite(l2)
            base.save(os.path.join(d, "tile_%04d.png" % k))
        print("tiles shot%d: %d" % (x["i"], nf))

def clips():
    for x in SHOTS:
        N = int(round(x["dur"] * FPS)); z0, z1 = x["z"]; px0, py0, px1, py1 = x["p"]
        e = "on/%d" % max(1, N - 1)
        vf = ("[0:v]fps=%d,setsar=1,zoompan=z='%r+(%r-%r)*%s'"
              ":x='max(0,min(iw-iw/zoom,iw*(%r+(%r-%r)*%s)-(iw/zoom)/2))'"
              ":y='max(0,min(ih-ih/zoom,ih*(%r+(%r-%r)*%s)-(ih/zoom)/2))':d=1:s=%dx%d:fps=%d,"
              "eq=contrast=1.06:saturation=1.12:brightness=-0.012,"
              "colorbalance=rm=.02:bm=-.035:rh=-.025:bh=.055:gm=.010:bs=-.02,vignette=PI/4.2[base];"
              "[1:v]fps=%d,scale=%d:%d:flags=lanczos,format=rgba[tile];"
              "[base][tile]overlay=0:0:format=auto:eof_action=repeat,"
              "noise=alls=5:allf=t+u,unsharp=5:5:1.0:5:5:.4,format=yuv420p[v]") % (
            FPS, z0, z1, z0, e, px0, px1, px0, e, py0, py1, py0, e, W, H, FPS, TFPS, W, H)
        run([FF, "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(FPS),
             "-t", "%.3f" % (x["dur"] + .14), "-i", x["master"], "-framerate", str(TFPS),
             "-start_number", "0", "-i", os.path.join(B, "t%d" % x["i"], "tile_%04d.png"),
             "-filter_complex", vf, "-map", "[v]", "-frames:v", str(N + 3), "-c:v", "libx264",
             "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", "-g", "15", "-r", str(FPS),
             os.path.join(B, "c%d.mp4" % x["i"])])
        print("clip%d ok" % x["i"])

def speech():
    inp, f, labs = [], [], []
    for i, s in enumerate(SEG):
        ms = int(round((s["t0"] + LEAD) * 1000)) if "t0" in s else 0
        inp += ["-i", s["w"]]; f.append("[%d:a]adelay=%d|%d[a%d]" % (i, ms, ms, i)); labs.append("[a%d]" % i)
    T = json.load(open(os.path.join(B, "tl.json")))["total"] + .5
    f.append("%samix=inputs=%d:normalize=0,apad=whole_dur=%.3f,aformat=sample_fmts=s16:sample_rates=%d[sp]"
             % ("".join(labs), len(SEG), T, SR))
    run([FF, "-y", "-loglevel", "error"] + inp + ["-filter_complex", ";".join(f), "-map", "[sp]",
        "-c:a", "pcm_s16le", "-ar", str(SR), "-ac", "1", os.path.join(B, "speech.wav")])
    print("speech.wav ok")

def _ma(x, k):
    c = np.cumsum(np.insert(x, 0, 0.)); return (c[k:] - c[:-k]) / k if k > 1 else x
def _bn(n, lo, hi, seed, tilt=0.):
    n = max(64, int(n)); X = np.fft.rfft(np.random.default_rng(seed).standard_normal(n))
    f = np.fft.rfftfreq(n, 1. / SR); m = ((f > lo) & (f < hi)).astype(float)
    if tilt:
        m *= (np.clip(f, 20., SR / 2) / 1000.) ** tilt
    y = np.fft.irfft(X * m, n); return y / (np.abs(y).max() + 1e-9)

def score():
    T = json.load(open(os.path.join(B, "tl.json")))["total"] + .35; n = int(T * SR)
    sp, _ = read_wav(os.path.join(B, "speech.wav")); sp = sp.astype(float)
    sp = np.concatenate([sp, np.zeros(max(0, n - len(sp)))])
    win = int(.04 * SR); nb = n // win
    r = np.sqrt((sp[:nb * win].reshape(nb, win) ** 2).mean(1)); e = _ma(r, 14)
    e = np.clip(e / (np.percentile(e, 97) + 1e-9), 0, 1)
    e = np.clip(_ma(np.concatenate([e, e[-1:] * np.zeros(40)]), 26)[:nb], 0, 1)
    env = np.zeros(n); env[:nb * win] = np.repeat(e, win)
    mus = np.zeros(n); crd = np.zeros(n); tt = np.arange(n) / SR
    def add(bus, sig, t0, g=1.):
        i0 = int(t0 * SR)
        if i0 >= n - 64 or len(sig) == 0: return
        if i0 < 0: sig = sig[-i0:]; i0 = 0
        i1 = min(n, i0 + len(sig))
        if i1 - i0 > 0: bus[i0:i1] += sig[:i1 - i0] * g
    def pad(fs, t0, d, amp):
        m = int(d * SR); t = np.arange(m) / SR; s = np.zeros(m)
        for f_ in fs:
            for k, dd in ((1., -.0045), (.72, 0.), (.5, .0045)):
                s += k * np.sin(2 * np.pi * f_ * (1 + dd) * t + dd * 40)
        s *= np.minimum(1., t / max(.05, d * .26)) * np.minimum(1., np.maximum(0, (d - t) / max(.05, d * .34)))
        X = np.fft.rfft(s); f2 = np.fft.rfftfreq(m, 1. / SR)
        add(mus, np.fft.irfft(X * np.exp(-(f2 / 2500.) ** 2), m), t0, amp)
    def kick(t0, g=1.):
        m = int(.42 * SR); t = np.arange(m) / SR
        s = np.sin(2 * np.pi * np.cumsum(46 + 88 * np.exp(-t * 34)) / SR) * np.exp(-t * 9.5)
        add(mus, s + .2 * _bn(m, 900, 9000, 5) * np.exp(-t * 90), t0, .95 * g)
    def boom(t0, g=1.):
        m = int(1.5 * SR); t = np.arange(m) / SR
        s = np.sin(2 * np.pi * np.cumsum(41 + 26 * np.exp(-t * 12)) / SR) * np.exp(-t * 3.1)
        add(mus, s + .45 * _bn(m, 60, 900, 11) * np.exp(-t * 13), t0, g)
    def riser(t0, d, g=1.):
        m = int(d * SR); t = np.arange(m) / SR; raw = _bn(m, 200, 11000, 21)
        step = max(1024, m // 22); out = np.zeros(m)
        for i in range(0, m, step):
            sg = raw[i:i + step]; X = np.fft.rfft(sg); fs = np.fft.rfftfreq(len(sg), 1. / SR)
            out[i:i + len(sg)] = np.fft.irfft(X * ((fs > 320 * (1 + 7 * (i / m))) & (fs < 12000)), len(sg))
        add(mus, out * (t / d) ** 2.1 + .3 * np.sin(2 * np.pi * np.cumsum(190 + 640 * (t / d) ** 1.6) / SR)
            * (t / d) ** 3, t0, .6 * g)
    def clap(t0, g=1.):
        m = int(.13 * SR); t = np.arange(m) / SR
        add(crd, _bn(m, 700, 6500, 44) * (np.exp(-t * 34) + .55 * np.exp(-((t - .03) ** 2) * 900)), t0, .45 * g)
    add(crd, _bn(n, 240, 4200, 3, tilt=-.45) * (.72 + .28 * np.sin(2 * np.pi * .11 * tt + 1.1))
        * np.clip(.35 + .65 * np.maximum(0, np.sin(2 * np.pi * tt / 21.)), 0, 1), 0, .62)
    for i, x in enumerate(SHOTS):
        g = .95 if i in (0, 1, len(SHOTS) - 1) else .45
        m = int(2.6 * SR); t = np.arange(m) / SR
        add(crd, _bn(m, 300, 6000, 60 + i) * (1 - np.exp(-t * 9)) * np.exp(-t * 1.15), max(0., x["start"] - .12), .5 * g)
        rng = np.random.default_rng(90 + i)
        for _ in range(int(30 * g) + 4):
            clap(max(0., x["start"] - .1) + float(rng.uniform(-.1, 2.2)), .26 * g)
        if x["tin"] > .3:
            riser(max(0., x["start"] - 1.05), 1.05, .5); boom(max(0., x["start"] - .03), .35)
    q1 = SEG[1]["t0"] if len(SEG) > 1 else SEG[0]["t0"]
    q2 = SEG[2]["t0"] if len(SEG) > 2 else q1 + 8.0
    q3 = SEG[3]["t0"] if len(SEG) > 3 else SEG[-1]["t0"]
    boom(q1 + .3, .95); riser(max(0., q1 - .95), 1.25, .8)
    boom(SHOTS[-1]["send"] + .45, 1.05)
    b = 60. / 122.; roots = [110., 87.31, 130.81, 98.]; t0m = q1; bars = 8 * b
    k, t = 0, t0m
    while t < T - 1.2:
        bar = roots[(k // 2) % 4]; en = min(1., max(0., (t - t0m) / 9.))
        if t > q3:
            en = 1.
        pad([bar, bar * 1.5, bar * 2., bar * 2.5], t, bars * .98, .13 + .13 * en)
        for i in range(8):
            bt = t + i * 2 * b
            if bt > T - 1.3: break
            if t < q2:
                if i % 4 == 0: kick(bt, .7)
            else:
                kick(bt, 1. if i % 2 == 0 else .5)
                if i % 2 == 1:
                    m = int(.06 * SR); t2 = np.arange(m) / SR
                    add(mus, _bn(m, 3200, 14000, 33) * np.exp(-t2 * 70), bt + b * .5, .26)
                if t > q3 and i % 4 == 3: kick(bt + b * .75, .45)
        k += 1; t += bars
    for f_, g in ((55., .17), (110., .05)):
        add(mus, np.sin(2 * np.pi * f_ * tt + .6 * np.sin(2 * np.pi * .07 * tt)) * np.clip((tt - t0m) / 7., 0, 1), 0, g)
    rl = int(.75 * SR); rev = _bn(rl, 300, 5000, 77) * np.exp(-np.arange(rl) / SR * 5.2); rev /= rev.max()
    def verb(x, wet):
        N = 1 << int(np.ceil(np.log2(len(x) + rl)))
        m = np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(rev, N), N)[:len(x)]
        return x * (1 - wet) + m / (np.abs(m).max() + 1e-9) * wet
    mus, crd = verb(mus, .26), verb(crd, .34)
    out = mus * (1 - .4 * env) * .62 + crd * (1 - .52 * env) * .5
    fo, fe = int(.55 * SR), int(1.15 * SR)
    out[:fo] *= np.linspace(0, 1, fo); out[-fe:] *= np.linspace(1, 0, fe) ** 1.3
    out = np.tanh(out * 1.35) / math.tanh(1.35); out = out / (np.abs(out).max() + 1e-9) * .3
    write_wav(os.path.join(B, "score.wav"), np.stack([out, np.roll(out, 2) * .99], 1))
    print("score.wav ok")

def final():
    T = json.load(open(os.path.join(B, "tl.json")))["total"]
    inp, f = [], []
    for x in SHOTS:
        inp += ["-i", os.path.join(B, "c%d.mp4" % x["i"])]
    prev = "[0:v]"
    for i in range(1, len(SHOTS)):
        nxt = "[vx%d]" % i if i < len(SHOTS) - 1 else "[vv]"
        dd = min(SHOTS[i]["tin"], max(.02, SHOTS[i - 1]["dur"] * .4))
        f.append("%s[%d:v]xfade=transition=fade:duration=%.4f:offset=%.4f%s"
                 % (prev, i, dd, SHOTS[i]["start"], nxt)); prev = nxt
    f.append("[vv]fade=t=in:st=0:d=0.85,fade=t=out:st=%.3f:d=1.15,format=yuv420p[v]" % (T - 1.15))
    d, _ = read_wav(os.path.join(B, "speech.wav")); g = min(8., .88 / (np.abs(d).max() + 1e-9))
    ia, ib = len(SHOTS), len(SHOTS) + 1        # audio inputs follow the N clip inputs
    f.append("[%d:a]volume=%.3f,acompressor=threshold=0.12:ratio=2.2:attack=8:release=180,"
             "aformat=sample_fmts=fltp:channel_layouts=stereo[s];[%d:a][s]"
             "amix=inputs=2:normalize=0,aformat=sample_fmts=fltp:channel_layouts=stereo,"
             "highpass=f=38,alimiter=limit=0.97:level=false[a]" % (ia, g, ib))
    out = os.path.join(M, "haya_shami_vertical.mp4")
    run([FF, "-y", "-loglevel", "error"] + inp + ["-i", os.path.join(B, "speech.wav"),
        "-i", os.path.join(B, "score.wav"), "-filter_complex", ";".join(f), "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "24", "-pix_fmt", "yuv420p", "-profile:v", "high",
        "-level", "4.1", "-g", "60", "-c:a", "aac", "-b:a", "160k", "-ar", str(SR), "-movflags",
        "+faststart", "-shortest", out])
    sm = os.path.join(M, "haya_shami_vertical_small.mp4")
    run([FF, "-y", "-loglevel", "error", "-i", out, "-filter_complex",
         "[0:v]scale=%d:%d:flags=lanczos,format=yuv420p[v]" % (W // 2, H // 2), "-map", "[v]", "-map", "0:a",
         "-c:v", "libx264", "-preset", "medium", "-crf", "30", "-profile:v", "main", "-level", "3.1",
         "-g", "60", "-c:a", "copy", "-movflags", "+faststart", sm])
    pt = (SEG[1]["t0"] if len(SEG) > 1 else SEG[0]["t0"]) + 1.0
    run([FF, "-y", "-loglevel", "error", "-ss", "%.2f" % pt, "-i", out, "-frames:v", "1",
         "-q:v", "3", os.path.join(M, "haya_poster.jpg")])
    run([FF, "-y", "-loglevel", "error", "-ss", "%.2f" % max(0.0, pt - .6), "-t", "7.5", "-i", out,
         "-vf", ("fps=9,scale=%d:-1:flags=lanczos" % (430 if LAND else 300)) + ",split[a][b];[a]palettegen=32[p];[b][p]"
         "paletteuse=dither=sierra2_4a", os.path.join(M, "haya_intro.gif")])
    for p in (out, sm, os.path.join(M, "haya_poster.jpg"), os.path.join(M, "haya_intro.gif")):
        print("%-46s %6.2f MB" % (os.path.basename(p), os.path.getsize(p) / 1e6))

if __name__ == "__main__":
    only = sys.argv[1:] or ["prep", "timeline", "tiles", "clips", "speech", "score", "final"]
    st = {"prep": prep, "timeline": timeline, "tiles": tiles, "clips": clips,
          "speech": speech, "score": score, "final": final}
    for k in only:
        st[k]()
