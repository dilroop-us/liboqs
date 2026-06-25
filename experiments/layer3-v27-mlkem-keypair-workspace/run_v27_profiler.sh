#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"
BUILD="$ROOT/build-v27-mlkem-keypair-workspace"
EXP="$ROOT/experiments/layer3-v27-mlkem-keypair-workspace"
RESULTS="$ROOT/layer3-results"

SRC="$EXP/v27_mlkem_operation_profiler.c"
BIN="$RESULTS/v27_mlkem_keypair_workspace_profiler"

mkdir -p "$RESULTS"

rm -f "$RESULTS/v27_mlkem_correctness.csv"
rm -f "$RESULTS/v27_mlkem_speed.csv"
rm -f "$RESULTS/v27_mlkem_size.csv"
rm -f "$RESULTS/v27_mlkem_workspace.csv"

echo "profile,text,data,bss,dec,hex,binary" > "$RESULTS/v27_mlkem_size.csv"

echo "================ Building v27 profiler ================"

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
echo "v27_keypair_workspace,$text,$data,$bss,$dec,$hex,$filename" >> "$RESULTS/v27_mlkem_size.csv"

echo
echo "================ v27 correctness ================"
"$BIN" \
  v27_keypair_workspace \
  1000 \
  "$RESULTS/v27_mlkem_correctness.csv" \
  "$RESULTS/v27_mlkem_workspace.csv"

echo
echo "================ v27 speed ================"
"$BIN" \
  v27_keypair_workspace \
  50000 \
  "$RESULTS/v27_mlkem_speed.csv" \
  "$RESULTS/v27_mlkem_workspace.csv"

echo
echo "================ correctness ================"
cat "$RESULTS/v27_mlkem_correctness.csv"

echo
echo "================ speed ================"
cat "$RESULTS/v27_mlkem_speed.csv"

echo
echo "================ size ================"
cat "$RESULTS/v27_mlkem_size.csv"

echo
echo "================ workspace ================"
cat "$RESULTS/v27_mlkem_workspace.csv"
