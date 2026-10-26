#!/bin/bash
# 16:9 cuts of the six life episodes, one after another (2-core box), committing+pushing
# each finished episode so a sandbox reset can never eat the work.
cd /home/user/masar-online || exit 1
export AR=16:9
PY=/home/user/.venv/bin/python
for e in ${EPS:-e1 e2 e3 e4 e5 e6}; do
  echo "@@START $e $(date +%H:%M:%S)"
  $PY media/episode.py media/series/$e/$e.json > /tmp/land3_$e.log 2>&1
  if [ $? -eq 0 ]; then
    $PY media/recap_frame.py "$e" >> /tmp/land3_$e.log 2>&1 || true
    for k in 1 2 3 4 5; do
      git add -A media && git commit -q -m "$e: 16:9 cut (life episode, landscape)" && break || sleep 12
    done
    git push -q origin arena/489e96d8-masar-online || echo "@@PUSH-FAIL $e"
    tail -3 /tmp/land3_$e.log
    echo "@@PUSHED $e $(date +%H:%M:%S)"
  else
    echo "@@FAILED $e"; tail -12 /tmp/land3_$e.log
  fi
done
echo "@@ALL-DONE $(date +%H:%M:%S)"
