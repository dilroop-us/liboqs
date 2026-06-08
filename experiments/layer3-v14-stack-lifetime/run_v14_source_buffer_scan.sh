#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"
RESULTS="$ROOT/layer3-results"
HOT="$ROOT/src/sig/ml_dsa/mldsa-native_ml-dsa-44_x86_64/mldsa/src"

mkdir -p "$RESULTS"

OUT="$RESULTS/v14_source_buffer_scan.txt"

{
  echo "Layer 3 v14 source buffer scan"
  echo
  echo "Files scanned:"
  echo "$HOT/sign.c"
  echo "$HOT/polyvec_lazy.h"
  echo "$HOT/polyvec_lazy.c"
  echo "$HOT/polyvec.h"
  echo "$HOT/polyvec.c"
  echo

  grep -RInE \
    "mld_polymat|mld_yvec|mld_polyvecl|mld_polyveck|mld_poly[[:space:]]+[A-Za-z_][A-Za-z0-9_]*|uint8_t[[:space:]]+[A-Za-z_][A-Za-z0-9_]*\\[|int32_t[[:space:]]+[A-Za-z_][A-Za-z0-9_]*\\[" \
    "$HOT/sign.c" \
    "$HOT/polyvec_lazy.h" \
    "$HOT/polyvec_lazy.c" \
    "$HOT/polyvec.h" \
    "$HOT/polyvec.c" \
    || true
} | tee "$OUT"

echo
echo "Wrote $OUT"
