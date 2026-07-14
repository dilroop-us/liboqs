# Layer 3 v40: Rust FFI / Integration Validation

## Scope

v40 validates that Rust can link against the optimized liboqs build, configure Rust-owned aligned lifecycle workspaces through FFI, and execute tested ML-KEM, ML-DSA, and combined flows.

The optimized build uses:

- ML-KEM-768 with v29 lifecycle workspace
- ML-DSA-44 with v24 lifecycle workspace

## Configuration

| Metric | Value |
|---|---:|
| iterations per case | 100 |

## Workspace sizes

| Scheme | Bytes | KiB |
|---|---:|---:|
| ML-KEM-768 | 13088 | 12.78 |
| ML-DSA-44 | 44064 | 43.03 |
| Combined | 57152 | 55.81 |

## Summary

| Metric | Value |
|---|---:|
| total rows | 3 |
| PASS rows | 3 |
| FAIL rows | 0 |
| overall v40 status | PASS |

## Rust FFI results

| Case | Iterations | Passed | Failed | Status | Notes |
|---|---:|---:|---:|---|---|
| rust_mlkem_valid_flow | 100 | 100 | 0 | PASS | Rust FFI ML-KEM keypair/encaps/decaps/shared-secret equality |
| rust_mldsa_valid_and_negative | 100 | 100 | 0 | PASS | Rust FFI ML-DSA sign/verify plus modified message/signature rejection |
| rust_combined_mlkem_mldsa_sequence | 100 | 100 | 0 | PASS | Rust FFI combined ML-KEM transcript plus ML-DSA signature flow |

## What v40 checks

| Area | Check |
|---|---|
| Rust linking | Rust binary links against optimized static liboqs build |
| Rust FFI | Rust calls OQS KEM/SIG APIs through extern C declarations |
| Workspace ownership | Rust allocates 64-byte aligned caller-owned lifecycle workspaces |
| Workspace setup | Rust calls ML-KEM and ML-DSA lifecycle workspace setters |
| ML-KEM correctness | keypair, encaps, decaps, shared-secret equality |
| ML-DSA correctness | keypair, sign, verify, modified message/signature rejection |
| Combined flow | ML-KEM transcript construction and ML-DSA signature verification |

## Claims supported by v40

| Claim | Status |
|---|---|
| Rust can link against the optimized liboqs build | supported if PASS |
| Rust-owned aligned lifecycle workspaces can be configured through FFI | supported if PASS |
| Tested ML-KEM, ML-DSA, and combined Rust FFI flows pass | supported if PASS |

## Limitations

- v40 does not prove full Rust safety.
- v40 does not prove complete FFI safety.
- v40 does not test async/threading safety; that belongs to a later step.
- v40 does not test all target platforms.
- v40 does not test real constrained-device hardware.
- v40 does not prove production readiness.

## Next

v41 should build a cleaner Rust workspace ownership/alignment API so raw unsafe FFI calls are not spread across the Rust integration layer.
