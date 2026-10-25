#!/bin/bash
# v2 landscape re-cuts: the tiles are still valid (timing/overlays unchanged), so only
# prep -> clips -> final are re-run. ~3x faster than a full render.
cd /home/user/masar-online || exit 1
export AR=16:9
PY=/home/user/.venv/bin/python
for e in g1 e0 pilot; do
  echo "@@START $e $(date +%H:%M:%S)"
  $PY media/episode.py media/series/$e/$e.json timeline prep clips speech score final > /tmp/land2_$e.log 2>&1
  if [ $? -eq 0 ]; then
    $PY media/recap_frame.py "$e" >> /tmp/land2_$e.log 2>&1
    git add -A media
    git commit -q -m "$e: landscape v2 — dominant feathered panel + full-bleed crowd shots" || echo "@@COMMIT-FAIL $e"
    git push -q origin arena/489e96d8-masar-online || echo "@@PUSH-FAIL $e"
    echo "@@PUSHED $e $(date +%H:%M:%S)"
  else
    echo "@@FAILED $e"; tail -14 /tmp/land2_$e.log
  fi
done
echo "@@ALL-DONE $(date +%H:%M:%S)"
