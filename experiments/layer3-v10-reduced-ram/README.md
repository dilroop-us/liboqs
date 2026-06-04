# Layer 3 v10: Reduced-RAM / Workspace Comparison

## Goal

v10 compares the current embedded ML-KEM-768 / ML-DSA-44 build against a reduced-RAM ML-DSA configuration.

## Why this matters

v8 identified ML-DSA-44 sign and verify as the highest memory-pressure operations. v9 mapped those hotspots to ML-DSA signing/verification internals, eager matrix expansion, polynomial sampling, and temporary vector storage.

v10 tests whether the implementation's reduced-RAM configuration can reduce memory pressure without changing ML-DSA parameters or cryptographic logic.

## Builds compared

### Baseline embedded build

- `OQS_EMBEDDED_BUILD=ON`
- `OQS_USE_OPENSSL=OFF`
- Minimal build:
  - ML-KEM-768
  - ML-DSA-44

### Reduced-RAM embedded build

- `OQS_EMBEDDED_BUILD=ON`
- `OQS_USE_OPENSSL=OFF`
- Minimal build:
  - ML-KEM-768
  - ML-DSA-44
- Additional C flag:
  - `-DMLD_CONFIG_REDUCE_RAM`

## Correctness

Both baseline and reduced-RAM builds passed ML-DSA-44 sign/verify correctness checks.

## Speed results

| Profile | Operation | Mean time |
|---|---|---:|
| Baseline | ML-DSA-44 sign | 81.799 us |
| Baseline | ML-DSA-44 verify | 27.971 us |
| Reduced-RAM | ML-DSA-44 sign | 236.170 us |
| Reduced-RAM | ML-DSA-44 verify | 41.803 us |

## Memory results

| Profile | Operation | Peak heap | Peak stack | Peak total |
|---|---|---:|---:|---:|
| Baseline | ML-DSA-44 sign | 8236 B | 50904 B | 59224 B |
| Baseline | ML-DSA-44 verify | 8236 B | 50904 B | 59224 B |
| Reduced-RAM | ML-DSA-44 sign | 7628 B | 15456 B | 23168 B |
| Reduced-RAM | ML-DSA-44 verify | 7628 B | 15456 B | 23168 B |

## Result

Reduced-RAM mode reduced ML-DSA-44 sign/verify stack usage from 50904 bytes to 15456 bytes.

That is about 69.6% lower stack usage.

Total memory reduced from 59224 bytes to 23168 bytes.

That is about 60.9% lower total memory.

The tradeoff is runtime overhead:

- ML-DSA-44 signing became about 2.89x slower.
- ML-DSA-44 verification became about 1.49x slower.

## Conclusion

Reduced-RAM mode is useful for constrained devices where stack/RAM is more important than maximum signing speed.

## Cryptographic boundary

v10 does not change ML-KEM or ML-DSA parameters, ciphertext formats, signature formats, sampling rules, or verification logic. It only compares an implementation-level memory configuration.
