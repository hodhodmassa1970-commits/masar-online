#!/bin/bash
# 16:9 (YouTube) cuts of the flagship episodes; commits and pushes each one as it lands.
cd /home/user/masar-online || exit 1
export AR=16:9
PY=/home/user/.venv/bin/python
for e in g1 e0 pilot; do
  echo "@@START $e $(date +%H:%M:%S)"
  $PY media/episode.py media/series/$e/$e.json > /tmp/land_$e.log 2>&1
  if [ $? -eq 0 ]; then
    $PY - <<PYEOF
from PIL import Image
import glob, os, subprocess
slug = {"g1":"haya_g1","e0":"haya_e0","pilot":"haya_pilot"}["$e"]
src = "media/series/$e/out/%s_land_web.mp4" % slug
out = "media/series/$e/out/%s_land_preview.gif" % slug
if os.path.exists(src):
    os.makedirs("/tmp/lp", exist_ok=True)
    for f in glob.glob("/tmp/lp/*"): os.remove(f)
    ff = subprocess.run(["/home/user/.venv/bin/python","-c","import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"],capture_output=True,text=True).stdout.strip()
    subprocess.run([ff,"-loglevel","error","-y","-i",src,"-vf","fps=3,scale=430:-1:flags=lanczos","/tmp/lp/f_%03d.png"],check=True)
    fs = sorted(glob.glob("/tmp/lp/f_*.png")); step = max(1, len(fs)//15)
    fr = [Image.open(p).convert("RGB").quantize(colors=190, method=Image.MEDIANCUT) for p in fs[::step]]
    fr[0].save(out, save_all=True, append_images=fr[1:], duration=330, loop=0, optimize=True)
    print("  → %s  %.2f MB (%d frames)" % (out, os.path.getsize(out)/1e6, len(fr)))
PYEOF
    git add -A media
    git commit -q -m "$e: 16:9 landscape cut (blurred-fill framing keeps the full outfit)" || echo "@@COMMIT-FAIL $e"
    git push -q origin arena/489e96d8-masar-online || echo "@@PUSH-FAIL $e"
    echo "@@PUSHED $e $(date +%H:%M:%S)"
  else
    echo "@@FAILED $e — tail:"; tail -12 /tmp/land_$e.log
  fi
done
echo "@@ALL-DONE $(date +%H:%M:%S)"
