# Layer 3 v31: Combined Correctness Harness

## Scope

v31 validates the final optimized combined PQC build using:

- ML-KEM-768 with v29 lifecycle workspace
- ML-DSA-44 with v24b lifecycle workspace
- one combined C harness linked against the optimized liboqs build

v31 is a correctness-validation step. It does not introduce new stack or workspace optimizations.

## Workspace setup

| Scheme | Workspace kind | Bytes | KiB |
|---|---|---:|---:|
| ML-KEM-768 | v29_lifecycle_workspace | 13088 | 12.78 |
| ML-DSA-44 | v24_lifecycle_workspace | 44064 | 43.03 |
| Combined | mlkem_plus_mldsa_lifecycle | 57152 | 55.81 |

## Correctness results

| Test | Iterations | Passed | Failed | Mean us | Status |
|---|---:|---:|---:|---:|---|
| mlkem_valid_flow | 1000 | 1000 | 0 | 43.267 | PASS |
| mldsa_valid_and_negative | 1000 | 1000 | 0 | 191.503 | PASS |
| combined_mlkem_mldsa_sequence | 1000 | 1000 | 0 | 190.240 | PASS |

## Summary

| Metric | Value |
|---|---:|
| total test groups | 3 |
| total iteration groups | 3000 |
| total passed | 3000 |
| total failed | 0 |
| overall status | PASS |

## What v31 checks

| Area | Check |
|---|---|
| ML-KEM | keypair, encapsulation, decapsulation, shared-secret equality |
| ML-DSA | keypair, signing, valid signature verification |
| ML-DSA negative check | modified message rejection |
| ML-DSA negative check | modified signature rejection |
| Combined sequence | ML-KEM key exchange followed by ML-DSA transcript signing and verification |

## Claims supported by v31

| Claim | Status |
|---|---|
| ML-KEM v29 lifecycle workspace can run valid KEM flow | supported if PASS |
| ML-DSA v24b lifecycle workspace can run valid sign/verify flow | supported if PASS |
| ML-DSA rejects modified messages/signatures in this harness | supported if PASS |
| ML-KEM + ML-DSA can coexist in the same optimized binary | supported if PASS |
| Full misuse, sanitizer, threading, and differential safety | not claimed in v31 |

## Limitations

- v31 is not a formal proof.
- v31 does not prove constant-time behavior.
- v31 does not test workspace misuse cases deeply; that belongs to v32.
- v31 does not perform baseline-vs-optimized differential testing; that belongs to v33.
- v31 does not run ASan/UBSan/Valgrind; that belongs to v34.
- v31 does not test Rust FFI or Pi behavior.

## Next

v32 should test workspace API misuse for both ML-KEM and ML-DSA.
