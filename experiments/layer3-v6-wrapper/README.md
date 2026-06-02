# Layer 3 v6: Custom liboqs Wrapper Benchmark

This experiment calls ML-KEM-768 and ML-DSA-44 directly through the public liboqs C API.

## Build used

- Minimal liboqs build
- OQS_USE_OPENSSL=OFF
- ML-KEM-768
- ML-DSA-44

## Purpose

- Benchmark outside liboqs test binaries
- Measure key, ciphertext, and signature sizes
- Prepare for static-buffer, no-heap, and embedded wrapper experiments

## Results

ML-KEM-768:
- public key: 1184 bytes
- secret key: 2400 bytes
- ciphertext: 1088 bytes
- shared secret: 32 bytes

ML-DSA-44:
- public key: 1312 bytes
- secret key: 2560 bytes
- signature: 2420 bytes

## Cryptographic boundary

The cryptographic core of ML-KEM and ML-DSA remains unchanged.
