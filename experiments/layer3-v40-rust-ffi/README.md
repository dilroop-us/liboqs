# Layer 3 v40: Rust FFI / Integration Validation

## Goal

v40 validates that Rust can link against the optimized liboqs build and use the optimized ML-KEM/ML-DSA lifecycle-workspace implementation through FFI.

## Optimized build under test

- ML-KEM-768 with v29 lifecycle workspace
- ML-DSA-44 with v24 lifecycle workspace

## What v40 checks

- Rust links against optimized static `liboqs.a`
- Rust declares raw `extern "C"` bindings for selected OQS APIs
- Rust allocates 64-byte aligned caller-owned lifecycle workspaces
- Rust calls lifecycle workspace byte-size and setter functions
- Rust runs ML-KEM keypair/encaps/decaps
- Rust runs ML-DSA keypair/sign/verify
- Rust rejects modified ML-DSA message/signature
- Rust runs combined ML-KEM transcript plus ML-DSA signature flow

## Claims supported

If PASS, v40 supports the claim that the optimized lifecycle-workspace implementation can be driven from a Rust FFI harness for the tested flows.

## Limitations

v40 does not prove:

- full Rust safety
- complete FFI safety
- async/threading safety
- cross-platform support
- real constrained-device readiness
- production readiness

## Next

v41 should build a cleaner Rust workspace ownership/alignment API, reducing raw unsafe FFI usage.
