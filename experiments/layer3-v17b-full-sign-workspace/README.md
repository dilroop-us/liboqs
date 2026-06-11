# Layer 3 v17b: Caller-Provided Full Signing Workspace

## Goal

Reduce ML-DSA-44 signing stack usage without using reduced-RAM lazy recomputation and without adding hidden static/BSS memory.

v17b extends the v16 caller-provided matrix workspace.

## Background

v16 moved only the ML-DSA matrix object out of stack:

- `mat`

v17a showed that the main large signing buffers overlap in lifetime:

- `mat`
- `s1hat`
- `s2hat`
- `t0hat`

Because their lifetimes overlap, simple union-based buffer reuse is not safe.

## v17b Idea

Move all of these large signing buffers into an explicit caller-provided workspace:

- `mat`
- `s1hat`
- `s2hat`
- `t0hat`

The memory is still required, but it is no longer hidden on the stack or in BSS. The caller owns it explicitly.

## Stack Result

| Function / hot frame | v16 | v17b |
|---|---:|---:|
| signing hot frame | 28,240 B | 15,584 B |
| verify_internal | 8,256 B | 8,256 B |
| mld_compute_pack_t0_t1 | 2,176 B | 2,176 B |

v17b reduces the effective signing hot frame by about 12.6 KB compared with v16.

## Speed Result

| Profile | Sign mean_us | Verify mean_us |
|---|---:|---:|
| baseline | 81.527 | 27.806 |
| reduced-RAM | 234.500 | 41.833 |
| static matrix | 81.108 | 27.711 |
| caller matrix | 81.985 | 27.635 |
| full sign workspace | 81.461 | 27.677 |

v17b keeps near-baseline speed.

## Size / BSS Result

| Profile | text | data | bss |
|---|---:|---:|---:|
| baseline | 468206 | 4016 | 216 |
| reduced-RAM | 462886 | 4016 | 216 |
| static matrix | 467886 | 4016 | 32984 |
| caller matrix | 468580 | 4040 | 232 |
| full sign workspace | 468760 | 4040 | 232 |

v17b avoids the large hidden BSS increase seen in the static matrix prototype.

## Conclusion

v17b is a strong IoT-style optimization result.

It reduces ML-DSA-44 signing stack from the v16 level of about 28.2 KB to about 15.6 KB, while preserving baseline-like signing speed and keeping BSS almost unchanged.

Compared with reduced-RAM mode, v17b is much faster while still giving a large stack reduction.
