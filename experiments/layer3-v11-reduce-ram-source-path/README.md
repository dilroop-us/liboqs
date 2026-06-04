# Layer 3 v11: Reduced-RAM Source-Path Confirmation

## Goal

v11 explains why the v10 reduced-RAM build lowered ML-DSA-44 stack usage.

v10 result:

| Profile | Operation | Peak stack | Peak total |
|---|---|---:|---:|
| Baseline | ML-DSA-44 sign/verify | 50904 B | 59224 B |
| Reduced-RAM | ML-DSA-44 sign/verify | 15456 B | 23168 B |

## Main finding

Reduced-RAM mode changes ML-DSA matrix handling from eager expansion to lazy expansion.

Baseline uses eager matrix functions:

- `polyvec_matrix_expand_eager`
- `polyvec_matrix_pointwise_montgomery_row_eager`
- `polyvec_matrix_pointwise_montgomery_yvec_eager`

Reduced-RAM uses lazy matrix functions:

- `polyvec_matrix_expand_lazy`
- `polyvec_matrix_pointwise_montgomery_row_lazy`
- `polyvec_matrix_pointwise_montgomery_yvec_lazy`

## Source-path explanation

The important dispatch happens in:

```text
src/sig/ml_dsa/mldsa-native_ml-dsa-44_x86_64/mldsa/src/polyvec_lazy.h
