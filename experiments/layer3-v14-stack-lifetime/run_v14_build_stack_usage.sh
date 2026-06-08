#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"

build_variant() {
  profile="$1"
  flags="$2"
  build_dir="$ROOT/build-v14-stack-$profile"

  echo
  echo "===== Building v14 stack-usage profile: $profile ====="

  rm -rf "$build_dir"

  cmake -GNinja \
    -S "$ROOT" \
    -B "$build_dir" \
    -DOQS_MINIMAL_BUILD="KEM_ml_kem_768;SIG_ml_dsa_44" \
    -DOQS_EMBEDDED_BUILD=ON \
    -DOQS_USE_OPENSSL=OFF \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DCMAKE_C_FLAGS="$flags -fstack-usage -Wframe-larger-than=4096"

  ninja -C "$build_dir" -j1

  echo
  echo "Built: $build_dir"
  echo "liboqs.a:"
  ls -lh "$build_dir/lib/liboqs.a"

  echo
  echo "Stack-usage files:"
  find "$build_dir" -name "*.su" | wc -l
}

build_variant "baseline" ""
build_variant "reduce_ram" "-DMLD_CONFIG_REDUCE_RAM"
build_variant "lazy_polyvec" "-DMLD_CONFIG_EXPERIMENTAL_LAZY_MATRIX_ONLY -DMLD_CONFIG_SERIAL_FIPS202_ONLY"
