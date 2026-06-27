#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"
BUILD="$ROOT/build-v28-mlkem-dec-workspace"
EXP="$ROOT/experiments/layer3-v28-mlkem-dec-workspace"
RESULTS="$ROOT/layer3-results"

SRC="$EXP/v28_mlkem_operation_profiler.c"
BIN="$RESULTS/v28_mlkem_dec_workspace_profiler"

mkdir -p "$RESULTS"

rm -f "$RESULTS/v28_mlkem_correctness.csv"
rm -f "$RESULTS/v28_mlkem_speed.csv"
rm -f "$RESULTS/v28_mlkem_size.csv"
rm -f "$RESULTS/v28_mlkem_workspace.csv"

echo "profile,text,data,bss,dec,hex,binary" > "$RESULTS/v28_mlkem_size.csv"

echo "================ Building v28 profiler ================"

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
echo "v28_dec_workspace,$text,$data,$bss,$dec,$hex,$filename" >> "$RESULTS/v28_mlkem_size.csv"

echo
echo "================ v28 correctness ================"
"$BIN" \
  v28_dec_workspace \
  1000 \
  "$RESULTS/v28_mlkem_correctness.csv" \
  "$RESULTS/v28_mlkem_workspace.csv"

echo
echo "================ v28 speed ================"
"$BIN" \
  v28_dec_workspace \
  50000 \
  "$RESULTS/v28_mlkem_speed.csv" \
  "$RESULTS/v28_mlkem_workspace.csv"

echo
echo "================ correctness ================"
cat "$RESULTS/v28_mlkem_correctness.csv"

echo
echo "================ speed ================"
cat "$RESULTS/v28_mlkem_speed.csv"

echo
echo "================ size ================"
cat "$RESULTS/v28_mlkem_size.csv"

echo
echo "================ workspace ================"
cat "$RESULTS/v28_mlkem_workspace.csv"
