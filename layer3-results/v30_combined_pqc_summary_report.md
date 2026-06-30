# Layer 3 v30: Combined PQC Workspace Summary

## Scope

This report summarizes the completed Layer 3 workspace work for:

- ML-KEM-768
- ML-DSA-44
- combined ML-KEM + ML-DSA constrained build profile

v30 is report-only. It does not introduce a new optimization or change cryptographic code.

## 1. Executive summary

| Scheme | Final version | Main result | Final lifecycle workspace | Workspace saved | Speed impact |
| --- | --- | --- | --- | --- | --- |
| ML-KEM-768 | v29 | IND-CPA stack frames reduced; operation workspaces compacted | 13088 B (12.78 KiB) | 14976 B (53.36%) | near baseline |
| ML-DSA-44 | v24b | keygen/sign/verify stack reduced; lifecycle workspace compacted | 44064 B (43.03 KiB) | 18368 B (29.42%) | near baseline |
| Combined | v30 | combined explicit PQC workspace budget | 57152 B (55.81 KiB) | - | not a new benchmark |

## 2. Version timeline

| Version | Scheme | Purpose | Main output |
| --- | --- | --- | --- |
| v16 | ML-DSA-44 | caller matrix workspace | reduced matrix-heavy signing/verify frames |
| v17b | ML-DSA-44 | full sign workspace | moved signing vectors to caller workspace |
| v19b | ML-DSA-44 | attempt-generation workspace | reduced signing attempt frame |
| v21 | ML-DSA-44 | unified signing workspace | combined sign-side caller workspace API |
| v22b | ML-DSA-44 | verify workspace | verify frame reduced |
| v23b | ML-DSA-44 | keygen/provisioning workspace | keypair and pk_from_sk frames reduced |
| v24b | ML-DSA-44 | compact lifecycle workspace | 62432 B separate to 44064 B lifecycle |
| v25a | ML-KEM-768 | stack/lifetime analysis | identified enc/keypair/dec hotspots |
| v25b | ML-KEM-768 | baseline profiler | baseline speed and size before ML-KEM changes |
| v26 | ML-KEM-768 | encapsulation workspace | indcpa_enc reduced |
| v27 | ML-KEM-768 | keypair workspace | indcpa_keypair_derand reduced |
| v28 | ML-KEM-768 | decapsulation workspace | indcpa_dec reduced |
| v29 | ML-KEM-768 | compact lifecycle workspace | 28064 B separate to 13088 B lifecycle |
| v30 | Combined | summary report | combined evidence pack |

## 3. ML-KEM stack reduction

| Variant | Function | Baseline stack | Final stack | Saved | Reduction | Version |
| --- | --- | --- | --- | --- | --- | --- |
| x86_64 | `indcpa_enc` | 13312 B | 192 B | 13120 B | 98.56% | v26/v29 |
| ref | `indcpa_enc` | 13312 B | 160 B | 13152 B | 98.80% | v26/v29 |
| x86_64 | `indcpa_keypair_derand` | 10336 B | 192 B | 10144 B | 98.14% | v27/v29 |
| ref | `indcpa_keypair_derand` | 10336 B | 128 B | 10208 B | 98.76% | v27/v29 |
| x86_64 | `indcpa_dec` | 4992 B | 80 B | 4912 B | 98.40% | v28/v29 |
| ref | `indcpa_dec` | 4992 B | 80 B | 4912 B | 98.40% | v28/v29 |

## 4. ML-KEM workspace compaction

| Workspace item | Bytes | KiB | Role |
| --- | --- | --- | --- |
| v26_enc_workspace | 13088 | 12.78 | encapsulation workspace |
| v27_keypair_workspace | 10112 | 9.88 | keypair workspace |
| v28_dec_workspace | 4864 | 4.75 | decapsulation workspace |
| separate total | 28064 | 27.41 | sum before lifecycle compaction |
| v29 lifecycle workspace | 13088 | 12.78 | compact reusable lifecycle workspace |
| saved | 14976 | 14.62 | 53.36% saved |

## 5. ML-KEM speed

| Operation | v25b baseline us | v29 final us | Delta us | Delta % | Correctness OK |
| --- | --- | --- | --- | --- | --- |
| kem-keypair | 12.651 | 12.767 | 0.116 | 0.92% | 1 |
| kem-encaps | 13.357 | 13.319 | -0.038 | -0.28% | 1 |
| kem-decaps | 16.812 | 16.817 | 0.005 | 0.03% | 1 |

## 6. ML-DSA stack reduction

| Variant | Function | Baseline/milestone stack | Final stack | Saved | Reduction | Version |
| --- | --- | --- | --- | --- | --- | --- |
| ref/x86_64 | `signature_internal` | 44624 B | 15584 B | 29040 B | 65.08% | v17b milestone |
| ref/x86_64 | `mld_attempt_signature_generation` | 15584 B | 544 B | 15040 B | 96.51% | v19b milestone |
| ref/x86_64 | `mld_sign_verify_internal` | 8256 B | 192 B | 8064 B | 97.67% | v22b |
| ref/x86_64 | `keypair_internal` | 8640 B | 160 B | 8480 B | 98.15% | v23b |
| ref/x86_64 | `pk_from_sk` | 10176 B | 96 B | 10080 B | 99.06% | v23b |

### ML-DSA high-level lifecycle stack proxy

| Metric | Bytes | KiB |
| --- | --- | --- |
| baseline high-level total | 88080 | 86.02 |
| final high-level total | 992 | 0.97 |
| saved | 87088 | 85.05 |
| saved % | 98.87% | - |

## 7. ML-DSA workspace compaction

| Workspace item | Bytes | KiB | Role |
| --- | --- | --- | --- |
| sign workspace | 44064 | 43.03 | signing lifecycle workspace |
| verify workspace | 8128 | 7.94 | verification workspace |
| keygen workspace | 10240 | 10.00 | keypair/provisioning workspace |
| separate total | 62432 | 60.97 | sum before lifecycle compaction |
| v24b lifecycle workspace | 44064 | 43.03 | compact reusable lifecycle workspace |
| saved | 18368 | 17.94 | 29.42% saved |

## 8. ML-DSA speed

| Operation | Baseline us | Final lifecycle us | Delta us | Delta % | Correctness OK |
| --- | --- | --- | --- | --- | --- |
| sig-keypair | 27.188 | 26.854 | -0.334 | -1.23% | 1 |
| sig-sign | 82.037 | 80.368 | -1.669 | -2.03% | 1 |
| sig-verify | 27.845 | 27.391 | -0.454 | -1.63% | 1 |

## 9. Combined PQC workspace budget

| Scheme | Lifecycle workspace bytes | KiB |
| --- | --- | --- |
| ML-KEM-768 | 13088 | 12.78 |
| ML-DSA-44 | 44064 | 43.03 |
| Combined total | 57152 | 55.81 |

This combined total is the explicit caller-provided workspace budget for a backend that keeps one ML-KEM lifecycle workspace and one ML-DSA lifecycle workspace. v30 does not claim cross-scheme workspace unioning.

## 10. Combined build profile

| Setting | Value |
| --- | --- |
| KEM | ML-KEM-768 |
| SIG | ML-DSA-44 |
| OQS_MINIMAL_BUILD | `KEM_ml_kem_768;SIG_ml_dsa_44` |
| OQS_EMBEDDED_BUILD | ON |
| OQS_USE_OPENSSL | OFF |
| ML-KEM workspace | v29 compact lifecycle workspace |
| ML-DSA workspace | v24b compact lifecycle workspace |
| Target use | desktop validation first, Rust backend next, Pi later |

## 11. Binary / section size snapshot

| Profile | text | data | bss | dec | hex | Binary |
| --- | --- | --- | --- | --- | --- | --- |
| v29_lifecycle_workspace | 536054 | 4976 | 280 | 541310 | 8427e | `/home/home/pqc/liboqs/layer3-results/v29_mlkem_lifecycle_workspace_profiler` |

## 12. Correctness summary

| Scheme | Operation group | Status | Depth |
| --- | --- | --- | --- |
| ML-KEM-768 | keypair / encaps / decaps | passed | smoke correctness in v29 |
| ML-DSA-44 | keypair / sign / verify | passed | smoke correctness in v24b |
| Combined | same minimal build profile | not deeply tested yet | planned for v31 |
| Negative tests | corruption / misuse / differential | not part of v30 | planned for v31-v34 |

## 13. Claims and evidence

| Claim | Evidence | Status |
| --- | --- | --- |
| ML-KEM stack hotspots reduced | indcpa_enc/keypair/dec stack tables | supported |
| ML-KEM workspace compacted | 28064 B to 13088 B | supported |
| ML-DSA high-stack lifecycle reduced | v16-v23b stack milestones | supported |
| ML-DSA workspace compacted | 62432 B to 44064 B | supported |
| Combined explicit workspace known | 57152 B total | supported |
| Speed stayed near baseline | ML-KEM and ML-DSA speed deltas | supported |
| Cryptographic behavior unchanged | storage/layout-only patches; smoke correctness passed | partially supported |
| Production readiness | requires v31-v39 validation | not claimed |

## 14. Limitations

- v30 is a summary report, not a new test run.
- v30 does not prove constant-time behavior.
- v30 does not prove production readiness.
- v30 does not include Rust FFI testing.
- v30 does not include Pi or constrained-device runtime testing.
- Deeper correctness, misuse, sanitizer, threading, build-matrix, and differential tests remain for v31-v39.

## 15. Next work

| Version | Next task |
| --- | --- |
| v31 | combined correctness harness for ML-KEM + ML-DSA |
| v32 | workspace API misuse tests for both schemes |
| v33 | baseline-vs-optimized differential tests |
| v34 | sanitizer and memory-safety validation |
| v35 | threading/TLS validation |
| v36 | build matrix validation |
| v37 | final memory accounting report |
| v38 | code hygiene and cleanup |
| v39 | cross-compile dry run |
| v40 | Rust backend integration starts |

