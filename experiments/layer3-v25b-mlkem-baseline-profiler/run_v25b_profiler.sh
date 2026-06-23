#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"
EXP="$ROOT/experiments/layer3-v25b-mlkem-baseline-profiler"
RESULTS="$ROOT/layer3-results"

SRC="$EXP/v25b_mlkem_operation_profiler.c"

MLKEM_ONLY="$ROOT/build-v25b-mlkem-only-baseline"
COMBINED="$ROOT/build-v25b-combined-baseline"

mkdir -p "$RESULTS"

rm -f "$RESULTS/v25b_mlkem_correctness.csv"
rm -f "$RESULTS/v25b_mlkem_speed.csv"
rm -f "$RESULTS/v25b_mlkem_size.csv"

echo "profile,text,data,bss,dec,hex,binary" > "$RESULTS/v25b_mlkem_size.csv"

build_and_run() {
    local profile="$1"
    local build="$2"
    local bin="$RESULTS/v25b_${profile}_mlkem_profiler"

    echo
    echo "================ Building profiler: $profile ================"

    cc -O3 -Wall -Wextra \
      -I"$build/include" \
      "$SRC" \
      "$build/lib/liboqs.a" \
      -o "$bin" \
      -pthread -lm

    echo
    echo "Binary size for $profile:"
    size "$bin"

    read text data bss dec hex filename < <(size "$bin" | awk 'NR==2 {print $1, $2, $3, $4, $5, $6}')
    echo "$profile,$text,$data,$bss,$dec,$hex,$filename" >> "$RESULTS/v25b_mlkem_size.csv"

    echo
    echo "Correctness/smoke benchmark for $profile:"
    "$bin" "$profile" 1000 "$RESULTS/v25b_mlkem_correctness.csv"

    echo
    echo "Final speed benchmark for $profile:"
    "$bin" "$profile" 50000 "$RESULTS/v25b_mlkem_speed.csv"
}

build_and_run "mlkem_only" "$MLKEM_ONLY"
build_and_run "combined" "$COMBINED"

echo
echo "================ v25b correctness ================"
cat "$RESULTS/v25b_mlkem_correctness.csv"

echo
echo "================ v25b speed ================"
cat "$RESULTS/v25b_mlkem_speed.csv"

echo
echo "================ v25b size ================"
cat "$RESULTS/v25b_mlkem_size.csv"
