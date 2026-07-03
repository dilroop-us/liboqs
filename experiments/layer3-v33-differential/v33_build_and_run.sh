#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/pqc/liboqs}"
EXP="$ROOT/experiments/layer3-v33-differential"
RESULTS="$ROOT/layer3-results"

mkdir -p "$RESULTS"

CSV="$RESULTS/v33_differential.csv"
REPORT="$RESULTS/v33_differential_report.md"
RUN_LOG="$RESULTS/v33_differential_run.log"
BUILD_LOG="$RESULTS/v33_build.log"

rm -f "$CSV" "$REPORT" "$RUN_LOG" "$BUILD_LOG"

ITERATIONS="${V33_ITERATIONS:-100}"

echo "Running v33 differential tests with ITERATIONS=$ITERATIONS"

V33_ITERATIONS="$ITERATIONS" "$EXP/v33_differential_runner.py"

"$EXP/v33_report.py"

echo
echo "Generated:"
ls -lh \
  "$CSV" \
  "$REPORT" \
  "$RUN_LOG" \
  "$BUILD_LOG" \
  "$RESULTS/v33_differential_baseline_harness" \
  "$RESULTS/v33_differential_optimized_harness" \
  "$RESULTS/v33_lifecycle_symbols.txt"

echo
cat "$REPORT"
