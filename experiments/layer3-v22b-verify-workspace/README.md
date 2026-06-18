# Layer 3 v22b: Caller-Provided ML-DSA Verify Workspace

## Goal

Reduce ML-DSA verification stack usage by moving verification-local buffers into caller-provided workspace.

## Background

v22a showed that `verify_internal` is local-buffer dominated:

- normal stack: 8256 B
- no-inline stack: 8288 B
- source-level buffers: about 8072 B

## v22b change

v22b introduces `mld_v22b_verify_workspace`.

It moves these buffers out of stack:

- `z`
- `cp`
- `w1`
- `tmp`
- `buf`
- `mu`
- `c`
- `c2`
- `hpk`

The matrix `mat` stays handled by the existing v17b/v21 workspace path.

## Results

Measured v22b result:

- Sign mean: 80.897 us
- Verify mean: 27.433 us
- BSS: 248 B
- Unified sign workspace: 44064 B
- Verify workspace: 8128 B
- Total sign+verify workspace: 52192 B

Stack result:

- `verify_internal`: 8256 B before v22b
- `verify_internal`: 192 B after v22b

## Interpretation

v22b does not remove memory.

It converts verification temporary memory from stack into explicit caller-owned workspace.

## Conclusion

v22b completes the ML-DSA sign/verify low-stack design together with v19b/v21.
