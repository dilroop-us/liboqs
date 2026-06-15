#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"

cd "$ROOT"

echo "Running v19a attempt-generation lifetime analysis..."

rm -f layer3-results/v19a_*.csv layer3-results/v19a_*.md

experiments/layer3-v19a-attempt-lifetime-map/v19a_attempt_lifetime_scan.py

echo
echo "Generated v19a result files:"
ls -lh layer3-results/v19a_*.md layer3-results/v19a_*.csv

echo
echo "Main x86_64 attempt-generation lifetime map:"
cat layer3-results/v19a_x86_64_attempt_generation_lifetime.md

echo
echo
echo "Reuse candidates:"
cat layer3-results/v19a_attempt_reuse_candidates.md

echo
echo
echo "Unknown types:"
cat layer3-results/v19a_unknown_types.md

echo
echo
echo "Summary:"
cat layer3-results/v19a_attempt_summary.md
