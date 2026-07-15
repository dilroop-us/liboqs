#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"
EXP="$ROOT/experiments/layer3-v41-rust-workspace-api"
BUILD="$ROOT/build-v41-rust-workspace-api"
RESULTS="$ROOT/layer3-results"

: "${V41_ITERATIONS:=100}"
: "${V41_FORCE_REBUILD:=0}"

EXPERIMENTAL_DEFINES=(
  -DMLK_CONFIG_EXPERIMENTAL_CALLER_ENC_WORKSPACE
  -DMLK_CONFIG_EXPERIMENTAL_CALLER_KEYPAIR_WORKSPACE
  -DMLK_CONFIG_EXPERIMENTAL_CALLER_DEC_WORKSPACE
  -DMLK_CONFIG_EXPERIMENTAL_COMPACT_LIFECYCLE_WORKSPACE
  -DMLD_CONFIG_EXPERIMENTAL_CALLER_SIGN_WORKSPACE
  -DMLD_CONFIG_EXPERIMENTAL_CALLER_ATTEMPT_WORKSPACE
  -DMLD_CONFIG_EXPERIMENTAL_UNIFIED_SIGN_WORKSPACE
  -DMLD_CONFIG_EXPERIMENTAL_CALLER_VERIFY_WORKSPACE
  -DMLD_CONFIG_EXPERIMENTAL_CALLER_KEYGEN_WORKSPACE
  -DMLD_CONFIG_EXPERIMENTAL_COMPACT_LIFECYCLE_WORKSPACE
)

cd "$ROOT"

mkdir -p "$RESULTS"

echo "Running v41 Rust workspace ownership and alignment API validation"
echo "Iterations:    $V41_ITERATIONS"
echo "Force rebuild: $V41_FORCE_REBUILD"

if [[ "$V41_FORCE_REBUILD" == "1" ]]; then
  rm -rf "$BUILD"
  rm -rf "$EXP/target"
fi

if [[ ! -f "$BUILD/lib/liboqs.a" ]]; then
  C_FLAGS="-O2 -g -fno-omit-frame-pointer ${EXPERIMENTAL_DEFINES[*]}"

  cmake \
    -S "$ROOT" \
    -B "$BUILD" \
    -DBUILD_SHARED_LIBS=OFF \
    "-DOQS_MINIMAL_BUILD=KEM_ml_kem_768;SIG_ml_dsa_44" \
    -DOQS_USE_OPENSSL=OFF \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    "-DCMAKE_C_FLAGS=$C_FLAGS"

  cmake --build "$BUILD" -j"$(nproc)"
else
  echo "v41 optimized liboqs build already exists:"
  echo "$BUILD/lib/liboqs.a"
fi

echo
echo "Lifecycle workspace symbols:"

nm -g --defined-only "$BUILD/lib/liboqs.a" 2>/dev/null \
  | grep -E \
    "MLKEM768.*v29_lifecycle_workspace_(bytes|set)|MLDSA44.*v24_lifecycle_workspace_(bytes|set)" \
  | tee "$RESULTS/v41_lifecycle_symbols.txt"

echo
echo "Formatting Rust project"

(
  cd "$EXP"
  cargo fmt --all
)

echo
echo "Running Rust workspace API harness"

(
  cd "$EXP"

  LIBOQS_V41_BUILD="$BUILD" \
  V41_ITERATIONS="$V41_ITERATIONS" \
  cargo run --release --quiet
) | tee "$RESULTS/v41_rust_workspace_api_run.log"

python3 "$EXP/v41_report.py"

echo
echo "Generated artifacts:"

ls -lh \
  "$RESULTS/v41_lifecycle_symbols.txt" \
  "$RESULTS/v41_rust_workspace_api_run.log" \
  "$RESULTS/v41_rust_workspace_api.csv" \
  "$RESULTS/v41_rust_workspace_api_report.md"

echo
cat "$RESULTS/v41_rust_workspace_api_report.md"
