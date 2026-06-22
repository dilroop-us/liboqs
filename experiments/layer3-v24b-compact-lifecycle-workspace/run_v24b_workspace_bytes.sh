#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"
OUT="$ROOT/experiments/layer3-v24b-compact-lifecycle-workspace"
RESULT="$ROOT/layer3-results/v24b_workspace_bytes.csv"

V24B="$ROOT/build-v24b-compact-lifecycle-workspace"
SRC="$OUT/v24b_workspace_bytes.c"

cc -O2 "$SRC" \
  -Wl,--whole-archive "$V24B/lib/liboqs.a" -Wl,--no-whole-archive \
  -o "$OUT/v24b_bytes" -pthread -lm

{
  echo "profile,workspace_kind,bytes"
  "$OUT/v24b_bytes" | while IFS=, read -r kind bytes
  do
    echo "compact_lifecycle_workspace,$kind,$bytes"
  done
} | tee "$RESULT"
