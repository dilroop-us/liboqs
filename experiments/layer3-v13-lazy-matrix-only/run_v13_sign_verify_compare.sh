#!/usr/bin/env bash
set -euo pipefail

RESULTS="$HOME/pqc/liboqs/layer3-results"
DIR="$HOME/pqc/liboqs/experiments/layer3-v13-lazy-matrix-only"

mkdir -p "$RESULTS"

declare -A BINS
BINS[baseline]="$DIR/v13_baseline_profiler"
BINS[reduce_ram]="$DIR/v13_reduce_ram_profiler"
BINS[lazy_polyvec]="$DIR/v13_lazy_polyvec_profiler"

PROFILES=(
  baseline
  reduce_ram
  lazy_polyvec
)

MODES=(
  sig-sign
  sig-verify
)

SPEED_SUMMARY="$RESULTS/v13_sign_verify_speed_summary.csv"
MEM_SUMMARY="$RESULTS/v13_sign_verify_memory_summary.csv"

echo "profile,mode,mean_us" > "$SPEED_SUMMARY"
echo "profile,mode,peak_heap_bytes,peak_stack_bytes,peak_total_bytes" > "$MEM_SUMMARY"

for profile in "${PROFILES[@]}"
do
  bin="${BINS[$profile]}"

  for mode in "${MODES[@]}"
  do
    echo
    echo "===== SPEED: $profile / $mode ====="

    speed_output="$("$bin" "$mode" 50000)"
    echo "$speed_output" | tee "$RESULTS/v13_${profile}_${mode}_speed.txt"

    mean_us="$(
      echo "$speed_output" \
        | awk -F': ' '/mean_us:/ { print $2 }'
    )"

    echo "$profile,$mode,$mean_us" >> "$SPEED_SUMMARY"

    echo
    echo "===== MASSIF: $profile / $mode ====="

    raw="$RESULTS/v13_${profile}_${mode}_stack.raw"
    txt="$RESULTS/v13_${profile}_${mode}_stack.txt"

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
done

echo
echo "v13 sign/verify speed summary:"
cat "$SPEED_SUMMARY"

echo
echo "v13 sign/verify memory summary:"
cat "$MEM_SUMMARY"
