# Layer 3 v37: Build Matrix Validation

## Scope

v37 validates whether the optimized ML-KEM-768 and ML-DSA-44 lifecycle-workspace build compiles and passes core correctness checks across selected build configurations.

The matrix uses static minimal liboqs builds for:

- ML-KEM-768 with v29 lifecycle workspace
- ML-DSA-44 with v24 lifecycle workspace

## Summary

| Metric | Value |
|---|---:|
| build cases | 4 |
| total result rows | 12 |
| PASS rows | 12 |
| FAIL rows | 0 |
| overall v37 status | PASS |

## Build matrix results

| Build case | Build type | C flags profile | Linkage | ML-KEM symbols | ML-DSA symbols | ML-KEM ws | ML-DSA ws | Combined ws | Status |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| release_static_o3 | Release | O3 | static | 2 | 2 | 13088 | 44064 | 57152 | PASS |
| relwithdebinfo_static_o2 | RelWithDebInfo | O2_debug | static | 2 | 2 | 13088 | 44064 | 57152 | PASS |
| debug_static_o0 | Debug | O0_debug | static | 2 | 2 | 13088 | 44064 | 57152 | PASS |
| size_static_os | Release | Os | static | 2 | 2 | 13088 | 44064 | 57152 | PASS |

## Component-level results

| Build case | Component | Iterations | Passed | Failed | Status | Notes |
|---|---|---:|---:|---:|---|---|
| release_static_o3 | mlkem_valid_flow | 5 | 5 | 0 | PASS | core correctness |
| release_static_o3 | mldsa_valid_and_negative | 5 | 5 | 0 | PASS | core correctness |
| release_static_o3 | combined_mlkem_mldsa_sequence | 5 | 5 | 0 | PASS | core correctness |
| relwithdebinfo_static_o2 | mlkem_valid_flow | 5 | 5 | 0 | PASS | core correctness |
| relwithdebinfo_static_o2 | mldsa_valid_and_negative | 5 | 5 | 0 | PASS | core correctness |
| relwithdebinfo_static_o2 | combined_mlkem_mldsa_sequence | 5 | 5 | 0 | PASS | core correctness |
| debug_static_o0 | mlkem_valid_flow | 5 | 5 | 0 | PASS | core correctness |
| debug_static_o0 | mldsa_valid_and_negative | 5 | 5 | 0 | PASS | core correctness |
| debug_static_o0 | combined_mlkem_mldsa_sequence | 5 | 5 | 0 | PASS | core correctness |
| size_static_os | mlkem_valid_flow | 5 | 5 | 0 | PASS | core correctness |
| size_static_os | mldsa_valid_and_negative | 5 | 5 | 0 | PASS | core correctness |
| size_static_os | combined_mlkem_mldsa_sequence | 5 | 5 | 0 | PASS | core correctness |

## What v37 checks

| Area | Check |
|---|---|
| Build coverage | selected Release, RelWithDebInfo, Debug, and size-focused static builds |
| Symbol coverage | ML-KEM and ML-DSA lifecycle workspace byte/setter symbols are discovered per build |
| Harness compile | v37 correctness harness compiles against each selected build |
| ML-KEM correctness | keypair, encaps, decaps, shared-secret equality |
| ML-DSA correctness | keypair, sign, verify, reject modified message/signature |
| Combined flow | ML-KEM transcript construction and ML-DSA signature verification |

## Claims supported by v37

| Claim | Status |
|---|---|
| optimized lifecycle-workspace build works across selected build configurations | supported if PASS |
| lifecycle workspace symbols are present across selected configurations | supported if PASS |
| core ML-KEM, ML-DSA, and combined correctness checks pass across the matrix | supported if PASS |

## Limitations

- v37 does not test every compiler.
- v37 does not test every architecture.
- v37 does not test every liboqs CMake option.
- v37 does not test Rust FFI.
- v37 does not prove constant-time behavior.
- v37 does not prove production portability.

## Next

v38 should perform timing / constant-time-style leakage validation.
