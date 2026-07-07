# Layer 3 v35: Constrained-Device Memory Budget Validation

## Scope

v35 evaluates the optimized lifecycle-workspace build under constrained-device-style resource checks.

This is a host-side Raspberry-Pi-style budget validation. It does not claim actual Raspberry Pi runtime validation unless the harness is run on a Raspberry Pi.

The optimized build uses:

- ML-KEM-768 with v29 lifecycle workspace
- ML-DSA-44 with v24 lifecycle workspace

## Workspace sizes

| Scheme | Bytes | KiB |
|---|---:|---:|
| ML-KEM-768 | 13088 | 12.78 |
| ML-DSA-44 | 44064 | 43.03 |
| Combined | 57152 | 55.81 |

## Summary

| Metric | Value |
|---|---:|
| total rows | 10 |
| PASS rows | 10 |
| FAIL rows | 0 |
| overall v35 status | PASS |

## Budget and correctness results

| Category | Name | Value | Budget | Iterations | Passed | Failed | Status | Notes |
|---|---|---:|---:|---:|---:|---:|---|---|
| workspace | workspace_mlkem | 13088 | 16384 |  |  |  | PASS | explicit workspace budget |
| workspace | workspace_mldsa | 44064 | 49152 |  |  |  | PASS | explicit workspace budget |
| workspace | workspace_combined | 57152 | 65536 |  |  |  | PASS | explicit workspace budget |
| correctness | mlkem_valid_flow |  |  | 100 | 100 | 0 | PASS | optimized flow correctness |
| correctness | mldsa_valid_and_negative |  |  | 100 | 100 | 0 | PASS | optimized flow correctness |
| correctness | combined_mlkem_mldsa_sequence |  |  | 100 | 100 | 0 | PASS | optimized flow correctness |
| resource | liboqs_archive_bytes | 864792 | 8388608 |  |  |  | PASS | size/rss budget |
| resource | harness_binary_bytes | 268648 | 16777216 |  |  |  | PASS | size/rss budget |
| resource | max_rss_kb | 2180 | 131072 |  |  |  | PASS | size/rss budget |
| resource | max_static_stack_usage_bytes | 3648 | 65536 |  |  |  | PASS | max .su static stack usage |

## Binary and runtime size details

| Metric | Value | Budget | Status |
|---|---:|---:|---|
| liboqs_archive_bytes | 864792 | 8388608 | PASS |
| harness_binary_bytes | 268648 | 16777216 | PASS |
| harness_text_bytes | 212018 |  | INFO |
| harness_data_bytes | 1696 |  | INFO |
| harness_bss_bytes | 344 |  | INFO |
| harness_dec_bytes | 214058 |  | INFO |
| max_rss_kb | 2180 | 131072 | PASS |

## Runtime memory

| Metric | Value |
|---|---:|
| Maximum resident set size | 2180 kB |
| User time | 0.05 s |
| System time | 0.00 s |
| Exit status | 0 |

## Top static stack-usage entries

| Rank | Bytes | Kind | Function | File |
|---:|---:|---|---|---|
| 1 | 3648 | static | `/home/home/pqc/liboqs/src/sig/ml_dsa/mldsa-native_ml-dsa-44_ref/mldsa/src/poly.c:682:6:PQCP_MLDSA_NATIVE_MLDSA44_C_poly_uniform_4x` | `build-v35-constrained-budget/src/sig/ml_dsa/CMakeFiles/ml_dsa_44_ref.dir/mldsa-native_ml-dsa-44_ref/mldsa/src/poly.c.su` |
| 2 | 3648 | static | `/home/home/pqc/liboqs/src/sig/ml_dsa/mldsa-native_ml-dsa-44_x86_64/mldsa/src/poly.c:682:6:PQCP_MLDSA_NATIVE_MLDSA44_X86_64_poly_uniform_4x` | `build-v35-constrained-budget/src/sig/ml_dsa/CMakeFiles/ml_dsa_44_x86_64.dir/mldsa-native_ml-dsa-44_x86_64/mldsa/src/poly.c.su` |
| 3 | 3360 | static | `/home/home/pqc/liboqs/src/sig/ml_dsa/mldsa-native_ml-dsa-44_ref/mldsa/src/poly_kl.c:510:6:PQCP_MLDSA_NATIVE_MLDSA44_C_poly_uniform_gamma1_4x` | `build-v35-constrained-budget/src/sig/ml_dsa/CMakeFiles/ml_dsa_44_ref.dir/mldsa-native_ml-dsa-44_ref/mldsa/src/poly_kl.c.su` |
| 4 | 3360 | static | `/home/home/pqc/liboqs/src/sig/ml_dsa/mldsa-native_ml-dsa-44_x86_64/mldsa/src/poly_kl.c:510:6:PQCP_MLDSA_NATIVE_MLDSA44_X86_64_poly_uniform_gamma1_4x` | `build-v35-constrained-budget/src/sig/ml_dsa/CMakeFiles/ml_dsa_44_x86_64.dir/mldsa-native_ml-dsa-44_x86_64/mldsa/src/poly_kl.c.su` |
| 5 | 2784 | static | `/home/home/pqc/liboqs/src/kem/ml_kem/mlkem-native_ml-kem-768_ref/mlkem/src/kem.c:43:5:PQCP_MLKEM_NATIVE_MLKEM768_C_check_pk` | `build-v35-constrained-budget/src/kem/ml_kem/CMakeFiles/ml_kem_768_ref.dir/mlkem-native_ml-kem-768_ref/mlkem/src/kem.c.su` |
| 6 | 2784 | static | `/home/home/pqc/liboqs/src/kem/ml_kem/mlkem-native_ml-kem-768_x86_64/mlkem/src/kem.c:43:5:PQCP_MLKEM_NATIVE_MLKEM768_X86_64_check_pk` | `build-v35-constrained-budget/src/kem/ml_kem/CMakeFiles/ml_kem_768_x86_64.dir/mlkem-native_ml-kem-768_x86_64/mlkem/src/kem.c.su` |
| 7 | 2240 | static | `/home/home/pqc/liboqs/src/kem/ml_kem/mlkem-native_ml-kem-768_ref/mlkem/src/sampling.c:152:6:PQCP_MLKEM_NATIVE_MLKEM768_C_poly_rej_uniform_x4` | `build-v35-constrained-budget/src/kem/ml_kem/CMakeFiles/ml_kem_768_ref.dir/mlkem-native_ml-kem-768_ref/mlkem/src/sampling.c.su` |
| 8 | 2240 | static | `/home/home/pqc/liboqs/src/kem/ml_kem/mlkem-native_ml-kem-768_x86_64/mlkem/src/sampling.c:152:6:PQCP_MLKEM_NATIVE_MLKEM768_X86_64_poly_rej_uniform_x4` | `build-v35-constrained-budget/src/kem/ml_kem/CMakeFiles/ml_kem_768_x86_64.dir/mlkem-native_ml-kem-768_x86_64/mlkem/src/sampling.c.su` |
| 9 | 2176 | static | `/home/home/pqc/liboqs/src/sig/ml_dsa/mldsa-native_ml-dsa-44_ref/mldsa/src/sign.c:428:12:mld_compute_pack_t0_t1` | `build-v35-constrained-budget/src/sig/ml_dsa/CMakeFiles/ml_dsa_44_ref.dir/mldsa-native_ml-dsa-44_ref/mldsa/src/sign.c.su` |
| 10 | 2176 | static | `/home/home/pqc/liboqs/src/sig/ml_dsa/mldsa-native_ml-dsa-44_x86_64/mldsa/src/sign.c:428:12:mld_compute_pack_t0_t1` | `build-v35-constrained-budget/src/sig/ml_dsa/CMakeFiles/ml_dsa_44_x86_64.dir/mldsa-native_ml-dsa-44_x86_64/mldsa/src/sign.c.su` |
| 11 | 1792 | static | `/home/home/pqc/liboqs/src/sig/sig.c:14:21:OQS_SIG_alg_identifier` | `build-v35-constrained-budget/src/CMakeFiles/oqs.dir/sig/sig.c.su` |
| 12 | 1376 | static | `/home/home/pqc/liboqs/src/kem/ml_kem/mlkem-native_ml-kem-768_ref/mlkem/src/kem.c:376:5:PQCP_MLKEM_NATIVE_MLKEM768_C_dec` | `build-v35-constrained-budget/src/kem/ml_kem/CMakeFiles/ml_kem_768_ref.dir/mlkem-native_ml-kem-768_ref/mlkem/src/kem.c.su` |
| 13 | 1376 | static | `/home/home/pqc/liboqs/src/kem/ml_kem/mlkem-native_ml-kem-768_x86_64/mlkem/src/kem.c:376:5:PQCP_MLKEM_NATIVE_MLKEM768_X86_64_dec` | `build-v35-constrained-budget/src/kem/ml_kem/CMakeFiles/ml_kem_768_x86_64.dir/mlkem-native_ml-kem-768_x86_64/mlkem/src/kem.c.su` |
| 14 | 1216 | static | `/home/home/pqc/liboqs/src/sig/ml_dsa/mldsa-native_ml-dsa-44_ref/mldsa/src/poly_kl.c:326:6:PQCP_MLDSA_NATIVE_MLDSA44_C_poly_uniform_eta_4x` | `build-v35-constrained-budget/src/sig/ml_dsa/CMakeFiles/ml_dsa_44_ref.dir/mldsa-native_ml-dsa-44_ref/mldsa/src/poly_kl.c.su` |
| 15 | 1216 | static | `/home/home/pqc/liboqs/src/sig/ml_dsa/mldsa-native_ml-dsa-44_x86_64/mldsa/src/poly_kl.c:326:6:PQCP_MLDSA_NATIVE_MLDSA44_X86_64_poly_uniform_eta_4x` | `build-v35-constrained-budget/src/sig/ml_dsa/CMakeFiles/ml_dsa_44_x86_64.dir/mldsa-native_ml-dsa-44_x86_64/mldsa/src/poly_kl.c.su` |
| 16 | 1064 | static | `/home/home/pqc/liboqs/src/common/sha3/xkcp_low/KeccakP-1600times4/avx2/KeccakP-1600-times4-SIMD256.c:842:6:KeccakP1600times4_PermuteAll_12rounds_avx2` | `build-v35-constrained-budget/src/common/sha3/xkcp_low/CMakeFiles/xkcp_low_keccakp_1600times4_avx2.dir/KeccakP-1600times4/avx2/KeccakP-1600-times4-SIMD256.c.su` |
| 17 | 1064 | static | `/home/home/pqc/liboqs/src/common/sha3/xkcp_low/KeccakP-1600times4/avx2/KeccakP-1600-times4-SIMD256.c:851:6:KeccakP1600times4_PermuteAll_6rounds_avx2` | `build-v35-constrained-budget/src/common/sha3/xkcp_low/CMakeFiles/xkcp_low_keccakp_1600times4_avx2.dir/KeccakP-1600times4/avx2/KeccakP-1600-times4-SIMD256.c.su` |
| 18 | 1064 | static | `/home/home/pqc/liboqs/src/common/sha3/xkcp_low/KeccakP-1600times4/avx2/KeccakP-1600-times4-SIMD256.c:860:6:KeccakP1600times4_PermuteAll_4rounds_avx2` | `build-v35-constrained-budget/src/common/sha3/xkcp_low/CMakeFiles/xkcp_low_keccakp_1600times4_avx2.dir/KeccakP-1600times4/avx2/KeccakP-1600-times4-SIMD256.c.su` |
| 19 | 1032 | static | `/home/home/pqc/liboqs/src/common/sha3/xkcp_low/KeccakP-1600times4/avx2/KeccakP-1600-times4-SIMD256.c:833:6:KeccakP1600times4_PermuteAll_24rounds_avx2` | `build-v35-constrained-budget/src/common/sha3/xkcp_low/CMakeFiles/xkcp_low_keccakp_1600times4_avx2.dir/KeccakP-1600times4/avx2/KeccakP-1600-times4-SIMD256.c.su` |
| 20 | 960 | static | `/home/home/pqc/liboqs/src/common/sha3/xkcp_low/KeccakP-1600times4/avx2/KeccakP-1600-times4-SIMD256.c:869:8:KeccakF1600times4_FastLoop_Absorb_avx2` | `build-v35-constrained-budget/src/common/sha3/xkcp_low/CMakeFiles/xkcp_low_keccakp_1600times4_avx2.dir/KeccakP-1600times4/avx2/KeccakP-1600-times4-SIMD256.c.su` |

## What v35 checks

| Area | Check |
|---|---|
| Workspace budget | ML-KEM, ML-DSA, and combined explicit workspace fit under configured budgets |
| Binary size | static archive and harness binary size are recorded and budget checked |
| Stack usage | compiler `.su` files are scanned and the largest static stack entries are reported |
| Runtime RSS | `/usr/bin/time -v` maximum resident set size is recorded and budget checked |
| Correctness | ML-KEM, ML-DSA, and combined KEM-transcript-signature flows are re-run |

## Claims supported by v35

| Claim | Status |
|---|---|
| optimized explicit workspace fits under the constrained workspace budget | supported if PASS |
| size-focused minimal build remains correct for tested ML-KEM and ML-DSA flows | supported if PASS |
| observed runtime RSS fits under configured host-side constrained-device budget | supported if PASS |
| largest observed static stack-usage entry fits under configured stack budget | supported if PASS |

## Limitations

- v35 is not actual Raspberry Pi validation unless run on Raspberry Pi hardware.
- v35 does not prove constant-time behavior.
- v35 does not prove formal memory safety.
- v35 does not prove thread/TLS safety.
- v35 does not test Rust FFI.
- v35 does not measure energy usage or thermal throttling.

## Next

v36 should perform timing/constant-time-style leakage checks, for example using repeated timing distributions or dudect-style experiments.
