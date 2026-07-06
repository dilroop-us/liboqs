# Layer 3 v34: ASan/UBSan/Valgrind Memory-Safety Validation

## Goal

Validate the optimized lifecycle-workspace ML-KEM/ML-DSA build under memory-safety tooling.

v34 checks whether representative optimized flows trigger:

- AddressSanitizer findings
- UndefinedBehaviorSanitizer findings
- Valgrind memory errors

## Optimized build under test

- ML-KEM-768 with v29 lifecycle workspace
- ML-DSA-44 with v24 lifecycle workspace

## Important implementation detail

The v34 generated workspace header detects and sets both implementation paths:

- ML-KEM C v29 lifecycle workspace
- ML-KEM X86_64 v29 lifecycle workspace
- ML-DSA C v24 lifecycle workspace
- ML-DSA X86_64 v24 lifecycle workspace

This is required because sanitizer and non-sanitizer builds can take different implementation paths.

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

## Tools

- ASan/UBSan build: `build-v34-asan-ubsan`
- Valgrind debug build: `build-v34-valgrind`

Valgrind is intentionally run on a non-ASan debug binary.

## Final result

Final v34 run:

- ASan/UBSan iterations: 100
- Valgrind iterations: 10
- total rows: 6
- PASS rows: 6
- FAIL rows: 0
- Valgrind: `ERROR SUMMARY: 0 errors`

## Workspace sizes

- ML-KEM-768 v29 lifecycle workspace: 13088 B
- ML-DSA-44 v24 lifecycle workspace: 44064 B
- combined explicit workspace: 57152 B

## Success criteria

v34 passes if:

- ASan/UBSan exits cleanly
- no sanitizer findings appear in the log
- Valgrind exits cleanly
- Valgrind reports `ERROR SUMMARY: 0 errors`
- all harness correctness rows pass

## Claims supported

v34 supports the claim that the optimized lifecycle-workspace implementation did not trigger sanitizer or Valgrind findings under the tested ML-KEM, ML-DSA, and combined KEM-transcript-signature flows.

## Limitations

v34 is not a formal memory-safety proof.

It does not prove:

- constant-time behavior
- thread/TLS safety
- Rust FFI safety
- Raspberry Pi readiness
- production readiness

## Next

v35 should perform constrained-device/Raspberry-Pi-style memory budget validation.
