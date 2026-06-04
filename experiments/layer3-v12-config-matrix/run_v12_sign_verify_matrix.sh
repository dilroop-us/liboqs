#!/usr/bin/env bash
set -euo pipefail

OUT="$HOME/pqc/liboqs/layer3-results"
DIR="$HOME/pqc/liboqs/experiments/layer3-v12-config-matrix"

mkdir -p "$OUT"

declare -A BINS
BINS[baseline]="$DIR/v12_baseline_profiler"
BINS[reduce_ram]="$DIR/v12_reduce_ram_profiler"
BINS[serial_fips202]="$DIR/v12_serial_fips202_profiler"
BINS[reduce_ram_serial_fips202]="$DIR/v12_reduce_ram_serial_fips202_profiler"

PROFILES=(
  baseline
  reduce_ram
  serial_fips202
  reduce_ram_serial_fips202
)

MODES=(
  sig-sign
  sig-verify
)

SPEED_SUMMARY="$OUT/v12_sign_verify_speed_summary.csv"
MEM_SUMMARY="$OUT/v12_sign_verify_memory_summary.csv"

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
    echo "$speed_output" | tee "$OUT/v12_${profile}_${mode}_speed.txt"

    mean_us="$(
      echo "$speed_output" \
        | awk -F': ' '/mean_us:/ { print $2 }'
    )"

    echo "$profile,$mode,$mean_us" >> "$SPEED_SUMMARY"

    echo
    echo "===== MASSIF: $profile / $mode ====="

    raw="$OUT/v12_${profile}_${mode}_stack.raw"
    txt="$OUT/v12_${profile}_${mode}_stack.txt"

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
echo "v12 sign/verify speed summary:"
cat "$SPEED_SUMMARY"

echo
echo "v12 sign/verify memory summary:"
cat "$MEM_SUMMARY"
