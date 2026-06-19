#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"
OUT="$ROOT/experiments/layer3-v23b-keygen-workspace"
RESULT="$ROOT/layer3-results/v23b_workspace_bytes.csv"

V23B="$ROOT/build-v23b-keygen-workspace"
SRC="$OUT/v23b_workspace_bytes.c"

cc -O2 "$SRC" \
  -Wl,--whole-archive "$V23B/lib/liboqs.a" -Wl,--no-whole-archive \
  -o "$OUT/v23b_bytes" -pthread -lm

sign_bytes=$("$OUT/v23b_bytes" | awk -F, '/unified_sign_workspace_bytes/ {print $2}')
verify_bytes=$("$OUT/v23b_bytes" | awk -F, '/verify_workspace_bytes/ {print $2}')
keygen_bytes=$("$OUT/v23b_bytes" | awk -F, '/keygen_workspace_bytes/ {print $2}')

total=$((sign_bytes + verify_bytes + keygen_bytes))

{
  echo "profile,workspace_kind,bytes"
  echo "keygen_workspace,unified_sign_workspace,$sign_bytes"
  echo "keygen_workspace,verify_workspace,$verify_bytes"
  echo "keygen_workspace,keygen_workspace,$keygen_bytes"
  echo "keygen_workspace,total_sign_verify_keygen_workspace,$total"
} | tee "$RESULT"
