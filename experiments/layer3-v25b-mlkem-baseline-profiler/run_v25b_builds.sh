#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"

MLKEM_ONLY="$ROOT/build-v25b-mlkem-only-baseline"
COMBINED="$ROOT/build-v25b-combined-baseline"

rm -rf "$MLKEM_ONLY" "$COMBINED"

echo "================ Building ML-KEM-only baseline ================"

cmake -GNinja \
  -S "$ROOT" \
  -B "$MLKEM_ONLY" \
  -DOQS_MINIMAL_BUILD="KEM_ml_kem_768" \
  -DOQS_EMBEDDED_BUILD=ON \
  -DOQS_USE_OPENSSL=OFF \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

ninja -C "$MLKEM_ONLY" -j1

echo
echo "ML-KEM-only liboqs:"
ls -lh "$MLKEM_ONLY/lib/liboqs.a"

echo
echo "================ Building combined ML-KEM + ML-DSA baseline ================"

cmake -GNinja \
  -S "$ROOT" \
  -B "$COMBINED" \
  -DOQS_MINIMAL_BUILD="KEM_ml_kem_768;SIG_ml_dsa_44" \
  -DOQS_EMBEDDED_BUILD=ON \
  -DOQS_USE_OPENSSL=OFF \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DCMAKE_C_FLAGS="-DMLD_CONFIG_EXPERIMENTAL_CALLER_SIGN_WORKSPACE -DMLD_CONFIG_EXPERIMENTAL_CALLER_ATTEMPT_WORKSPACE -DMLD_CONFIG_EXPERIMENTAL_UNIFIED_SIGN_WORKSPACE -DMLD_CONFIG_EXPERIMENTAL_CALLER_VERIFY_WORKSPACE -DMLD_CONFIG_EXPERIMENTAL_CALLER_KEYGEN_WORKSPACE -DMLD_CONFIG_EXPERIMENTAL_COMPACT_LIFECYCLE_WORKSPACE"

ninja -C "$COMBINED" -j1

echo
echo "Combined liboqs:"
ls -lh "$COMBINED/lib/liboqs.a"
