# Layer 3 v15: Static Matrix Workspace Prototype

## Goal

v15 tests whether ML-DSA-44 stack pressure can be reduced without switching fully to reduced-RAM/lazy recomputation.

v14 showed that the largest stack frames are concentrated in:

- `signature_internal`
- `verify_internal`
- `mld_compute_pack_t0_t1`

v15 moves the large eager `mld_polymat` matrix workspace out of stack and into static storage when this macro is enabled:

```text
MLD_CONFIG_EXPERIMENTAL_STATIC_MATRIX_WORKSPACE
