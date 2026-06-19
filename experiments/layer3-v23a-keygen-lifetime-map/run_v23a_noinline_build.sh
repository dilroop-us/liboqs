#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"
BUILD="$ROOT/build-v23a-keygen-lifetime-map-noinline"

rm -rf "$BUILD"

cmake -GNinja \
  -S "$ROOT" \
  -B "$BUILD" \
  -DOQS_MINIMAL_BUILD="KEM_ml_kem_768;SIG_ml_dsa_44" \
  -DOQS_EMBEDDED_BUILD=ON \
  -DOQS_USE_OPENSSL=OFF \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DCMAKE_C_FLAGS="-DMLD_CONFIG_EXPERIMENTAL_CALLER_SIGN_WORKSPACE -DMLD_CONFIG_EXPERIMENTAL_CALLER_ATTEMPT_WORKSPACE -DMLD_CONFIG_EXPERIMENTAL_UNIFIED_SIGN_WORKSPACE -DMLD_CONFIG_EXPERIMENTAL_CALLER_VERIFY_WORKSPACE -fstack-usage -Wframe-larger-than=4096 -fno-inline -fno-inline-functions -fno-inline-small-functions -fno-inline-functions-called-once"

ninja -C "$BUILD" -j1

echo
echo "Built v23a no-inline attribution build:"
ls -lh "$BUILD/lib/liboqs.a"

echo
echo "Target stack usage from .su files:"
find "$BUILD" -name "*.su" -print0 | \
  xargs -0 grep -H "keypair_internal\|pk_from_sk" | \
  grep "MLDSA_NATIVE_MLDSA44" | \
  sort || true
