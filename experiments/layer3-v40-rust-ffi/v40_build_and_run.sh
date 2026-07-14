#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"
EXP="$ROOT/experiments/layer3-v40-rust-ffi"
BUILD="$ROOT/build-v40-rust-ffi"
RESULTS="$ROOT/layer3-results"

: "${V40_ITERATIONS:=100}"
: "${V40_FORCE_REBUILD:=0}"

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

echo "Running v40 Rust FFI / integration validation"
echo "Iterations:     $V40_ITERATIONS"
echo "Force rebuild:  $V40_FORCE_REBUILD"

if [[ "$V40_FORCE_REBUILD" == "1" ]]; then
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
  echo "v40 optimized liboqs build already exists: $BUILD/lib/liboqs.a"
fi

echo
echo "Lifecycle workspace symbols:"
nm -g --defined-only "$BUILD/lib/liboqs.a" \
  | grep -E "MLKEM768.*v29_lifecycle_workspace_(bytes|set)|MLDSA44.*v24_lifecycle_workspace_(bytes|set)" \
  | tee "$RESULTS/v40_lifecycle_symbols.txt"

echo
echo "Running Rust harness"

(
  cd "$EXP"
  LIBOQS_V40_BUILD="$BUILD" \
  V40_ITERATIONS="$V40_ITERATIONS" \
  cargo run --release --quiet
) | tee "$RESULTS/v40_rust_ffi_run.log"

python3 "$EXP/v40_report.py"

echo
echo "Generated:"
ls -lh \
  "$RESULTS/v40_lifecycle_symbols.txt" \
  "$RESULTS/v40_rust_ffi_run.log" \
  "$RESULTS/v40_rust_ffi.csv" \
  "$RESULTS/v40_rust_ffi_report.md"

echo
cat "$RESULTS/v40_rust_ffi_report.md"
