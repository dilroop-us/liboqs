#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"

: "${V38_SAMPLES:=2000}"
: "${V38_WARMUP:=100}"
: "${V38_THRESHOLD:=4.5}"
: "${V38_BATCH:=1}"
: "${V38_FORCE_REBUILD:=0}"

cd "$ROOT"

echo "Running v38 timing / constant-time-style leakage validation"
echo "Samples:        $V38_SAMPLES"
echo "Warmup:         $V38_WARMUP"
echo "Threshold:      $V38_THRESHOLD"
echo "Batch:          $V38_BATCH"
echo "Force rebuild:  $V38_FORCE_REBUILD"

V38_SAMPLES="$V38_SAMPLES" \
V38_WARMUP="$V38_WARMUP" \
V38_THRESHOLD="$V38_THRESHOLD" \
V38_BATCH="$V38_BATCH" \
V38_FORCE_REBUILD="$V38_FORCE_REBUILD" \
python3 experiments/layer3-v38-timing-leakage/v38_timing_leakage_runner.py

python3 experiments/layer3-v38-timing-leakage/v38_report.py

echo
echo "Generated:"
ls -lh \
  layer3-results/v38_build.log \
  layer3-results/v38_lifecycle_symbols.txt \
  layer3-results/v38_timing_leakage_run.log \
  layer3-results/v38_timing_leakage.csv \
  layer3-results/v38_timing_leakage_report.md \
  layer3-results/v38_timing_leakage_harness

echo
cat layer3-results/v38_timing_leakage_report.md
