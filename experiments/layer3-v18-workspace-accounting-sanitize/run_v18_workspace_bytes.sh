#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"
OUT="$ROOT/experiments/layer3-v18-workspace-accounting-sanitize"
RESULT="$ROOT/layer3-results/v18_workspace_bytes.csv"

V16="$ROOT/build-v16-caller-matrix-workspace"
V17B="$ROOT/build-v17b-full-sign-workspace"
V18="$ROOT/build-v18-workspace-accounting-sanitize"

SRC="$OUT/v18_workspace_bytes.c"

echo "profile,workspace_kind,bytes" > "$RESULT"
echo "baseline,none,0" >> "$RESULT"
echo "reduce_ram,none,0" >> "$RESULT"
echo "static_matrix,hidden_bss_workspace,0" >> "$RESULT"

cc -O2 "$SRC" \
  -Wl,--whole-archive "$V16/lib/liboqs.a" -Wl,--no-whole-archive \
  -o "$OUT/v18_bytes_v16" -pthread -lm

v16_bytes=$("$OUT/v18_bytes_v16" | awk -F, '/caller_matrix_workspace_bytes/ {print $2}')
echo "caller_matrix,caller_matrix_workspace,$v16_bytes" >> "$RESULT"

cc -O2 "$SRC" \
  -Wl,--whole-archive "$V17B/lib/liboqs.a" -Wl,--no-whole-archive \
  -o "$OUT/v18_bytes_v17b" -pthread -lm

v17b_bytes=$("$OUT/v18_bytes_v17b" | awk -F, '/caller_sign_workspace_bytes/ {print $2}')
echo "full_sign,caller_sign_workspace,$v17b_bytes" >> "$RESULT"

cc -O2 "$SRC" \
  -Wl,--whole-archive "$V18/lib/liboqs.a" -Wl,--no-whole-archive \
  -o "$OUT/v18_bytes_v18" -pthread -lm

v18_bytes=$("$OUT/v18_bytes_v18" | awk -F, '/caller_sign_workspace_bytes/ {print $2}')
echo "workspace_sanitize,caller_sign_workspace,$v18_bytes" >> "$RESULT"

cat "$RESULT"
