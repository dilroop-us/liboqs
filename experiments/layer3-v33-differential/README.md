# Layer 3 v33: Baseline-vs-Optimized Differential Tests

## Goal

Validate behavioral compatibility between baseline/reference liboqs and the optimized lifecycle-workspace liboqs build.

v33 compares:

- baseline/reference liboqs built from the official merge-base
- optimized liboqs from the experiments branch

The optimized build uses:

- ML-KEM-768 with v29 lifecycle workspace
- ML-DSA-44 with v24 lifecycle workspace

## What v33 tests

ML-KEM:

- baseline generated ML-KEM vectors consumed by optimized build
- optimized generated ML-KEM vectors consumed by baseline build
- decapsulation shared-secret equality
- local encapsulation using foreign public keys

ML-DSA:

- baseline generated signatures verified by optimized build
- optimized generated signatures verified by baseline build
- modified message rejection
- modified signature rejection
- local signing using foreign secret keys

Combined sequence:

- baseline KEM transcript plus DSA signature consumed by optimized build
- optimized KEM transcript plus DSA signature consumed by baseline build
- KEM decapsulation shared-secret equality
- DSA transcript verification
- negative transcript/signature rejection

## Optimized workspace sizes

- ML-KEM v29 lifecycle workspace: 13088 B
- ML-DSA v24 lifecycle workspace: 44064 B
- combined explicit workspace: 57152 B

## Result

The final v33 run passed with 100 iterations per row:

- total rows: 12
- PASS rows: 12
- FAIL rows: 0

## Limitations

v33 does not prove:

- production readiness
- constant-time behavior
- sanitizer cleanliness
- threading/TLS safety
- Rust FFI safety
- Pi readiness

## Next

v34 should run ASan/UBSan/Valgrind-style memory-safety validation.
