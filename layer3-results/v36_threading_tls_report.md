# Layer 3 v36: Threading/TLS Workspace Validation

## Scope

v36 validates whether the optimized lifecycle-workspace implementation works under concurrent thread execution.

Each worker thread allocates its own caller-owned ML-KEM and/or ML-DSA workspace, sets the lifecycle workspace pointer inside that thread, and then runs optimized cryptographic flows concurrently.

The optimized build uses:

- ML-KEM-768 with v29 lifecycle workspace
- ML-DSA-44 with v24 lifecycle workspace

## Configuration

| Metric | Value |
|---|---:|
| threads | 8 |
| iterations per thread | 100 |

## Workspace sizes

| Scheme | Bytes | KiB |
|---|---:|---:|
| ML-KEM-768 | 13088 | 12.78 |
| ML-DSA-44 | 44064 | 43.03 |
| Combined | 57152 | 55.81 |

## Summary

| Metric | Value |
|---|---:|
| total rows | 5 |
| PASS rows | 5 |
| FAIL rows | 0 |
| overall v36 status | PASS |

## Threading/TLS results

| Case | Threads | Iterations/thread | Total ops | Passed ops | Worker failures | Canary failures | Status | Notes |
|---|---:|---:|---:|---:|---:|---:|---|---|
| single_thread_control | 1 | 100 | 100 | 100 | 0 | 0 | PASS | thread-local workspace |
| multi_thread_mlkem | 8 | 100 | 800 | 800 | 0 | 0 | PASS | thread-local workspace |
| multi_thread_mldsa | 8 | 100 | 800 | 800 | 0 | 0 | PASS | thread-local workspace |
| multi_thread_combined | 8 | 100 | 800 | 800 | 0 | 0 | PASS | thread-local workspace |
| thread_repeated_setter_stress | 8 | 100 | 800 | 800 | 0 | 0 | PASS | repeated setter stress |

## What v36 checks

| Area | Check |
|---|---|
| Thread-local workspace setup | each thread sets its own ML-KEM and/or ML-DSA lifecycle workspace |
| ML-KEM concurrency | concurrent keypair, encaps, decaps, shared-secret equality |
| ML-DSA concurrency | concurrent keypair, sign, verify, reject modified message/signature |
| Combined concurrency | concurrent KEM transcript construction and ML-DSA signature verification |
| Repeated setter stress | each worker repeatedly re-sets workspace pointers before operations |
| Canary integrity | guard regions before and after each workspace are checked for corruption |

## Claims supported by v36

| Claim | Status |
|---|---|
| optimized lifecycle-workspace flows work under concurrent execution when each thread sets its own workspace | supported if PASS |
| ML-KEM and ML-DSA workspaces showed no guard/canary corruption in this harness | supported if PASS |
| repeated workspace setter calls did not break correctness in this threaded harness | supported if PASS |

## Limitations

- v36 is not a formal proof of thread safety.
- v36 does not prove all possible scheduler interleavings.
- v36 does not use ThreadSanitizer.
- v36 does not prove Rust async safety.
- v36 does not prove constant-time behavior.
- v36 does not prove production readiness.

## Next

v37 should perform build matrix validation across selected compiler/build configurations.
