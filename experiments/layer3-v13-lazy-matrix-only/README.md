# Layer 3 v13: Experimental Lazy Polyvec Path

## Goal

v13 tests whether the reduced-RAM memory benefit in ML-DSA-44 can be isolated through a smaller internal implementation experiment.

Earlier results showed that reduced-RAM mode lowers stack usage significantly, mainly by switching ML-DSA matrix handling from eager to lazy. This experiment checks whether exposing the lazy polyvec path separately gives a better speed/memory tradeoff.

## Build configuration

All builds use:

- `OQS_EMBEDDED_BUILD=ON`
- `OQS_USE_OPENSSL=OFF`
- Minimal algorithms:
  - ML-KEM-768
  - ML-DSA-44

The experimental build uses:

```text
-DMLD_CONFIG_EXPERIMENTAL_LAZY_MATRIX_ONLY
-DMLD_CONFIG_SERIAL_FIPS202_ONLY
