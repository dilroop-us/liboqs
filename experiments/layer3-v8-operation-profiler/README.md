# Layer 3 v8: Operation-Specific Profiler

## Goal

This experiment separates ML-KEM-768 and ML-DSA-44 operations into individual profiling modes.

## Why this matters

Earlier versions showed that ML-DSA-44 has higher stack pressure than ML-KEM-768, but they measured combined flows. v8 identifies which exact operation causes the highest speed and memory cost.

## Build used

- `OQS_EMBEDDED_BUILD=ON`
- `OQS_USE_OPENSSL=OFF`
- Minimal build:
  - ML-KEM-768
  - ML-DSA-44

## Custom RNG

The embedded build uses a custom RNG callback backed by Linux `getrandom()` for this Ubuntu experiment.

## Modes

```bash
./v8_operation_profiler kem-keygen
./v8_operation_profiler kem-encaps
./v8_operation_profiler kem-decaps
./v8_operation_profiler sig-keypair
./v8_operation_profiler sig-sign
./v8_operation_profiler sig-verify
