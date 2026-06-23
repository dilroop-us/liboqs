# Layer 3 v25b: ML-KEM-768 Baseline Operation Profiler

## Goal

Measure ML-KEM-768 performance before modifying ML-KEM implementation code.

v25b is profiling only.

## Operations measured

- ML-KEM keypair
- ML-KEM encapsulation
- ML-KEM decapsulation

## Build profiles

v25b uses two release builds:

1. ML-KEM-only build
2. Combined ML-KEM + ML-DSA build

The ML-KEM-only build gives the clean ML-KEM baseline.

The combined build validates ML-KEM performance in the full project context with ML-DSA v24b included.

## Outputs

Generated result files:

- `layer3-results/v25b_mlkem_correctness.csv`
- `layer3-results/v25b_mlkem_speed.csv`
- `layer3-results/v25b_mlkem_size.csv`
- `layer3-results/v25b_mlkem_baseline_profiler_report.md`

## Why v25b matters

v25a identified the ML-KEM stack hotspots:

- `indcpa_enc`
- `indcpa_keypair_derand`
- `indcpa_dec`

v25b creates the speed and size baseline before those functions are modified.

## Next versions

Recommended order:

1. v26b: caller workspace for `indcpa_enc`
2. v27b: caller workspace for `indcpa_keypair_derand`
3. v28b: caller workspace for `indcpa_dec`
4. v29a: compact ML-KEM lifecycle workspace analysis
5. v29b: compact ML-KEM lifecycle workspace API

## Safety rule

Future ML-KEM patches should only move storage location:

- from stack local buffer
- to caller-provided workspace buffer

Do not change:

- constant-time comparison
- failure handling
- decapsulation selection logic
- hashing/KDF order
- randomness
- compression/decompression arithmetic
- polynomial arithmetic

## Embedded-build RNG note

The profiler installs a benchmark-only custom RNG using `OQS_randombytes_custom_algorithm()`.

This is needed because `OQS_EMBEDDED_BUILD=ON` disables the default system RNG path.

The custom RNG is only for local benchmarking and correctness testing. It is not production randomness.
