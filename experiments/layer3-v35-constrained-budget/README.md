# Layer 3 v35: Constrained-Device Memory Budget Validation

## Goal

Validate whether the optimized lifecycle-workspace ML-KEM/ML-DSA build fits within constrained-device-style memory and size budgets.

v35 is a host-side Raspberry-Pi-style validation step. It does not claim actual Raspberry Pi validation unless the harness is run on Raspberry Pi hardware.

## Optimized build under test

- ML-KEM-768 with v29 lifecycle workspace
- ML-DSA-44 with v24 lifecycle workspace

## What v35 measures

- explicit workspace size
- static archive size
- harness binary size
- `.text`, `.data`, `.bss`, and total binary section size
- compiler static stack-usage entries from `.su` files
- runtime maximum resident set size using `/usr/bin/time -v`
- correctness of ML-KEM, ML-DSA, and combined flows

## Important implementation detail

The generated v35 workspace header detects and sets both implementation paths:

- ML-KEM C v29 lifecycle workspace
- ML-KEM X86_64 v29 lifecycle workspace
- ML-DSA C v24 lifecycle workspace
- ML-DSA X86_64 v24 lifecycle workspace

This avoids false failures when different builds choose different implementation paths.

## Default budgets

- ML-KEM workspace: 16 KiB
- ML-DSA workspace: 48 KiB
- combined explicit workspace: 64 KiB
- liboqs archive size: 8 MiB
- harness binary size: 16 MiB
- max RSS: 128 MiB
- max static stack-usage entry: 64 KiB

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

v35 passes if:

- ML-KEM workspace fits the configured budget
- ML-DSA workspace fits the configured budget
- combined workspace fits the configured budget
- binary/resource metrics fit configured budgets
- stack-usage scan fits configured budget
- all correctness flows pass

## Limitations

v35 does not prove:

- actual Raspberry Pi readiness unless run on Raspberry Pi hardware
- constant-time behavior
- formal memory safety
- thread/TLS safety
- Rust FFI safety
- production readiness

## Next

v36 should perform timing/constant-time-style leakage checks.
