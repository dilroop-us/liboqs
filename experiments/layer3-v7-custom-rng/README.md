# Layer 3 v7: Embedded Custom RNG Wrapper

## Goal

This experiment makes the embedded liboqs build usable by registering a custom RNG callback with `OQS_randombytes_custom_algorithm()`.

## Build used

- `OQS_EMBEDDED_BUILD=ON`
- `OQS_USE_OPENSSL=OFF`
- Minimal build:
  - ML-KEM-768
  - ML-DSA-44

## Why this matters

In embedded mode, liboqs does not provide the default system RNG. The application or platform must provide a secure random source before using ML-KEM or ML-DSA.

## Test RNG

For this Ubuntu experiment, the custom callback uses Linux `getrandom()`.

For real embedded deployments, this must be replaced with a secure platform RNG, hardware RNG, or properly seeded DRBG.

## Results

Correctness passed:
- ML-KEM-768 shared secrets matched
- ML-DSA-44 signature verified

Speed results, 50,000 iterations:
- ML-KEM-768 keygen: 12.831 us
- ML-KEM-768 encaps: 13.406 us
- ML-KEM-768 decaps: 16.852 us
- ML-DSA-44 keypair: 27.188 us
- ML-DSA-44 sign: 82.037 us
- ML-DSA-44 verify: 27.845 us

Memory results:
- Peak heap: 8236 bytes
- Peak stack: 50968 bytes
- Peak total: 59288 bytes

## Cryptographic boundary

The cryptographic core of ML-KEM and ML-DSA remains unchanged.
