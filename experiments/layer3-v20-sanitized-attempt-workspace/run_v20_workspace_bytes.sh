#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"
OUT="$ROOT/experiments/layer3-v20-sanitized-attempt-workspace"
RESULT="$ROOT/layer3-results/v20_workspace_bytes.csv"

V20="$ROOT/build-v20-sanitized-attempt-workspace"
SRC="$OUT/v20_workspace_bytes.c"

cc -O2 "$SRC" \
  -Wl,--whole-archive "$V20/lib/liboqs.a" -Wl,--no-whole-archive \
  -o "$OUT/v20_bytes" -pthread -lm

sign_bytes=$("$OUT/v20_bytes" | awk -F, '/caller_sign_workspace_bytes/ {print $2}')
attempt_bytes=$("$OUT/v20_bytes" | awk -F, '/caller_attempt_workspace_bytes/ {print $2}')
total=$((sign_bytes + attempt_bytes))

{
  echo "profile,workspace_kind,bytes"
  echo "sanitized_attempt_workspace,caller_sign_workspace,$sign_bytes"
  echo "sanitized_attempt_workspace,caller_attempt_workspace,$attempt_bytes"
  echo "sanitized_attempt_workspace,total_caller_workspace,$total"
} | tee "$RESULT"
