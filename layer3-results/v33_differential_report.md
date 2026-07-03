# Layer 3 v33: Baseline-vs-Optimized Differential Tests

## Scope

v33 checks behavioral compatibility between baseline/reference liboqs and the optimized lifecycle-workspace liboqs build.

The optimized build uses:

- ML-KEM-768 with v29 lifecycle workspace
- ML-DSA-44 with v24 lifecycle workspace

v33 does not add new stack or workspace optimizations. It is a differential compatibility validation step.

## Workspace sizes for optimized build

| Scheme | Bytes | KiB |
|---|---:|---:|
| ML-KEM-768 | 13088 | 12.78 |
| ML-DSA-44 | 44064 | 43.03 |
| Combined | 57152 | 55.81 |

## Summary

| Metric | Value |
|---|---:|
| total rows | 12 |
| interoperability rows | 6 |
| PASS rows | 12 |
| FAIL rows | 0 |
| overall v33 status | PASS |

## Differential results

| Test | Producer | Consumer | Operation | Iterations | Passed | Failed | Status | Notes |
|---|---|---|---|---:|---:|---:|---|---|
| baseline_mlkem_generate | baseline | none | mlkem_gen | 100 | 100 | 0 | PASS | baseline generates ML-KEM vectors |
| baseline_mlkem_to_optimized | baseline | optimized | mlkem_consume | 100 | 100 | 0 | PASS | optimized consumes baseline ML-KEM vectors |
| optimized_mlkem_generate | optimized | none | mlkem_gen | 100 | 100 | 0 | PASS | optimized generates ML-KEM vectors |
| optimized_mlkem_to_baseline | optimized | baseline | mlkem_consume | 100 | 100 | 0 | PASS | baseline consumes optimized ML-KEM vectors |
| baseline_mldsa_generate | baseline | none | mldsa_gen | 100 | 100 | 0 | PASS | baseline generates ML-DSA signatures |
| baseline_mldsa_to_optimized | baseline | optimized | mldsa_consume | 100 | 100 | 0 | PASS | optimized verifies and signs using baseline ML-DSA vectors |
| optimized_mldsa_generate | optimized | none | mldsa_gen | 100 | 100 | 0 | PASS | optimized generates ML-DSA signatures |
| optimized_mldsa_to_baseline | optimized | baseline | mldsa_consume | 100 | 100 | 0 | PASS | baseline verifies and signs using optimized ML-DSA vectors |
| baseline_combined_generate | baseline | none | combined_gen | 100 | 100 | 0 | PASS | baseline generates combined KEM transcript and signature vectors |
| baseline_combined_to_optimized | baseline | optimized | combined_consume | 100 | 100 | 0 | PASS | optimized consumes baseline combined vectors |
| optimized_combined_generate | optimized | none | combined_gen | 100 | 100 | 0 | PASS | optimized generates combined KEM transcript and signature vectors |
| optimized_combined_to_baseline | optimized | baseline | combined_consume | 100 | 100 | 0 | PASS | baseline consumes optimized combined vectors |

## What v33 checks

| Area | Check |
|---|---|
| ML-KEM | baseline generated keys/ciphertexts/shared secrets are consumed by optimized build |
| ML-KEM | optimized generated keys/ciphertexts/shared secrets are consumed by baseline build |
| ML-DSA | baseline generated signatures verify in optimized build |
| ML-DSA | optimized generated signatures verify in baseline build |
| ML-DSA negative checks | modified messages and signatures are rejected during consume tests |
| Combined | baseline KEM transcript plus DSA signature is consumed by optimized build |
| Combined | optimized KEM transcript plus DSA signature is consumed by baseline build |

## Claims supported by v33

| Claim | Status |
|---|---|
| optimized ML-KEM remains interoperable with baseline ML-KEM | supported if PASS |
| optimized ML-DSA remains interoperable with baseline ML-DSA | supported if PASS |
| optimized combined KEM transcript plus DSA signature flow remains baseline-compatible | supported if PASS |
| lifecycle-workspace changes did not break baseline-level API behavior in this harness | supported if PASS |

## Limitations

- v33 is not a formal proof.
- v33 does not prove constant-time behavior.
- v33 does not run sanitizers.
- v33 does not prove memory safety.
- v33 does not prove threading/TLS safety.
- v33 does not test Rust FFI.
- v33 does not test Pi/constrained-device behavior.

## Next

v34 should run ASan/UBSan/Valgrind-style memory-safety validation.
