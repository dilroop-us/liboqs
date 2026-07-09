# Layer 3 v37: Build Matrix Validation

## Goal

Validate whether the optimized lifecycle-workspace ML-KEM/ML-DSA build compiles and passes core correctness checks across selected build configurations.

## Optimized build under test

- ML-KEM-768 with v29 lifecycle workspace
- ML-DSA-44 with v24 lifecycle workspace

## Matrix

v37 tests selected static minimal liboqs builds:

- Release static with `-O3`
- RelWithDebInfo static with `-O2 -g`
- Debug static with `-O0 -g3`
- size-focused Release static with `-Os`

## What v37 checks

For every build case, v37 checks:

- ML-KEM lifecycle workspace symbols exist
- ML-DSA lifecycle workspace symbols exist
- the v37 harness compiles against the selected build
- ML-KEM keypair/encaps/decaps/shared-secret equality passes
- ML-DSA keypair/sign/verify/negative checks pass
- combined ML-KEM transcript + ML-DSA signature verification passes

## Success criteria

v37 passes if every selected build case:

- builds successfully
- exposes the expected lifecycle workspace symbols
- compiles the v37 harness
- passes all ML-KEM, ML-DSA, and combined correctness rows

## Claims supported

v37 supports the claim that the optimized lifecycle-workspace build works across the selected build configurations.

## Limitations

v37 does not prove:

- all compilers work
- all architectures work
- all CMake options work
- Rust FFI works
- constant-time behavior
- production portability

## Next

v38 should perform timing / constant-time-style leakage validation.
