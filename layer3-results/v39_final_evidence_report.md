# Layer 3 v39: Final Evidence / Memory-Accounting Report

## Scope

v39 consolidates the Layer 3 validation evidence for the optimized lifecycle-workspace implementation of:

- ML-KEM-768 with v29 lifecycle workspace
- ML-DSA-44 with v24 lifecycle workspace

This report ties together v31 through v38 and records the empirical claims supported by the validation chain.

v39 does not run a new cryptographic primitive test. It is an evidence, accounting, and claims-boundary report.

## Repository state

| Metric | Value |
|---|---|
| branch | `experiments` |
| HEAD | `02e5953a` |
| working tree status | `M .gitignore
?? experiments/layer3-v39-final-evidence/` |

## Final summary

| Metric | Value |
|---|---:|
| evidence layers checked | 8 |
| clean PASS layers | 8 |
| PASS with timing flags | 0 |
| missing reports | 0 |
| unknown/check reports | 0 |
| final v39 status | PASS |

## Memory accounting

| Item | Bytes | KiB |
|---|---:|---:|
| ML-KEM-768 lifecycle workspace | 13088 | 12.78 |
| ML-DSA-44 lifecycle workspace | 44064 | 43.03 |
| Combined explicit workspace | 57152 | 55.81 |

## Evidence chain

| Layer | Title | Status | Evidence report | Supported claim |
|---|---|---|---|---|
| v31 | Optimized correctness | PASS | `layer3-results/v31_combined_correctness_report.md` | Optimized ML-KEM-768, ML-DSA-44, and combined flow correctness passed in the tested harness. |
| v32 | Workspace misuse / guard validation | PASS | `layer3-results/v32_workspace_misuse_report.md` | Workspace guard/misuse checks passed for tested misuse scenarios. |
| v33 | Baseline-vs-optimized differential compatibility | PASS | `layer3-results/v33_differential_report.md` | Baseline and optimized builds were interoperable for tested ML-KEM, ML-DSA, and combined flows. |
| v34 | Memory-safety validation | PASS | `layer3-results/v34_memory_safety_report.md` | ASan/UBSan and Valgrind found no issues in the tested optimized flows. |
| v35 | Constrained-device / memory-budget validation | PASS | `layer3-results/v35_constrained_budget_report.md` | Optimized build fit within the selected 64 KiB combined explicit workspace budget while preserving correctness. |
| v36 | Threading / TLS workspace validation | PASS | `layer3-results/v36_threading_tls_report.md` | Concurrent ML-KEM, ML-DSA, and combined flows passed with independent thread workspaces. |
| v37 | Build matrix validation | PASS | `layer3-results/v37_build_matrix_report.md` | Selected build configurations exposed required lifecycle symbols and passed core correctness checks. |
| v38 | Timing / constant-time-style leakage validation | PASS_NO_FLAGS | `layer3-results/v38_timing_leakage_report.md` | Selected timing classes produced no timing flags under the configured Welch t-threshold. |

## Claims supported by v31-v38

If all evidence rows are PASS/PASS_NO_FLAGS, the Layer 3 validation chain supports the following empirical claim:

> Across v31-v38, the optimized ML-KEM-768 and ML-DSA-44 lifecycle-workspace implementation passed correctness, workspace misuse/guard, baseline differential compatibility, sanitizer/memory-safety, constrained-budget, threading/TLS, selected build-matrix, and selected timing-distribution validation.

More specifically:

- v31 supports optimized correctness for the tested ML-KEM, ML-DSA, and combined flows.
- v32 supports tested workspace misuse/guard behavior.
- v33 supports baseline-vs-optimized differential compatibility for tested flows.
- v34 supports sanitizer and Valgrind memory-safety evidence for tested flows.
- v35 supports the 64 KiB combined explicit workspace budget claim under host-side constrained-device-style testing.
- v36 supports concurrent execution with independent caller-owned workspaces.
- v37 supports selected build-profile portability across Release, RelWithDebInfo, Debug, and size-focused static builds.
- v38 supports statistical timing-distribution evidence with no timing flags in the selected timing classes.

## Claims not supported

This validation package does not prove:

- formal correctness
- formal memory safety
- formal constant-time behavior
- power, EM, cache, branch-predictor, or microarchitectural side-channel resistance
- all compiler, OS, CPU, architecture, or CMake configuration portability
- Rust FFI safety
- Raspberry Pi hardware readiness unless separately tested on Pi hardware
- production readiness

## Evidence artifact hashes

| Layer | Report | SHA-256 |
|---|---|---|
| v31 | `layer3-results/v31_combined_correctness_report.md` | `c2bcad77c41259f2bd54d27a2a0bf5a70e1603cf5e97f027d0844cae5bc2c533` |
| v32 | `layer3-results/v32_workspace_misuse_report.md` | `3cdf23dd82f255297ec414b5472c3a7b5cccb6b549fe3d0e857c95e3e2727041` |
| v33 | `layer3-results/v33_differential_report.md` | `89cd712c4bd66729dcaee6bb8afa67a2bd60b86f4f24a078d50b9c4d2e7d921d` |
| v34 | `layer3-results/v34_memory_safety_report.md` | `65ff7ec4911b074988eb43c0d3cf100f8e6cd8ec18c06c5a78ca056e77522081` |
| v35 | `layer3-results/v35_constrained_budget_report.md` | `b3d061e9c645ecc907b5502ac708e505beea3dba449d0710793df94c263503de` |
| v36 | `layer3-results/v36_threading_tls_report.md` | `9b5bffee57feaf61f833e6227912b002d3c16eab20240906195b55118a736a7d` |
| v37 | `layer3-results/v37_build_matrix_report.md` | `1b38b7c1e2fd83801b51e4897a8192efd6ca0a4135fe0d6382fc2f303b200124` |
| v38 | `layer3-results/v38_timing_leakage_report.md` | `cf99d32cdd3af8903b141ba181c0b97e7964b85119b6a26ff589ec34e43d75ad` |

## Layer-specific limitations

| Layer | Limitation |
|---|---|
| v31 | Empirical correctness testing only; not a formal proof. |
| v32 | Does not prove every misuse pattern or memory-safety property. |
| v33 | Does not prove equivalence for all possible inputs or configurations. |
| v34 | Does not prove formal memory safety. |
| v35 | Host-side constrained-device-style evidence; not a real hardware deployment proof. |
| v36 | Does not prove all scheduler interleavings or Rust async/threading safety. |
| v37 | Does not test every compiler, architecture, OS, or CMake option. |
| v38 | Statistical timing evidence only; not a formal constant-time or side-channel proof. |

## Recent git log

```text
02e5953a Add Layer 3 v38 timing leakage validation
c08bd8fc Add Layer 3 v37 build matrix validation
dc2f297d Add Layer 3 v36 threading TLS validation
8c6bbb99 Add Layer 3 v35 constrained-device budget validation
befa5067 Add Layer 3 v34 memory-safety validation
f71edffe Add Layer 3 v33 differential compatibility tests
c6d92eeb Add Layer 3 v32 workspace misuse tests
9c8a501c Add Layer 3 v31 combined correctness harness
8a1ee127 Add Layer 3 v30 combined PQC summary
39eabad8 Add Layer 3 v29 ML-KEM lifecycle workspace
1f691037 Add Layer 3 v28 ML-KEM decapsulation workspace
6560364c Add Layer 3 v27 ML-KEM keypair workspace
```

## Recommended next step

After v39, the next useful validation target is Rust FFI / integration validation, because v31-v39 are C/liboqs-side evidence. A later step can also run real Raspberry Pi hardware validation if Pi readiness is a goal.
