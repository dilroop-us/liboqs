#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"

: "${V36_THREADS:=8}"
: "${V36_ITERATIONS_PER_THREAD:=100}"
: "${V36_FORCE_REBUILD:=0}"

cd "$ROOT"

echo "Running v36 threading/TLS workspace validation"
echo "Threads:                 $V36_THREADS"
echo "Iterations per thread:   $V36_ITERATIONS_PER_THREAD"
echo "Force rebuild:           $V36_FORCE_REBUILD"

V36_THREADS="$V36_THREADS" \
V36_ITERATIONS_PER_THREAD="$V36_ITERATIONS_PER_THREAD" \
V36_FORCE_REBUILD="$V36_FORCE_REBUILD" \
python3 experiments/layer3-v36-threading-tls/v36_threading_tls_runner.py

python3 experiments/layer3-v36-threading-tls/v36_report.py

echo
echo "Generated:"
ls -lh \
  layer3-results/v36_build.log \
  layer3-results/v36_lifecycle_symbols.txt \
  layer3-results/v36_threading_tls_run.log \
  layer3-results/v36_threading_tls.csv \
  layer3-results/v36_threading_tls_report.md \
  layer3-results/v36_threading_tls_harness

echo
cat layer3-results/v36_threading_tls_report.md
