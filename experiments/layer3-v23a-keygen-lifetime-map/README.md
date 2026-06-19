# Layer 3 v23a: ML-DSA Keypair / pk_from_sk Lifetime Map

## Goal

Analyze the remaining large ML-DSA stack frames after v22b reduced verification stack usage.

## Targets

- `keypair_internal`
- `pk_from_sk`

## Background

Previous work:

- v19b/v21 reduced signing stack pressure.
- v22b reduced `verify_internal` from about 8256 B to about 192 B.

After v22b, the largest remaining ML-DSA stack frames are key generation / provisioning related:

- `keypair_internal`
- `pk_from_sk`

## Findings

### keypair_internal

Normal frame:

- 8640 B

No-inline frame:

- 8576 B

Source-level local buffer total:

- 8418 B

Main buffers:

- `s1`: 4096 B
- `s2`: 4096 B
- `seedbuf`: 128 B
- `tr`: 64 B
- `inbuf`: 34 B

### pk_from_sk

Normal frame:

- 10176 B

No-inline frame:

- 10176 B

Source-level local buffer total:

- 10048 B

Main buffers:

- `s1`: 4096 B
- `s2`: 4096 B
- `t0_packed`: 1664 B
- `tr`: 64 B
- `tr_computed`: 64 B
- `rho`: 32 B
- `key`: 32 B

## Interpretation

Both target frames are local-buffer dominated, not inlining dominated.

## Next step

v23b should introduce caller-provided keygen/provisioning workspace.
