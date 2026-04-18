#!/usr/bin/env bash
# Runs post-render: review, retry low scorers, re-review, spot-check, final commit prep.
set -euo pipefail
cd /home/fank/repo/vanguard-galaxy

echo "=== 1. Initial review ==="
/home/fank/vgtts-env/bin/python tools/prerender/review.py 2>&1 | tail -5

echo
echo "=== 2. Retry lines scoring below 0.80 with 5 more seeds ==="
/home/fank/vgtts-env/bin/python tools/prerender/retry_lows.py --threshold 0.80 --extra-seeds 5 2>&1 | tail -30

echo
echo "=== 3. Second retry pass for anything still below 0.70 (deeper search) ==="
/home/fank/vgtts-env/bin/python tools/prerender/retry_lows.py --threshold 0.70 --extra-seeds 8 2>&1 | tail -30

echo
echo "=== 4. Final review ==="
/home/fank/vgtts-env/bin/python tools/prerender/review.py 2>&1 | tail -5

echo
echo "=== 5. Spot-check report ==="
/home/fank/vgtts-env/bin/python tools/prerender/spot_check.py 2>&1 | tail -5

echo
echo "=== 6. Stats summary ==="
python3 -c "
import json
m = json.load(open('prerender/echo/manifest.json'))
scores = [e.get('score_total') or e.get('score',{}).get('total') for e in m.values()]
scores = [s for s in scores if s is not None]
print(f'Total entries:   {len(m)}')
print(f'Scored entries:  {len(scores)}')
print(f'  Perfect 1.00:   {sum(1 for s in scores if s==1.00)}')
print(f'  Excellent 0.95: {sum(1 for s in scores if s>=0.95)}')
print(f'  Good 0.85:      {sum(1 for s in scores if s>=0.85)}')
print(f'  Mid 0.70-0.85:  {sum(1 for s in scores if 0.70<=s<0.85)}')
print(f'  Low <0.70:      {sum(1 for s in scores if s<0.70)}')
print(f'  avg {sum(scores)/len(scores):.3f}, min {min(scores):.2f}, max {max(scores):.2f}')"

echo
echo "=== Done — manifest ready for commit ==="
