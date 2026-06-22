#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"
V23B="$ROOT/build-v23b-keygen-workspace"
OUT="$ROOT/experiments/layer3-v24a-compact-workspace-layout"
RESULT="$ROOT/layer3-results/v24a_current_workspace_symbols.csv"

if [ ! -f "$V23B/lib/liboqs.a" ]; then
  echo "missing v23b build: $V23B/lib/liboqs.a"
  echo "run v23b build first: experiments/layer3-v23b-keygen-workspace/run_v23b_build.sh"
  exit 1
fi

cc -O2 "$OUT/v24a_current_workspace_symbols.c" \
  -Wl,--whole-archive "$V23B/lib/liboqs.a" -Wl,--no-whole-archive \
  -o "$OUT/v24a_current_workspace_symbols" \
  -pthread -lm

{
  echo "workspace_kind,bytes"
  "$OUT/v24a_current_workspace_symbols"
} | tee "$RESULT"
