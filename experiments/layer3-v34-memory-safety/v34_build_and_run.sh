#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"

: "${V34_ASAN_ITERATIONS:=100}"
: "${V34_VALGRIND_ITERATIONS:=10}"

cd "$ROOT"

echo "Running v34 memory-safety validation"
echo "ASan/UBSan iterations: $V34_ASAN_ITERATIONS"
echo "Valgrind iterations:   $V34_VALGRIND_ITERATIONS"

V34_ASAN_ITERATIONS="$V34_ASAN_ITERATIONS" \
V34_VALGRIND_ITERATIONS="$V34_VALGRIND_ITERATIONS" \
python3 experiments/layer3-v34-memory-safety/v34_memory_safety_runner.py

python3 experiments/layer3-v34-memory-safety/v34_report.py

echo
echo "Generated:"
ls -lh \
  layer3-results/v34_build.log \
  layer3-results/v34_asan_ubsan_run.log \
  layer3-results/v34_valgrind_run.log \
  layer3-results/v34_lifecycle_symbols.txt \
  layer3-results/v34_memory_safety.csv \
  layer3-results/v34_memory_safety_report.md \
  layer3-results/v34_asan_ubsan_harness \
  layer3-results/v34_valgrind_harness

echo
cat layer3-results/v34_memory_safety_report.md
