# Layer 3 v17a: ML-DSA Lifetime Map

## Goal

Map the approximate lifetime of large temporary objects inside ML-DSA-44 signing and verification.

v17a is analysis only. It does not change cryptographic code.

## Reason

After v16, the matrix workspace is caller-provided and BSS stays low. However, `signature_internal` still has a stack frame around 28 KB.

v17a checks whether simple lifetime-based buffer reuse is possible before doing a v17b code edit.

## Finding

The main large objects inside `signature_internal` are:

| Object | Approx size | Lifetime |
|---|---:|---|
| `mat` | 16,384 B | 723-829 |
| `s1hat` | 4,096 B | 724-828 |
| `t0hat` | 4,096 B | 725-827 |
| `s2hat` | 4,096 B | 726-826 |

Their lifetimes almost fully overlap.

## Conclusion

v17a shows that simple top-level buffer reuse is not safe inside `signature_internal`.

The next useful step should not be union-based reuse. Instead, v17b should test a caller-provided full signing workspace that moves `mat`, `s1hat`, `s2hat`, and `t0hat` into explicit caller-owned memory.

## Output

Generated result files are written to `layer3-results/v17a_*.md` and `layer3-results/v17a_*.csv`.

These generated files are ignored by git.
