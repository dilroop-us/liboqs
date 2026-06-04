#!/usr/bin/env bash
set -euo pipefail

OUT="$HOME/pqc/liboqs/layer3-results"
DIR="$HOME/pqc/liboqs/experiments/layer3-v10-reduced-ram"

BASE_BIN="$DIR/v10_baseline_profiler"
REDUCE_BIN="$DIR/v10_reduce_ram_profiler"

mkdir -p "$OUT"

MODES=(
  sig-sign
  sig-verify
)

SPEED_SUMMARY="$OUT/v10_sign_verify_speed_summary.csv"
MEM_SUMMARY="$OUT/v10_sign_verify_memory_summary.csv"

echo "profile,mode,mean_us" > "$SPEED_SUMMARY"
echo "profile,mode,peak_heap_bytes,peak_stack_bytes,peak_total_bytes" > "$MEM_SUMMARY"

run_profile() {
  local profile="$1"
  local bin="$2"

  for mode in "${MODES[@]}"
  do
    echo
    echo "===== SPEED: $profile / $mode ====="

    speed_output="$("$bin" "$mode" 50000)"
    echo "$speed_output" | tee "$OUT/v10_${profile}_${mode}_speed.txt"

    mean_us="$(
      echo "$speed_output" \
        | awk -F': ' '/mean_us:/ { print $2 }'
    )"

    echo "$profile,$mode,$mean_us" >> "$SPEED_SUMMARY"

    echo
    echo "===== MASSIF: $profile / $mode ====="

    raw="$OUT/v10_${profile}_${mode}_stack.raw"
    txt="$OUT/v10_${profile}_${mode}_stack.txt"

    valgrind --tool=massif --stacks=yes \
      --massif-out-file="$raw" \
      "$bin" "$mode" 1000

    ms_print "$raw" > "$txt"

    peak_heap="$(
      grep "mem_heap_B" "$raw" \
        | sed 's/mem_heap_B=//' \
        | sort -n \
        | tail -1
    )"

    peak_stack="$(
      grep "mem_stacks_B" "$raw" \
        | sed 's/mem_stacks_B=//' \
        | sort -n \
        | tail -1
    )"

    peak_total="$(
      awk -F= '
        /mem_heap_B=/ { heap=$2 }
        /mem_heap_extra_B=/ { extra=$2 }
        /mem_stacks_B=/ {
          stack=$2
          total=heap+extra+stack
          if (total > max) max=total
        }
        END { print max }
      ' "$raw"
    )"

    echo "$profile,$mode,$peak_heap,$peak_stack,$peak_total" >> "$MEM_SUMMARY"
  done
}

run_profile "baseline" "$BASE_BIN"
run_profile "reduce_ram" "$REDUCE_BIN"

echo
echo "v10 sign/verify speed summary:"
cat "$SPEED_SUMMARY"

echo
echo "v10 sign/verify memory summary:"
cat "$MEM_SUMMARY"
