#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Glue the 4.2 s series opener in front of any finished film.

    python media/brand/attach.py media/series/e1/out/haya_e1_web.mp4 ...
    python media/brand/attach.py --all          # every web copy (both formats)

Each target keeps its own size/fps/audio layout; the opener is matched to it, so the seam is
invisible.  Output: <name>_op.mp4 beside the source.
"""
import os, re, sys, glob, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
MEDIA = os.path.dirname(HERE)
import imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe()
OP = {"land": os.path.join(HERE, "opener_land.mp4"), "vert": os.path.join(HERE, "opener_vert.mp4")}


def probe(p):
    """(w, h, fps) from ffmpeg's own stream line — this build has no ffprobe"""
    out = subprocess.run([FF, "-i", p], capture_output=True, text=True).stderr
    m = re.search(r"Video:.*?(\d{3,5})x(\d{3,5}).*?([\d.]+) fps", out, re.S)
    if not m:
        raise SystemExit("cannot read video stream of " + p)
    return int(m.group(1)), int(m.group(2)), float(m.group(3))


def attach(src):
    w, h, fps = probe(src)
    key = "land" if w >= h else "vert"
    op = OP[key]
    if not os.path.exists(op):
        raise SystemExit("missing %s — run: %s media/brand/opener.py" % (op, "AR=16:9 " if key == "land" else ""))
    ow, oh, ofps = probe(op)
    dst = src[:-4] + "_op.mp4"
    chain = ("[0:v]fps=%g,scale=%d:%d:flags=lanczos,setsar=1,format=yuv420p[v0];"
             "[1:v]fps=%g,scale=%d:%d:flags=lanczos,setsar=1,format=yuv420p[v1];"
             "[0:a]aformat=sample_fmts=fltp:channel_layouts=stereo,aresample=48000[a0];"
             "[1:a]aformat=sample_fmts=fltp:channel_layouts=stereo,aresample=48000[a1];"
             "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]") % (fps, w, h, fps, w, h)
    cmd = [FF, "-y", "-loglevel", "error", "-i", op, "-i", src, "-filter_complex", chain,
           "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "24",
           "-pix_fmt", "yuv420p", "-r", "%g" % fps, "-g", "60", "-c:a", "aac", "-b:a", "160k",
           "-ar", "48000", "-movflags", "+faststart", dst]
    subprocess.run(cmd, check=True)
    a = (os.path.getsize(src) + os.path.getsize(dst)) / 1e6
    print("  %-46s %d×%d · +4.2 س → %.2f MB" % (os.path.relpath(dst, MEDIA), w, h, os.path.getsize(dst) / 1e6))


def main():
    args = sys.argv[1:]
    if args == ["--all"]:
        args = sorted(glob.glob(os.path.join(MEDIA, "series", "*", "out", "*_web.mp4")))
        args = [a for a in args if not a.endswith("_op.mp4")]
        args += [os.path.join(MEDIA, "haya_shami_vertical_small.mp4")]
    for a in args:
        p = a if os.path.isabs(a) else os.path.join(os.path.abspath("."), a)
        if os.path.exists(p):
            attach(p)
        else:
            print("skip (missing):", a)


if __name__ == "__main__":
    main()
