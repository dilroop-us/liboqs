#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/pqc/liboqs}"
EXP="$ROOT/experiments/layer3-v32-workspace-misuse"
RESULTS="$ROOT/layer3-results"

BUILD_DIR="${BUILD_DIR:-$ROOT/build-v29-mlkem-lifecycle-workspace}"

LIBOQS_A=""

if [ -f "$BUILD_DIR/lib/liboqs.a" ]; then
  LIBOQS_A="$BUILD_DIR/lib/liboqs.a"
elif [ -f "$BUILD_DIR/liboqs.a" ]; then
  LIBOQS_A="$BUILD_DIR/liboqs.a"
else
  echo "ERROR: liboqs.a not found in $BUILD_DIR"
  echo "Rebuild final optimized build first, or set BUILD_DIR=/path/to/build"
  exit 1
fi

INCLUDE_ARGS=()

if [ -d "$BUILD_DIR/include" ]; then
  INCLUDE_ARGS+=("-I" "$BUILD_DIR/include")
fi

INCLUDE_ARGS+=("-I" "$ROOT/include")
INCLUDE_ARGS+=("-I" "$EXP")

mkdir -p "$RESULTS"

GEN_H="$EXP/v32_workspace_setup.generated.h"
BIN="$RESULTS/v32_workspace_misuse_harness"
CSV="$RESULTS/v32_workspace_misuse.csv"
RUN_LOG="$RESULTS/v32_workspace_misuse_run.log"
BUILD_LOG="$RESULTS/v32_build.log"
REPORT="$RESULTS/v32_workspace_misuse_report.md"
SYMS_FILE="$RESULTS/v32_lifecycle_symbols.txt"

nm -g --defined-only "$LIBOQS_A" \
  | awk '$2 ~ /^[A-Za-z]$/ {print $3}' \
  | sort -u > "$SYMS_FILE"

collect_pairs() {
  local pattern="$1"
  local bytes_symbols
  bytes_symbols="$(grep -E "$pattern" "$SYMS_FILE" | grep '_bytes$' || true)"

  local pairs=""
  local b
  for b in $bytes_symbols; do
    local s="${b%_bytes}_set"
    if grep -qx "$s" "$SYMS_FILE"; then
      pairs="$pairs $b:$s"
    fi
  done

  echo "$pairs"
}

MLKEM_PAIRS="$(collect_pairs '(MLKEM|ML_KEM).*768.*v29.*lifecycle.*workspace.*_bytes$')"
MLDSA_PAIRS="$(collect_pairs '(MLDSA|ML_DSA|MLD).*44.*v24b?.*lifecycle.*workspace.*_bytes$')"

if [ -z "$MLKEM_PAIRS" ]; then
  echo "ERROR: No ML-KEM v29 lifecycle workspace byte/set symbol pairs found."
  grep -E '(MLKEM|ML_KEM).*v29|lifecycle' "$SYMS_FILE" | head -100 || true
  exit 1
fi

if [ -z "$MLDSA_PAIRS" ]; then
  echo "ERROR: No ML-DSA v24 lifecycle workspace byte/set symbol pairs found."
  grep -E '(MLDSA|ML_DSA|MLD).*v24|lifecycle' "$SYMS_FILE" | head -100 || true
  exit 1
fi

{
  echo "#ifndef V32_WORKSPACE_SETUP_GENERATED_H"
  echo "#define V32_WORKSPACE_SETUP_GENERATED_H"
  echo
  echo "#include <stddef.h>"
  echo

  for pair in $MLKEM_PAIRS $MLDSA_PAIRS; do
    b="${pair%%:*}"
    s="${pair##*:}"
    echo "extern size_t $b(void);"
    echo "extern void $s(void *);"
  done

  echo
  echo "static size_t v32_mlkem_workspace_need(void) {"
  echo "    size_t need = 0;"
  echo "    size_t n = 0;"
  for pair in $MLKEM_PAIRS; do
    b="${pair%%:*}"
    echo "    n = $b();"
    echo "    if (n > need) { need = n; }"
  done
  echo "    return need;"
  echo "}"
  echo

  echo "static int v32_mlkem_workspace_set(void *workspace, size_t cap) {"
  echo "    size_t need = v32_mlkem_workspace_need();"
  echo "    if (workspace == 0 || cap < need) { return -1; }"
  for pair in $MLKEM_PAIRS; do
    s="${pair##*:}"
    echo "    $s(workspace);"
  done
  echo "    return 0;"
  echo "}"
  echo

  echo "static void v32_mlkem_raw_set(void *workspace) {"
  for pair in $MLKEM_PAIRS; do
    s="${pair##*:}"
    echo "    $s(workspace);"
  done
  echo "}"
  echo

  echo "static size_t v32_mldsa_workspace_need(void) {"
  echo "    size_t need = 0;"
  echo "    size_t n = 0;"
  for pair in $MLDSA_PAIRS; do
    b="${pair%%:*}"
    echo "    n = $b();"
    echo "    if (n > need) { need = n; }"
  done
  echo "    return need;"
  echo "}"
  echo

  echo "static int v32_mldsa_workspace_set(void *workspace, size_t cap) {"
  echo "    size_t need = v32_mldsa_workspace_need();"
  echo "    if (workspace == 0 || cap < need) { return -1; }"
  for pair in $MLDSA_PAIRS; do
    s="${pair##*:}"
    echo "    $s(workspace);"
  done
  echo "    return 0;"
  echo "}"
  echo

  echo "static void v32_mldsa_raw_set(void *workspace) {"
  for pair in $MLDSA_PAIRS; do
    s="${pair##*:}"
    echo "    $s(workspace);"
  done
  echo "}"
  echo

  echo "#endif"
} > "$GEN_H"

{
  echo "ROOT=$ROOT"
  echo "BUILD_DIR=$BUILD_DIR"
  echo "LIBOQS_A=$LIBOQS_A"
  echo
  echo "MLKEM_PAIRS=$MLKEM_PAIRS"
  echo "MLDSA_PAIRS=$MLDSA_PAIRS"
  echo
  echo "Compiling v32 harness..."
} | tee "$BUILD_LOG"

cc \
  -std=c11 \
  -O2 \
  -Wall \
  -Wextra \
  "${INCLUDE_ARGS[@]}" \
  "$EXP/v32_workspace_misuse.c" \
  "$LIBOQS_A" \
  -o "$BIN" \
  -pthread \
  -lm \
  -ldl \
  2>&1 | tee -a "$BUILD_LOG"

ITERATIONS="${V32_ITERATIONS:-100}"

echo "Running v32 harness with ITERATIONS=$ITERATIONS" | tee "$RUN_LOG"

"$BIN" "$CSV" "$ITERATIONS" 2>&1 | tee -a "$RUN_LOG"

echo
echo "Generated:"
ls -lh "$BIN" "$CSV" "$RUN_LOG" "$BUILD_LOG" "$SYMS_FILE"

if [ -x "$EXP/v32_report.py" ]; then
  "$EXP/v32_report.py"
  echo
  cat "$REPORT"
fi
