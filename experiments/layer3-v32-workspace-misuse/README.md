# Layer 3 v32: Workspace API Misuse Tests

## Goal

Test caller-side workspace misuse behavior for the final optimized PQC build using:

- ML-KEM-768 with v29 lifecycle workspace
- ML-DSA-44 with v24 lifecycle workspace

v32 does not add a new optimization. It validates safe wrapper behavior and documents raw setter misuse behavior.

## What v32 tests

Safe wrapper tests:

- NULL workspace rejection
- too-small workspace rejection
- misaligned workspace rejection
- exact-size workspace acceptance
- larger-than-needed workspace acceptance
- workspace replacement
- valid combined ML-KEM + ML-DSA setup

Raw child-process observations:

- operation without workspace
- partial combined setup
- raw setter with NULL
- raw setter with too-small allocation
- raw setter with misaligned pointer

## Final result

For 100 iterations in valid-flow wrapper tests:

- safe wrapper rows: 19
- raw child observation rows: 10
- PASS rows: 19
- FAIL rows: 0
- DOCUMENTED rows: 10
- safe wrapper failures: 0
- overall status: PASS

## Workspace sizes

- ML-KEM v29 lifecycle workspace: 13088 B
- ML-DSA v24 lifecycle workspace: 44064 B
- combined explicit workspace: 57152 B

## Important interpretation

The raw experimental workspace setters do not know the allocation size or alignment by themselves.

Therefore, raw misuse tests are run in isolated child processes and recorded as observations.

The future Rust backend should not call raw setters directly. It should call a C shim or Rust wrapper that validates:

- non-NULL pointer
- minimum capacity
- required alignment
- correct scheme type

## Outputs

Generated files:

- `layer3-results/v32_workspace_misuse.csv`
- `layer3-results/v32_workspace_misuse_report.md`
- `layer3-results/v32_workspace_misuse_run.log`
- `layer3-results/v32_build.log`
- `layer3-results/v32_lifecycle_symbols.txt`

## Success criteria

v32 passes if:

- safe wrapper rejects invalid workspace inputs
- exact-size and larger workspace inputs pass
- workspace replacement passes
- valid combined setup passes
- raw misuse cases are isolated and documented
- main test process completes without crashing

## Limitations

v32 does not prove:

- production readiness
- constant-time behavior
- sanitizer cleanliness
- Rust FFI safety
- Pi readiness

Those belong to later versions.

## Next

v33 should perform baseline-vs-optimized differential tests.
