# Layer 3 v16: Caller Matrix Workspace Prototype

## Goal

Test whether the v15 static matrix workspace can be changed into a caller-provided workspace.

v15 reduced ML-DSA-44 stack usage, but it moved the matrix into hidden static/BSS memory. v16 keeps the same stack idea, but lets the caller provide the matrix workspace.

## Idea

v15: stack -> hidden static/BSS matrix
v16: stack -> caller-provided workspace

## Result

| Metric | Baseline | Reduced-RAM | v15 static | v16 caller |
|---|---:|---:|---:|---:|
| sign stack | 44,624 B | 13,040 B | 28,240 B | 28,240 B |
| verify stack | 24,640 B | 9,312 B | 8,224 B | 8,256 B |
| sign speed | 81.379 us | 234.314 us | 81.001 us | 81.607 us |
| verify speed | 27.911 us | 41.815 us | 27.691 us | 27.700 us |
| BSS | 184 B | 184 B | 32,952 B | 200 B |

## Conclusion

v16 keeps the same stack reduction and near-baseline speed as v15, but removes the large hidden BSS increase.

The matrix memory is still required, but ownership moves from hidden static memory to an explicit caller-provided workspace.
