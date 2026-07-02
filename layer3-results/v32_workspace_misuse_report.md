# Layer 3 v32: Workspace API Misuse Tests

## Scope

v32 tests caller-side workspace misuse behavior for the final optimized PQC build:

- ML-KEM-768 with v29 lifecycle workspace
- ML-DSA-44 with v24 lifecycle workspace
- combined ML-KEM + ML-DSA workspace setup

v32 does not add a new optimization. It validates wrapper-level misuse handling and documents raw setter misuse behavior in isolated child processes.

## Workspace sizes

| Scheme | Bytes | KiB |
|---|---:|---:|
| ML-KEM-768 | 13088 | 12.78 |
| ML-DSA-44 | 44064 | 43.03 |
| Combined | 57152 | 55.81 |

## Summary

| Metric | Value |
|---|---:|
| total rows | 29 |
| safe wrapper rows | 19 |
| raw child observation rows | 10 |
| PASS rows | 19 |
| FAIL rows | 0 |
| DOCUMENTED rows | 10 |
| safe wrapper failures | 0 |
| overall v32 status | PASS |

## Safe wrapper tests

| Test | Scheme | Expected | Observed | Iterations | Passed | Failed | Status | Notes |
|---|---|---|---|---:|---:|---:|---|---|
| mlkem_null_wrapper | ML-KEM | reject | rejected | 1 | 1 | 0 | PASS | NULL rejected before raw setter |
| mldsa_null_wrapper | ML-DSA | reject | rejected | 1 | 1 | 0 | PASS | NULL rejected before raw setter |
| mlkem_size_0_wrapper | ML-KEM | reject | rejected | 1 | 1 | 0 | PASS | capacity 0 rejected |
| mlkem_size_1_wrapper | ML-KEM | reject | rejected | 1 | 1 | 0 | PASS | capacity 1 rejected |
| mlkem_size_half_wrapper | ML-KEM | reject | rejected | 1 | 1 | 0 | PASS | half capacity rejected |
| mlkem_size_minus1_wrapper | ML-KEM | reject | rejected | 1 | 1 | 0 | PASS | required minus one rejected |
| mldsa_size_0_wrapper | ML-DSA | reject | rejected | 1 | 1 | 0 | PASS | capacity 0 rejected |
| mldsa_size_1_wrapper | ML-DSA | reject | rejected | 1 | 1 | 0 | PASS | capacity 1 rejected |
| mldsa_size_half_wrapper | ML-DSA | reject | rejected | 1 | 1 | 0 | PASS | half capacity rejected |
| mldsa_size_minus1_wrapper | ML-DSA | reject | rejected | 1 | 1 | 0 | PASS | required minus one rejected |
| mlkem_misaligned_wrapper | ML-KEM | reject | rejected | 1 | 1 | 0 | PASS | misaligned pointer rejected |
| mldsa_misaligned_wrapper | ML-DSA | reject | rejected | 1 | 1 | 0 | PASS | misaligned pointer rejected |
| mlkem_exact_wrapper | ML-KEM | pass | passed | 100 | 100 | 0 | PASS | exact required capacity |
| mldsa_exact_wrapper | ML-DSA | pass | passed | 100 | 100 | 0 | PASS | exact required capacity |
| mlkem_larger_wrapper | ML-KEM | pass | passed | 100 | 100 | 0 | PASS | required plus 4096 capacity |
| mldsa_larger_wrapper | ML-DSA | pass | passed | 100 | 100 | 0 | PASS | required plus 4096 capacity |
| mlkem_replace_workspace | ML-KEM | pass | passed | 200 | 200 | 0 | PASS | set workspace A then workspace B |
| mldsa_replace_workspace | ML-DSA | pass | passed | 200 | 200 | 0 | PASS | set workspace A then workspace B |
| combined_valid_wrapper | Combined | pass | passed | 100 | 100 | 0 | PASS | both lifecycle workspaces valid |

## Raw setter child-process observations

| Test | Scheme | Expected | Observed | Status | Notes |
|---|---|---|---|---|---|
| mlkem_no_workspace | ML-KEM | record_result | exit_1 | DOCUMENTED | fresh child without ML-KEM workspace |
| mldsa_no_workspace | ML-DSA | record_result | exit_1 | DOCUMENTED | fresh child without ML-DSA workspace |
| combined_only_mlkem_set | Combined | record_result | exit_1 | DOCUMENTED | ML-KEM set; ML-DSA missing |
| combined_only_mldsa_set | Combined | record_result | exit_1 | DOCUMENTED | ML-DSA set; ML-KEM missing |
| mlkem_raw_null | ML-KEM | record_result | exit_1 | DOCUMENTED | raw setter with NULL |
| mldsa_raw_null | ML-DSA | record_result | exit_1 | DOCUMENTED | raw setter with NULL |
| mlkem_raw_too_small | ML-KEM | record_result | exit_1 | DOCUMENTED | raw setter with 64-byte allocation |
| mldsa_raw_too_small | ML-DSA | record_result | exit_1 | DOCUMENTED | raw setter with 64-byte allocation |
| mlkem_raw_misaligned | ML-KEM | record_result | exit_1 | DOCUMENTED | raw setter with pointer + 1 |
| mldsa_raw_misaligned | ML-DSA | record_result | exit_1 | DOCUMENTED | raw setter with pointer + 1 |

## Interpretation

- Safe wrapper tests are expected to pass or reject invalid inputs cleanly.
- Raw setter misuse tests are documented observations because raw experimental setters do not carry size or alignment metadata.
- Raw setters should not be exposed directly to the future Rust backend.
- Rust integration should use a typed wrapper/shim that enforces non-NULL, minimum capacity, and alignment before calling raw setters.

## Claims supported by v32

| Claim | Status |
|---|---|
| NULL workspace can be rejected at wrapper layer | supported if PASS |
| too-small workspace can be rejected at wrapper layer | supported if PASS |
| misaligned workspace can be rejected at wrapper layer | supported if PASS |
| exact-size workspace works | supported if PASS |
| larger-than-needed workspace works | supported if PASS |
| workspace replacement works | supported if PASS |
| raw setter misuse behavior is isolated from main test process | documented |

## Limitations

- v32 is not a sanitizer run.
- v32 does not prove memory safety.
- v32 does not prove constant-time behavior.
- v32 does not prove Rust FFI safety yet.
- Raw setter misuse observations are not production guarantees.

## Next

v33 should perform baseline-vs-optimized differential testing.
