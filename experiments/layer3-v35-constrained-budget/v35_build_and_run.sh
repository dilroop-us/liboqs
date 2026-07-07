#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"

: "${V35_ITERATIONS:=100}"
: "${V35_FORCE_REBUILD:=0}"

: "${V35_LIB_BUDGET_BYTES:=8388608}"
: "${V35_BIN_BUDGET_BYTES:=16777216}"
: "${V35_RSS_BUDGET_KB:=131072}"
: "${V35_STACK_BUDGET_BYTES:=65536}"

cd "$ROOT"

echo "Running v35 constrained-device memory budget validation"
echo "Iterations:              $V35_ITERATIONS"
echo "Force rebuild:           $V35_FORCE_REBUILD"
echo "liboqs.a budget bytes:   $V35_LIB_BUDGET_BYTES"
echo "harness budget bytes:    $V35_BIN_BUDGET_BYTES"
echo "RSS budget kB:           $V35_RSS_BUDGET_KB"
echo "stack budget bytes:      $V35_STACK_BUDGET_BYTES"

V35_ITERATIONS="$V35_ITERATIONS" \
V35_FORCE_REBUILD="$V35_FORCE_REBUILD" \
V35_LIB_BUDGET_BYTES="$V35_LIB_BUDGET_BYTES" \
V35_BIN_BUDGET_BYTES="$V35_BIN_BUDGET_BYTES" \
V35_RSS_BUDGET_KB="$V35_RSS_BUDGET_KB" \
V35_STACK_BUDGET_BYTES="$V35_STACK_BUDGET_BYTES" \
python3 experiments/layer3-v35-constrained-budget/v35_constrained_budget_runner.py

python3 experiments/layer3-v35-constrained-budget/v35_report.py

echo
echo "Generated:"
ls -lh \
  layer3-results/v35_build.log \
  layer3-results/v35_lifecycle_symbols.txt \
  layer3-results/v35_constrained_budget_run.log \
  layer3-results/v35_time.log \
  layer3-results/v35_constrained_budget.csv \
  layer3-results/v35_size.csv \
  layer3-results/v35_stack_usage.csv \
  layer3-results/v35_constrained_budget_report.md \
  layer3-results/v35_constrained_budget_harness

echo
cat layer3-results/v35_constrained_budget_report.md
