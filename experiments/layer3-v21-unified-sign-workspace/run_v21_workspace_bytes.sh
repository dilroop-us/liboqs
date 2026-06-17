#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"
OUT="$ROOT/experiments/layer3-v21-unified-sign-workspace"
RESULT="$ROOT/layer3-results/v21_workspace_bytes.csv"

V21="$ROOT/build-v21-unified-sign-workspace"
SRC="$OUT/v21_workspace_bytes.c"

cc -O2 "$SRC" \
  -Wl,--whole-archive "$V21/lib/liboqs.a" -Wl,--no-whole-archive \
  -o "$OUT/v21_bytes" -pthread -lm

sign_bytes=$("$OUT/v21_bytes" | awk -F, '/caller_sign_workspace_bytes/ {print $2}')
attempt_bytes=$("$OUT/v21_bytes" | awk -F, '/caller_attempt_workspace_bytes/ {print $2}')
unified_bytes=$("$OUT/v21_bytes" | awk -F, '/unified_sign_workspace_bytes/ {print $2}')

{
  echo "profile,workspace_kind,bytes"
  echo "unified_sign_workspace,caller_sign_workspace,$sign_bytes"
  echo "unified_sign_workspace,caller_attempt_workspace,$attempt_bytes"
  echo "unified_sign_workspace,unified_sign_workspace,$unified_bytes"
} | tee "$RESULT"
