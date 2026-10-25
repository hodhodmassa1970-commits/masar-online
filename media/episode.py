#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Solve Haya's episodes — config-driven renderer built on media/build_reel.py.

    python episode.py media/series/e1/e1.json

The config JSON holds everything that changes per episode:
  { "title": "...", "frames": "<dir>", "seg": [ {a, tail, minimum}, ... ],
    "shots": [ {f, seg, tin, cx, rays, conf, z:[..], p:[..], lines:[..],
                kicker|title|motto|endcard: {...}}, ... ] }
Everything else (identity anchor = frames + media/reference.jpg, one voice,
9:16 framing, subtitles, particles, colour grade, score) is reused unchanged
so every episode keeps the same look and the same voice.
"""
import os, sys, json, shutil, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
MEDIA = HERE
sys.path.insert(0, MEDIA)

cfg_path = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(MEDIA, "series/e1/e1.json"))
cfg = json.load(open(cfg_path, encoding="utf-8"))
slug = cfg.get("slug") or os.path.basename(os.path.dirname(cfg_path))
sfx = "_land" if os.environ.get("AR", "").startswith("16") else ""
work = os.environ.get("WORK") or os.path.join(MEDIA, "work_" + slug + sfx)
os.makedirs(work, exist_ok=True)
os.environ["WORK"] = work                      # read by build_reel at import time

import build_reel as br                         # noqa: E402

br.AU = os.path.dirname(cfg_path)               # per-episode audio folder
if cfg.get("frames"):
    br.FR = cfg["frames"] if os.path.isabs(cfg["frames"]) else os.path.join(MEDIA, cfg["frames"])
br.SEG[:] = cfg["seg"]
shots = cfg["shots"]
for i, x in enumerate(shots):
    x["i"] = i
    for k in ("z", "p"):
        x[k] = tuple(x[k])
    x.setdefault("tin", br.DISS)
    x.setdefault("rays", .6)
    x.setdefault("conf", 170)
    x.setdefault("cx", .5)
br.SHOTS[:] = shots

# keep the pilot's fixed output names, but write into the episode dir, then rename
tmp = os.path.join(work, "out")
shutil.rmtree(tmp, ignore_errors=True)
os.makedirs(tmp, exist_ok=True)
real_M, br.M = br.M, tmp

ALL = ("prep", "timeline", "tiles", "clips", "speech", "score", "final")
stages = tuple(sys.argv[2:]) or ALL
if "timeline" not in stages and ("score" in stages or "final" in stages):
    stages = ("timeline",) + stages          # cue times live in memory
for stage in stages:
    print("\n### " + stage, flush=True)
    getattr(br, stage)()

dst = os.path.join(os.path.dirname(cfg_path), "out")
os.makedirs(dst, exist_ok=True)
for f in os.listdir(dst):                      # refresh only this format's own outputs
    if f.startswith(slug + sfx):
        os.remove(os.path.join(dst, f))
names = {"haya_shami_vertical.mp4": "%s%s_hd.mp4" % (slug, sfx),
         "haya_shami_vertical_small.mp4": "%s%s_web.mp4" % (slug, sfx),
         "haya_poster.jpg": slug + sfx + "_poster.jpg", "haya_intro.gif": slug + sfx + "_teaser.gif"}
for a, b in names.items():
    src = os.path.join(tmp, a)
    if os.path.exists(src):
        shutil.move(src, os.path.join(dst, b))
        print("  → media/%s  %.2f MB" % (os.path.relpath(os.path.join(dst, b), MEDIA),
                                          os.path.getsize(os.path.join(dst, b)) / 1e6))

# a contact sheet of the episode key art for quick review in the file viewer
from PIL import Image
tiles, cw = [], 360
for x in shots:
    p = os.path.join(br.FR, x["f"])
    im = Image.open(p).convert("RGB")
    w, h = br.W, br.H
    if w > h:                                   # 16:9 contact sheet
        bw = min(im.width, int(round(im.height * 16 / 9)))
        x0 = min(max(0, int(im.width * x.get("cx", .5)) - bw // 2), im.width - bw)
        im = im.crop((x0, 0, x0 + bw, im.height)).resize((cw, int(cw * 9 / 16)), Image.LANCZOS)
    else:
        bw = int(round(im.height * 9 / 16)); x0 = min(max(0, int(im.width * x.get("cx", .5)) - bw // 2), im.width - bw)
        im = im.crop((x0, 0, x0 + bw, im.height)).resize((cw, int(cw * 16 / 9)), Image.LANCZOS)
    tiles.append(im)
phh = int(cw * (9 / 16 if w > h else 16 / 9))
sheet = Image.new("RGB", (cw * len(tiles), phh), (10, 12, 18))
for i, t in enumerate(tiles):
    sheet.paste(t, (i * cw, 0))
sp = os.path.join(dst, slug + sfx + "_keyart.png")
sheet.save(sp)
print("  → media/%s" % os.path.relpath(sp, MEDIA))
print("\nepisode %s done · %.2fs" % (slug, json.load(open(os.path.join(work, "tl.json")))["total"]))
