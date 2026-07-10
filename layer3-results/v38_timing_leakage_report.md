# Layer 3 v38: Timing / Constant-Time-Style Leakage Validation

## Scope

v38 performs dudect-style timing-distribution screening for selected optimized ML-KEM-768 and ML-DSA-44 lifecycle-workspace operations.

This is statistical timing screening, not a formal constant-time proof.

The optimized build uses:

- ML-KEM-768 with v29 lifecycle workspace
- ML-DSA-44 with v24 lifecycle workspace

## Configuration

| Metric | Value |
|---|---:|
| samples per case | 5000 |
| warmup operations per case | 500 |
| Welch t-threshold | 4.500 |
| batch size | 1 |

## Workspace sizes

| Scheme | Bytes | KiB |
|---|---:|---:|
| ML-KEM-768 | 13088 | 12.78 |
| ML-DSA-44 | 44064 | 43.03 |
| Combined | 57152 | 55.81 |

## Summary

| Metric | Value |
|---|---:|
| total timing rows | 4 |
| PASS rows | 4 |
| FLAG rows | 0 |
| FAIL rows | 0 |
| execution status | PASS |
| timing classification | NO_FLAGS |

## Timing results

| Case | Samples | Class 0 n | Class 1 n | Class 0 mean ns | Class 1 mean ns | abs(Welch t) | Threshold | Exec failures | Status | Notes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| mlkem_decaps_valid_vs_invalid_ct | 5000 | 2509 | 2491 | 17112.681 | 17116.271 | 0.251639 | 4.500 | 0 | PASS | secret-key operation; valid ciphertext class vs modified ciphertext class |
| mldsa_verify_valid_vs_invalid_sig | 5000 | 2547 | 2453 | 27614.184 | 27622.292 | 0.474924 | 4.500 | 0 | PASS | public verification operation; valid signature class vs modified signature class |
| mldsa_sign_fixed_vs_alt_msg | 5000 | 2502 | 2498 | 78884.430 | 79704.725 | 0.620985 | 4.500 | 0 | PASS | secret-key operation; fixed message class vs alternate message class |
| combined_verify_valid_vs_modified_transcript | 5000 | 2468 | 2532 | 32851.385 | 32833.550 | 0.913085 | 4.500 | 0 | PASS | combined transcript verification; valid transcript class vs modified transcript class |

## Interpretation

- `PASS` means the tested timing classes stayed below the configured Welch t-threshold.
- `FLAG` means the tested timing classes exceeded the configured threshold and should be treated as a timing-leakage candidate or public-input timing difference requiring investigation.
- `FAIL` means the underlying cryptographic operation failed an expected correctness condition during timing collection.

## What v38 checks

| Area | Check |
|---|---|
| ML-KEM decapsulation | valid ciphertext timing class vs modified ciphertext timing class |
| ML-DSA verification | valid signature timing class vs modified signature timing class |
| ML-DSA signing | fixed message timing class vs alternate message timing class |
| Combined transcript verification | valid transcript timing class vs modified transcript timing class |
| Statistical test | absolute Welch t-statistic against configured threshold |

## Claims supported by v38

| Claim | Status |
|---|---|
| v38 timing harness executed selected ML-KEM/ML-DSA timing classes without correctness failures | supported if execution status is PASS |
| no tested timing row exceeded the configured t-threshold | supported only if FLAG rows = 0 |
| selected timing rows require investigation | supported if FLAG rows > 0 |

## Limitations

- v38 is not a formal constant-time proof.
- v38 does not test power, EM, cache, branch predictor, or microarchitectural leakage directly.
- v38 results can be affected by CPU frequency scaling, OS scheduling, thermal throttling, and background processes.
- ML-DSA verification timing differences may involve public inputs and are not automatically secret leakage.
- v38 does not prove production side-channel resistance.

## Next

v39 should produce a final memory/accounting/evidence report tying v31-v38 together, or run a deeper timing follow-up if v38 produces timing flags.
