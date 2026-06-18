# Layer 3 v22a: ML-DSA verify_internal Lifetime Map

## Goal

Analyze the remaining ML-DSA verification stack hotspot after v19b/v20/v21 optimized the signing path.

## Target

Source function:

`mld_sign_verify_internal`

Compiler-reported symbol:

`verify_internal`

## Findings

Normal stack report:

- `verify_internal`: 8256 B

No-inline attribution build:

- `verify_internal`: 8288 B

This shows the frame is local-buffer dominated, not inlining dominated.

## Source-level buffer map

The scanner identified these verification-local buffers:

- `z`: 4096 B
- `cp`: 1024 B
- `w1`: 1024 B
- `tmp`: 1024 B
- `buf`: 768 B
- `mu`: 64 B
- `c`: 32 B
- `c2`: 32 B

Known local total:

`8072 B`

This closely matches the compiler frame of `8256 B`.

## Interpretation

v22a confirms that verification stack pressure comes from local verification buffers.

## Next step

v22b should move these buffers into a caller-provided verify workspace:

- `z`
- `cp`
- `w1`
- `tmp`
- `buf`
- `mu`
- `c`
- `c2`

The matrix `mat` is already handled by the existing caller workspace path.
