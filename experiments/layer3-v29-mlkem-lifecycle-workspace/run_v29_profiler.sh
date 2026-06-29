#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"
BUILD="$ROOT/build-v29-mlkem-lifecycle-workspace"
EXP="$ROOT/experiments/layer3-v29-mlkem-lifecycle-workspace"
RESULTS="$ROOT/layer3-results"

SRC="$EXP/v29_mlkem_operation_profiler.c"
BIN="$RESULTS/v29_mlkem_lifecycle_workspace_profiler"

mkdir -p "$RESULTS"

rm -f "$RESULTS/v29_mlkem_correctness.csv"
rm -f "$RESULTS/v29_mlkem_speed.csv"
rm -f "$RESULTS/v29_mlkem_size.csv"
rm -f "$RESULTS/v29_mlkem_workspace.csv"

echo "profile,text,data,bss,dec,hex,binary" > "$RESULTS/v29_mlkem_size.csv"

echo "================ Building v29 profiler ================"

cc -O3 -Wall -Wextra \
  -I"$BUILD/include" \
  "$SRC" \
  -Wl,--whole-archive "$BUILD/lib/liboqs.a" -Wl,--no-whole-archive \
  -o "$BIN" \
  -pthread -lm

echo
echo "Binary size:"
size "$BIN"

read text data bss dec hex filename < <(size "$BIN" | awk 'NR==2 {print $1, $2, $3, $4, $5, $6}')
echo "v29_lifecycle_workspace,$text,$data,$bss,$dec,$hex,$filename" >> "$RESULTS/v29_mlkem_size.csv"

echo
echo "================ v29 correctness ================"
"$BIN" \
  v29_lifecycle_workspace \
  1000 \
  "$RESULTS/v29_mlkem_correctness.csv" \
  "$RESULTS/v29_mlkem_workspace.csv"

echo
echo "================ v29 speed ================"
"$BIN" \
  v29_lifecycle_workspace \
  50000 \
  "$RESULTS/v29_mlkem_speed.csv" \
  "$RESULTS/v29_mlkem_workspace.csv"

echo
echo "================ correctness ================"
cat "$RESULTS/v29_mlkem_correctness.csv"

echo
echo "================ speed ================"
cat "$RESULTS/v29_mlkem_speed.csv"

echo
echo "================ size ================"
cat "$RESULTS/v29_mlkem_size.csv"

echo
echo "================ workspace ================"
cat "$RESULTS/v29_mlkem_workspace.csv"
