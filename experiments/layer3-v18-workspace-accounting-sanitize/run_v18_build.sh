#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/pqc/liboqs"
BUILD="$ROOT/build-v18-workspace-accounting-sanitize"

rm -rf "$BUILD"

cmake -GNinja \
  -S "$ROOT" \
  -B "$BUILD" \
  -DOQS_MINIMAL_BUILD="KEM_ml_kem_768;SIG_ml_dsa_44" \
  -DOQS_EMBEDDED_BUILD=ON \
  -DOQS_USE_OPENSSL=OFF \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DCMAKE_C_FLAGS="-DMLD_CONFIG_EXPERIMENTAL_CALLER_SIGN_WORKSPACE -DMLD_CONFIG_EXPERIMENTAL_WORKSPACE_SANITIZE -fstack-usage -Wframe-larger-than=4096"

ninja -C "$BUILD" -j1

echo
echo "Built v18:"
ls -lh "$BUILD/lib/liboqs.a"

echo
echo "Stack-usage files:"
find "$BUILD" -name "*.su" | wc -l

echo
echo "Flag check:"
grep -R "MLD_CONFIG_EXPERIMENTAL_WORKSPACE_SANITIZE" "$BUILD/compile_commands.json" | head
