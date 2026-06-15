# Layer 3 v19a: Attempt-Generation Lifetime Map

## Goal

Analyze the remaining ML-DSA-44 signing stack hotspot after v17b and v18.

The target function is:

`mld_attempt_signature_generation`

v19a is analysis only. It does not modify cryptographic code.

## Background

v17b moved the outer signing buffers into caller-provided workspace:

- `mat`
- `s1hat`
- `s2hat`
- `t0hat`

v18 then measured the real memory tradeoff and added workspace sanitization.

After v17b/v18, the largest remaining signing frame is:

`mld_attempt_signature_generation`

around 15.6 KB.

## Method

v19a performs:

- lifetime scan of `mld_attempt_signature_generation`
- extracted source inspection
- no-inline attribution build
- approximate buffer-size accounting
- reuse candidate detection

## Final finding

The corrected lifetime map shows that the remaining frame is dominated by:

| Buffer | Type | Approx bytes |
|---|---|---:|
| `y` | `mld_yvec` | 4096 |
| `w1tmp` | `w1tmp_u` | 4096 |
| `w0` | `mld_polyveck` | 4096 |
| `z` | `mld_poly` | 1024 |
| `cp` | `mld_poly` | 1024 |
| `t` | `mld_poly` | 1024 |
| `challenge_bytes` | `uint8_t[MLDSA_CTILDEBYTES]` | 32 |

Known total:

`15,392 B`

This matches the compiler-reported frame of about 15.6 KB.

## Reuse result

No safe simple reuse candidates were found.

The major buffers overlap heavily:

- `y`: 893–1021
- `w1tmp`: 895–1019
- `w0`: 896–1018
- `z`: 894–1020
- `cp`: 897–1017
- `t`: 898–1016

## Conclusion

v19a shows that the remaining signing stack pressure is caused by attempt-generation buffers inside `mld_attempt_signature_generation`.

Because these buffers overlap heavily, v19b should use a caller-provided attempt-generation workspace instead of simple union-style reuse.
