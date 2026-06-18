#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"
OUT="$ROOT/experiments/layer3-v22b-verify-workspace"
RESULT="$ROOT/layer3-results/v22b_workspace_bytes.csv"

V22B="$ROOT/build-v22b-verify-workspace"
SRC="$OUT/v22b_workspace_bytes.c"

cc -O2 "$SRC" \
  -Wl,--whole-archive "$V22B/lib/liboqs.a" -Wl,--no-whole-archive \
  -o "$OUT/v22b_bytes" -pthread -lm

sign_bytes=$("$OUT/v22b_bytes" | awk -F, '/unified_sign_workspace_bytes/ {print $2}')
verify_bytes=$("$OUT/v22b_bytes" | awk -F, '/verify_workspace_bytes/ {print $2}')
total=$((sign_bytes + verify_bytes))

{
  echo "profile,workspace_kind,bytes"
  echo "verify_workspace,unified_sign_workspace,$sign_bytes"
  echo "verify_workspace,verify_workspace,$verify_bytes"
  echo "verify_workspace,total_sign_plus_verify_workspace,$total"
} | tee "$RESULT"
