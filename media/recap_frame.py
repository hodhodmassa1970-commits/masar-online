#!/usr/bin/env python3
# rebuilds the small viewer-friendly gif for a landscape cut
import os, sys, glob, subprocess
from PIL import Image
import imageio_ffmpeg
slug = {"g1": "haya_g1", "e0": "haya_e0", "pilot": "haya_pilot"}[sys.argv[1]]
od = "/home/user/masar-online/media/series/%s/out" % sys.argv[1]
src = os.path.join(od, "%s_land_web.mp4" % slug)
out = os.path.join(od, "%s_land_preview.gif" % slug)
ff = imageio_ffmpeg.get_ffmpeg_exe()
os.makedirs("/tmp/lp2", exist_ok=True)
for f in glob.glob("/tmp/lp2/*"): os.remove(f)
subprocess.run([ff, "-loglevel", "error", "-y", "-i", src, "-vf",
                "fps=3,scale=480:-1:flags=lanczos", "/tmp/lp2/f_%03d.png"], check=True)
fs = sorted(glob.glob("/tmp/lp2/f_*.png")); step = max(1, len(fs) // 15)
fr = [Image.open(p).convert("RGB").quantize(colors=190, method=Image.MEDIANCUT) for p in fs[::step]]
fr[0].save(out, save_all=True, append_images=fr[1:], duration=330, loop=0, optimize=True)
print("  → %s  %.2f MB (%d frames)" % (out, os.path.getsize(out) / 1e6, len(fr)))
