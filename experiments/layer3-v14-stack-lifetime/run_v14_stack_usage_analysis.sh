#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"
EXP="$ROOT/experiments/layer3-v14-stack-lifetime"
RESULTS="$ROOT/layer3-results"

mkdir -p "$RESULTS"

for profile in baseline reduce_ram lazy_polyvec
do
  build_dir="$ROOT/build-v14-stack-$profile"

  echo
  echo "===== Analyzing stack usage: $profile ====="

  "$EXP/v14_stack_usage_analyzer.py" \
    "$build_dir" \
    "$profile" \
    "$RESULTS"

  echo
  echo "Top functions for $profile:"
  sed -n '1,25p' "$RESULTS/v14_${profile}_top_stack_usage.md"
done

echo
echo "Generated files:"
ls -lh "$RESULTS"/v14_*_stack_usage.csv "$RESULTS"/v14_*_top_stack_usage.md
