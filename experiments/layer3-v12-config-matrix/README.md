# Layer 3 v12: Build/Config Matrix Comparison

## Goal

v12 compares safe ML-DSA-44 build configurations to find the best memory/speed tradeoff before manual internal source edits.

## Background

v10 showed that `MLD_CONFIG_REDUCE_RAM` significantly reduced ML-DSA-44 sign/verify stack usage, but made signing slower.

v11 confirmed that reduced-RAM mode switches ML-DSA matrix handling from eager expansion to lazy expansion.

v12 checks whether another safe build configuration gives a better middle ground.

## Variants compared

| Variant | Flags |
|---|---|
| baseline | none |
| reduce_ram | `-DMLD_CONFIG_REDUCE_RAM` |
| serial_fips202 | `-DMLD_CONFIG_SERIAL_FIPS202_ONLY` |
| reduce_ram_serial_fips202 | `-DMLD_CONFIG_REDUCE_RAM -DMLD_CONFIG_SERIAL_FIPS202_ONLY` |

All variants use:

- `OQS_EMBEDDED_BUILD=ON`
- `OQS_USE_OPENSSL=OFF`
- Minimal algorithms:
  - ML-KEM-768
  - ML-DSA-44

## Speed results

| Variant | Operation | Mean time |
|---|---|---:|
| baseline | ML-DSA-44 sign | 81.430 us |
| baseline | ML-DSA-44 verify | 27.863 us |
| reduce_ram | ML-DSA-44 sign | 234.125 us |
| reduce_ram | ML-DSA-44 verify | 41.825 us |
| serial_fips202 | ML-DSA-44 sign | 109.848 us |
| serial_fips202 | ML-DSA-44 verify | 41.486 us |
| reduce_ram_serial_fips202 | ML-DSA-44 sign | 232.746 us |
| reduce_ram_serial_fips202 | ML-DSA-44 verify | 42.100 us |

## Memory results

| Variant | Operation | Peak heap | Peak stack | Peak total |
|---|---|---:|---:|---:|
| baseline | ML-DSA-44 sign | 8236 B | 50904 B | 59224 B |
| baseline | ML-DSA-44 verify | 8236 B | 50888 B | 59208 B |
| reduce_ram | ML-DSA-44 sign | 7628 B | 15440 B | 23152 B |
| reduce_ram | ML-DSA-44 verify | 7628 B | 15440 B | 23152 B |
| serial_fips202 | ML-DSA-44 sign | 7628 B | 47248 B | 54960 B |
| serial_fips202 | ML-DSA-44 verify | 7628 B | 47248 B | 54960 B |
| reduce_ram_serial_fips202 | ML-DSA-44 sign | 7628 B | 15440 B | 23152 B |
| reduce_ram_serial_fips202 | ML-DSA-44 verify | 7628 B | 15440 B | 23152 B |

## Findings

Baseline is the fastest configuration, but has the highest stack usage.

Reduced-RAM gives the best memory reduction:

- stack reduced from 50904 B to 15440 B
- about 69.7% lower stack usage
- total memory reduced from 59224 B to 23152 B
- about 60.9% lower total memory

The tradeoff is speed:

- signing becomes about 2.88x slower
- verification becomes about 1.50x slower

Serial FIPS202 alone is not a strong tradeoff in this build. It only slightly reduces stack usage, but slows sign/verify.

Reduced-RAM + Serial FIPS202 does not reduce memory beyond Reduced-RAM alone.

## Conclusion

v12 did not find a better middle configuration. The two useful choices are:

- baseline for maximum speed
- reduced-RAM for constrained-memory devices

This means the next stage should move to controlled internal implementation experiments.

## Cryptographic boundary

v12 does not change ML-KEM or ML-DSA cryptographic logic. It only compares safe build-time configuration variants.
