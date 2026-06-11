#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"

cd "$ROOT"

echo "Running v17a lifetime map analysis..."
experiments/layer3-v17a-lifetime-map/v17a_lifetime_scan.py

echo
echo "Generated v17a result files:"
ls -lh layer3-results/v17a_*.md layer3-results/v17a_*.csv

echo
echo "Main signing lifetime map:"
cat layer3-results/v17a_x86_64_signature_internal_lifetime.md

echo
echo
echo "Reuse candidates:"
cat layer3-results/v17a_reuse_candidates.md
