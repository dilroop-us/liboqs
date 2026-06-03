#!/usr/bin/env bash
set -euo pipefail

OUT="$HOME/pqc/liboqs/layer3-results"
BIN="$HOME/pqc/liboqs/experiments/layer3-v8-operation-profiler/v8_operation_profiler"

mkdir -p "$OUT"

MODES=(
  kem-keygen
  kem-encaps
  kem-decaps
  sig-keypair
  sig-sign
  sig-verify
)

SUMMARY="$OUT/v8_operation_memory_summary.csv"

echo "mode,peak_heap_bytes,peak_stack_bytes,peak_total_bytes" > "$SUMMARY"

for mode in "${MODES[@]}"
do
  echo "Running Massif for $mode"

  RAW="$OUT/v8_${mode}_stack.raw"
  TXT="$OUT/v8_${mode}_stack.txt"

  valgrind --tool=massif --stacks=yes \
    --massif-out-file="$RAW" \
    "$BIN" "$mode" 1000

  ms_print "$RAW" > "$TXT"

  peak_heap=$(
    grep "mem_heap_B" "$RAW" \
      | sed 's/mem_heap_B=//' \
      | sort -n \
      | tail -1
  )

  peak_stack=$(
    grep "mem_stacks_B" "$RAW" \
      | sed 's/mem_stacks_B=//' \
      | sort -n \
      | tail -1
  )

  peak_total=$(
    awk -F= '
      /mem_heap_B=/ { heap=$2 }
      /mem_heap_extra_B=/ { extra=$2 }
      /mem_stacks_B=/ {
        stack=$2
        total=heap+extra+stack
        if (total > max) max=total
      }
      END { print max }
    ' "$RAW"
  )

  echo "$mode,$peak_heap,$peak_stack,$peak_total" >> "$SUMMARY"
done

echo
echo "v8 operation-specific memory summary:"
cat "$SUMMARY"
