# Layer 3 v36: Threading/TLS Workspace Validation

## Goal

Validate whether the optimized lifecycle-workspace ML-KEM/ML-DSA implementation works correctly under concurrent thread execution.

v36 focuses on thread-local workspace behavior.

## Optimized build under test

- ML-KEM-768 with v29 lifecycle workspace
- ML-DSA-44 with v24 lifecycle workspace

## What v36 tests

Each worker thread allocates and sets its own caller-owned workspace.

The harness checks:

- single-thread control flow
- multi-thread ML-KEM flow
- multi-thread ML-DSA flow
- multi-thread combined ML-KEM + ML-DSA flow
- repeated workspace setter stress
- workspace guard/canary integrity

## Tested flows

ML-KEM:

- keypair
- encaps
- decaps
- shared-secret equality

ML-DSA:

- keypair
- sign
- verify valid signature
- reject modified message
- reject modified signature

Combined:

- ML-KEM keypair/encaps/decaps
- transcript = ML-KEM public key || ciphertext || shared secret
- ML-DSA sign transcript
- verify transcript
- reject modified transcript/signature

## Success criteria

v36 passes if:

- all threaded correctness flows pass
- worker failure count is zero
- workspace canary failure count is zero
- repeated setter stress passes
- final summary has zero failed rows

## Claims supported

v36 supports the claim that the optimized lifecycle-workspace flows work correctly under concurrent execution when each thread sets and uses its own workspace.

## Limitations

v36 does not prove:

- formal thread safety
- all possible scheduler interleavings
- Rust async safety
- constant-time behavior
- production readiness

## Next

v37 should perform build matrix validation.
