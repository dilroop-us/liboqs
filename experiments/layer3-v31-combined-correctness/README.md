# Layer 3 v31: Combined Correctness Harness

## Goal

Validate the final optimized combined PQC build using:

- ML-KEM-768 with v29 lifecycle workspace
- ML-DSA-44 with v24b lifecycle workspace

v31 is a correctness-validation step. It does not add new stack or workspace optimizations.

## What v31 tests

ML-KEM:

- keypair
- encapsulation
- decapsulation
- shared-secret equality

ML-DSA:

- keypair
- signing
- valid signature verification
- modified message rejection
- modified signature rejection

Combined sequence:

- ML-KEM keypair
- ML-KEM encapsulation
- ML-KEM decapsulation
- shared-secret equality
- ML-DSA keypair
- ML-DSA signing over a transcript
- ML-DSA verification of that transcript

## Important implementation notes

The optimized build is an embedded liboqs build, so v31 registers a custom Linux RNG through `OQS_randombytes_custom_algorithm()`.

The harness also refreshes lifecycle workspace pointers after `OQS_KEM_new()` and `OQS_SIG_new()` so the active runtime-dispatched implementation has explicit workspace pointers set.

## Final result

For 1000 iterations per test group:

- ML-KEM valid flow: 1000 passed, 0 failed
- ML-DSA valid and negative checks: 1000 passed, 0 failed
- combined ML-KEM + ML-DSA sequence: 1000 passed, 0 failed

Total:

- 3000 passed
- 0 failed
- overall status: PASS

## Workspace sizes

- ML-KEM v29 lifecycle workspace: 13088 B
- ML-DSA v24b lifecycle workspace: 44064 B
- combined explicit workspace: 57152 B

## Outputs

Generated files:

- `layer3-results/v31_combined_correctness.csv`
- `layer3-results/v31_combined_workspace.csv`
- `layer3-results/v31_combined_correctness_report.md`
- `layer3-results/v31_build.log`
- `layer3-results/v31_combined_correctness_run.log`
- `layer3-results/v31_lifecycle_symbols.txt`

## Success criteria

v31 passes only if:

- ML-KEM valid flow passes
- ML-DSA valid flow passes
- ML-DSA rejects modified message
- ML-DSA rejects modified signature
- combined ML-KEM + ML-DSA sequence passes
- all tests complete with zero failures

## Limitations

v31 does not prove:

- production readiness
- constant-time behavior
- sanitizer cleanliness
- workspace misuse safety
- threading/TLS safety
- Rust FFI readiness
- Pi readiness

Those belong to later versions.

## Next

v32 should test workspace API misuse cases for both ML-KEM and ML-DSA.
