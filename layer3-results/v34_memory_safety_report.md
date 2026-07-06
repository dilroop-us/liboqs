# Layer 3 v34: ASan/UBSan/Valgrind Memory-Safety Validation

## Scope

v34 checks whether the optimized lifecycle-workspace build triggers sanitizer or Valgrind findings under representative ML-KEM, ML-DSA, and combined protocol-like flows.

The optimized build uses:

- ML-KEM-768 with v29 lifecycle workspace
- ML-DSA-44 with v24 lifecycle workspace

v34 does not add a new optimization. It validates memory-safety behavior of the existing optimized implementation.

## Workspace sizes

| Scheme | Bytes | KiB |
|---|---:|---:|
| ML-KEM-768 | 13088 | 12.78 |
| ML-DSA-44 | 44064 | 43.03 |
| Combined | 57152 | 55.81 |

## Summary

| Metric | Value |
|---|---:|
| total rows | 6 |
| PASS rows | 6 |
| FAIL rows | 0 |
| overall v34 status | PASS |

## Tool results

| Tool | Case | Iterations | Passed | Failed | Status | Notes |
|---|---|---:|---:|---:|---|---|
| ASan+UBSan | mlkem_valid_flow | 100 | 100 | 0 | PASS | clean |
| ASan+UBSan | mldsa_valid_and_negative | 100 | 100 | 0 | PASS | clean |
| ASan+UBSan | combined_mlkem_mldsa_sequence | 100 | 100 | 0 | PASS | clean |
| Valgrind | mlkem_valid_flow | 10 | 10 | 0 | PASS | clean |
| Valgrind | mldsa_valid_and_negative | 10 | 10 | 0 | PASS | clean |
| Valgrind | combined_mlkem_mldsa_sequence | 10 | 10 | 0 | PASS | clean |

## Valgrind summary

```text
ERROR SUMMARY: 0 errors from 0 contexts (suppressed: 0 from 0)
```

## What v34 checks

| Area | Check |
|---|---|
| ASan | invalid reads/writes, use-after-free, double free, heap buffer overflow |
| UBSan | undefined behavior such as invalid shifts, alignment issues, integer UB where instrumented |
| Valgrind | invalid memory access, uninitialized-value use, definite/possible leaks, runtime memory errors |
| ML-KEM flow | keypair, encaps, decaps, shared-secret equality |
| ML-DSA flow | keypair, sign, verify, reject modified message, reject modified signature |
| Combined flow | KEM transcript construction, ML-DSA signing, verification, negative transcript/signature checks |

## Claims supported by v34

| Claim | Status |
|---|---|
| optimized ML-KEM lifecycle-workspace flow produced no sanitizer findings in this harness | supported if PASS |
| optimized ML-DSA lifecycle-workspace flow produced no sanitizer findings in this harness | supported if PASS |
| optimized combined KEM transcript plus DSA signature flow produced no sanitizer findings in this harness | supported if PASS |
| Valgrind reported zero runtime memory errors for the tested flows | supported if PASS |

## Limitations

- v34 is not a formal memory-safety proof.
- v34 does not prove constant-time behavior.
- v34 does not prove thread/TLS safety.
- v34 does not test Rust FFI.
- v34 does not test Raspberry Pi or constrained-device behavior.
- Valgrind coverage is slower and uses fewer iterations than ASan/UBSan.

## Next

v35 should perform constrained-device/Raspberry-Pi-style memory budget validation.
