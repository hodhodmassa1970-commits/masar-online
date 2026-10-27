#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""4.2 s series opener ("أميرة الجماهير" logo sting) rendered with the SAME look engine as the
films, so gluing it in front of any episode leaves no visible seam: same plate grade
(contrast / saturation / teal-gold balance / vignette / grain), same Amiri logotype and gold
rule, same confetti + bokeh + light-ray particle fields, and a 122 BPM cue that hands off cleanly.

    python media/brand/opener.py            ->  media/brand/opener_vert.mp4   (1080x1920)
    AR=16:9 python media/brand/opener.py    ->  media/brand/opener_land.mp4   (1920x1080)

Then prepend it to a film with:  python media/brand/attach.py media/series/e1/out/haya_e1_web.mp4
"""
import os, sys, math, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                       # .../media  -> build_reel
import build_reel as br                                          # noqa: E402

DUR, FPS = 4.2, 30
N = int(round(DUR * FPS))
BEAT = 60.0 / 122.0
PLATE = "s4_heart.png"
TAIL = "_land" if br.LAND else "_vert"
OUT = os.path.join(HERE, "opener%s.mp4" % TAIL)
GIF = OUT.replace(".mp4", ".gif")
WORK = os.path.join(HERE, "work")
TW, TH = br.TW, br.TH


def env(t, a, b, c, d):
    """ramp 0→1 across a..b, hold until c, ramp 1→0 until d"""
    if t <= a or t >= d:
        return 0.0
    if t < b:
        return (t - a) / max(1e-6, b - a)
    if t <= c:
        return 1.0
    return 1.0 - (t - c) / max(1e-6, d - c)


def alpha(im, k):
    q = im.copy()
    q.putalpha(q.split()[3].point(lambda v: int(v * max(0.0, min(1.0, k)))))
    return q


def cue(path):
    """sub pad, riser, soft impact when the logotype lands, bell arpeggio, clean hand-off"""
    sr, n = br.SR, int(DUR * br.SR)
    t = np.arange(n) / sr
    x = np.zeros(n)

    pad = (np.sin(2 * np.pi * 55.0 * t) + .55 * np.sin(2 * np.pi * 110.0 * t)
           + .28 * np.sin(2 * np.pi * 164.8 * t))
    x += np.clip(t / .8, 0, 1) * (1 - np.clip((t - 3.5) / .6, 0, 1)) * pad * .30

    r = np.random.default_rng(9)
    nz = np.convolve(r.standard_normal(n), np.ones(48) / 48, mode="same")
    rise = np.clip(t / .78, 0, 1) ** 2.4 * (1 - np.clip((t - .78) / .12, 0, 1))
    x += rise * nz * .34

    hit = np.exp(-np.maximum(0, t - .74) * 26.0) * np.sin(2 * np.pi * 96 * np.maximum(0, t - .74))
    x += (t > .74) * hit * .55

    bell = np.zeros(n)
    for k, f in enumerate([1046.5, 1318.5, 1568.0, 2093.0]):
        t0 = .78 + k * BEAT * .5
        bell += np.exp(-np.maximum(0, t - t0) * 7.0) * (t > t0) * np.sin(2 * np.pi * f * (t - t0)) * (.30 - .04 * k)
    x += bell * .7

    x += np.exp(-np.maximum(0, t - 3.55) * 4.2) * (t > 3.55) * np.sin(2 * np.pi * 82.4 * t) * .12
    x = np.convolve(x, np.ones(9) / 9, mode="same")
    x *= 1 - np.clip((t - (DUR - .28)) / .28, 0, 1) * .85
    x = x / (np.abs(x).max() + 1e-9) * .50
    br.write_wav(path, np.stack([x, x], 1))


def main():
    os.makedirs(WORK, exist_ok=True)
    for f in glob.glob(os.path.join(WORK, "*")):
        os.remove(f)

    bg = Image.open(os.path.join(br.M, "frames", PLATE)).convert("RGB")
    s = max(TW / bg.width, TH / bg.height)
    bg = bg.resize((int(bg.width * s + .5), int(bg.height * s + .5)), Image.LANCZOS)
    bx, by = (bg.width - TW) // 2, (bg.height - TH) // 2
    bg = bg.crop((bx, by, bx + TW, by + TH)).filter(ImageFilter.GaussianBlur(3))
    bg = ImageEnhance.Brightness(bg).enhance(.47)
    bg = ImageEnhance.Color(bg).enhance(.90).convert("RGBA")

    P = br.parts(120 if br.LAND else 96, 4211)
    K = br.bokeh(14, 909)
    R1, R2 = br.rays(.62, 1207, 4), br.rays(.50, 5150, 3)

    kick = br.text_layer(br.shape("مسلسل هيا"), br.KUF, br.ts(17), (255, 228, 170, 245),
                         max_w=int(TW * .8), stroke=1, sf=(6, 8, 14, 220), y=.402)
    logo = br.text_layer(br.shape("أميرة|الجماهير"), br.AMI, br.ts(66), (255, 236, 170, 255),
                         max_w=int(TW * .84), stroke=2, sf=(20, 14, 2, 255),
                         glow=(255, 200, 90, 235), gs=17, grad=(br.GHI, (232, 180, 66)), y=.50)
    sub = br.text_layer(br.shape("ثماني حلقات من حكايتها"), br.KUF, br.ts(18), (228, 235, 244, 235),
                        max_w=int(TW * .8), stroke=1, sf=(4, 6, 12, 220), y=.612)

    for k in range(N):
        t = k / FPS
        fade = min(1.0, t / .38) * (1 - .30 * min(1.0, max(0.0, (t - 3.72) / .44)))
        cv = ImageEnhance.Brightness(bg).enhance(max(.03, fade))

        rw = .30 + .70 * env(t, .25, 1.15, 3.35, 4.0)
        lay = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
        for R, dx, dy, m in ((R1, 0, int(-16 * t), .90), (R2, int(24 * math.sin(t * .6)), int(-9 * t), .55)):
            q = R.copy()
            q.putalpha(q.split()[3].point(lambda v: int(v * rw * m)))
            lay.alpha_composite(q, (dx, dy))
        cv.alpha_composite(lay)

        if t > .28:
            l2 = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
            br.confetti(l2, P, t * .5 + 3.0)
            br.draw_bokeh(l2, K, t * .5 + 3.0)
            cv.alpha_composite(alpha(l2, env(t, .28, 1.1, 3.5, 4.1)))

        cv.alpha_composite(alpha(kick, env(t, .30, .62, 3.72, 4.06)))

        la = env(t, .62, 1.02, 3.72, 4.08)
        if la > .01:
            z = 1.07 - .07 * min(1.0, max(0.0, (t - .62) / .8))
            w, h = int(TW * z), int(TH * z)
            q = logo.resize((w, h), Image.LANCZOS)
            cx, cy = (w - TW) // 2, (h - TH) // 2
            q = q.crop((cx, cy, cx + TW, cy + TH)) if (w > TW and h > TH) else q
            cv.alpha_composite(alpha(q, la), (0, 0))

        gw = int(TW * .68 * env(t, .95, 1.75, 3.7, 4.05))
        if gw > 6:
            y = int(TH * .578)
            ImageDraw.Draw(cv).rectangle([(TW - gw) // 2, y, (TW + gw) // 2, y + max(3, br.ts(4))],
                                         fill=br.GOLD + (int(230 * la),))
        cv.alpha_composite(alpha(sub, env(t, 1.35, 2.0, 3.7, 4.06)))
        cv.convert("RGB").save(os.path.join(WORK, "op_%04d.png" % k))

    cue(os.path.join(WORK, "cue.wav"))
    chain = ("[0:v]fps=%d,setsar=1,scale=%d:%d:flags=lanczos,"
             "eq=contrast=1.06:saturation=1.12:brightness=-0.012,"
             "colorbalance=rm=.02:bm=-.035:rh=-.025:bh=.055:gm=.010:bs=-.02,vignette=PI/4.2,"
             "noise=alls=5:allf=t+u,unsharp=5:5:1.0:5:5:.4,format=yuv420p[v];"
             "[1:a]aformat=sample_fmts=fltp:channel_layouts=stereo[a]") % (FPS, br.W, br.H)
    br.run([br.FF, "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(WORK, "op_%04d.png"),
            "-i", os.path.join(WORK, "cue.wav"), "-filter_complex", chain, "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "160k", "-ar", str(br.SR), "-movflags", "+faststart", "-shortest", OUT])
    br.run([br.FF, "-y", "-loglevel", "error", "-i", OUT, "-vf",
            "fps=6,scale=460:-1:flags=lanczos,split[a][b];[a]palettegen=32[p];[b][p]paletteuse=dither=sierra2_4a",
            GIF])
    print("wrote %s · %.2f MB   (+ %s)" % (OUT, os.path.getsize(OUT) / 1e6, os.path.basename(GIF)))


if __name__ == "__main__":
    main()
