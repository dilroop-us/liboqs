#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"
BUILD="$ROOT/build-v25a-mlkem-only-stack-lifetime"

rm -rf "$BUILD"

cmake -GNinja \
  -S "$ROOT" \
  -B "$BUILD" \
  -DOQS_MINIMAL_BUILD="KEM_ml_kem_768" \
  -DOQS_EMBEDDED_BUILD=ON \
  -DOQS_USE_OPENSSL=OFF \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DCMAKE_C_FLAGS="-fstack-usage -Wframe-larger-than=4096"

ninja -C "$BUILD" -j1

echo
echo "Built v25a ML-KEM-only stack/lifetime build:"
ls -lh "$BUILD/lib/liboqs.a"

echo
echo "Stack-usage files:"
find "$BUILD" -name "*.su" | wc -l
