#!/bin/bash
# Renders the remaining Haya episodes in sequence, committing each one as it lands
# so nothing is lost if the sandbox or the turn is interrupted.
cd /home/user/masar-online || exit 1
PY=/home/user/.venv/bin/python
for e in e4 e5 e6 e1; do
  echo "@@START $e $(date +%H:%M:%S)"
  $PY media/episode.py media/series/$e/$e.json > /tmp/render_$e.log 2>&1
  rc=$?
  tail -6 /tmp/render_$e.log
  if [ $rc -eq 0 ]; then
    git add -A media
    git commit -q -m "$e: rendered episode (series batch)" || echo "@@COMMIT-FAIL $e"
    git push -q origin arena/489e96d8-masar-online || echo "@@PUSH-FAIL $e"
    echo "@@PUSHED $e $(date +%H:%M:%S)"
  else
    echo "@@FAILED $e (rc=$rc)"
  fi
done
echo "@@ALL-DONE $(date +%H:%M:%S)"
