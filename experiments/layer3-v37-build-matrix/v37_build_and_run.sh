#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"

: "${V37_ITERATIONS:=20}"
: "${V37_FORCE_REBUILD:=0}"

cd "$ROOT"

echo "Running v37 build matrix validation"
echo "Iterations per component: $V37_ITERATIONS"
echo "Force rebuild:            $V37_FORCE_REBUILD"

V37_ITERATIONS="$V37_ITERATIONS" \
V37_FORCE_REBUILD="$V37_FORCE_REBUILD" \
python3 experiments/layer3-v37-build-matrix/v37_build_matrix_runner.py

echo
echo "Generated:"
ls -lh \
  layer3-results/v37_build_matrix.csv \
  layer3-results/v37_build_matrix_report.md

echo
echo "Build logs:"
ls -lh layer3-results/v37-build-logs

echo
cat layer3-results/v37_build_matrix_report.md
