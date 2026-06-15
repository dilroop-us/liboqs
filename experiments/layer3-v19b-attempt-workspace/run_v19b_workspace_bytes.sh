#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"
OUT="$ROOT/experiments/layer3-v19b-attempt-workspace"
RESULT="$ROOT/layer3-results/v19b_workspace_bytes.csv"

V19B="$ROOT/build-v19b-attempt-workspace"
SRC="$OUT/v19b_workspace_bytes.c"

cc -O2 "$SRC" \
  -Wl,--whole-archive "$V19B/lib/liboqs.a" -Wl,--no-whole-archive \
  -o "$OUT/v19b_bytes" -pthread -lm

sign_bytes=$("$OUT/v19b_bytes" | awk -F, '/caller_sign_workspace_bytes/ {print $2}')
attempt_bytes=$("$OUT/v19b_bytes" | awk -F, '/caller_attempt_workspace_bytes/ {print $2}')
total=$((sign_bytes + attempt_bytes))

{
  echo "profile,workspace_kind,bytes"
  echo "attempt_workspace,caller_sign_workspace,$sign_bytes"
  echo "attempt_workspace,caller_attempt_workspace,$attempt_bytes"
  echo "attempt_workspace,total_caller_workspace,$total"
} | tee "$RESULT"
