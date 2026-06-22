# Layer 3 v24b: Compact ML-DSA Lifecycle Workspace API

## Goal

Implement the compact lifecycle workspace model from v24a.

v24b adds one caller-facing lifecycle workspace API that maps the older v21, v22b, and v23b workspaces into one compact buffer.

## Background

After v23b, the separate workspace accounting was:

- v21 unified sign workspace: 44064 B
- v22b verify workspace: 8128 B
- v23b keygen workspace: 10240 B
- separate total: 62432 B

v24a proved that these can be modeled as:

- common matrix region: 16384 B
- operation-specific union region: 27680 B
- compact lifecycle workspace: 44064 B

## v24b change

v24b introduces:

- `v24_lifecycle_workspace_bytes`
- `v24_lifecycle_workspace_set`

The setter maps:

- v21 sign workspace to the base of the compact buffer
- v22b verify workspace to the operation-union region
- v23b keygen workspace to the same operation-union region

## Result

Workspace:

- v23b separate total: 62432 B
- v24 lifecycle workspace: 44064 B
- saved: 18368 B
- saved percent: 29.42%

Speed:

- keypair: 26.854 us
- sign: 80.368 us
- verify: 27.391 us

BSS:

- 264 B

## Stack result

v24b preserves the low-stack behavior from v21, v22b, and v23b.

Important high-level ML-DSA frames remain low:

- keypair_internal: about 160 B
- pk_from_sk: about 96 B
- verify_internal: about 192 B
- signature/sign wrappers: about 528-544 B

## Safety condition

The compact workspace assumes:

- one workspace per thread/context
- no concurrent sign/verify/keygen operation on the same workspace

## Interpretation

v24b is not a new cryptographic algorithm.

It is an implementation/API optimization that reduces caller-visible workspace size while keeping stack usage, speed, and BSS under control.

## Conclusion

v24b keeps the low-stack behavior from v21, v22b, and v23b while reducing the caller-visible lifecycle workspace from 62432 B to 44064 B.

This saves 18368 B, or about 29.42%, without hurting keypair/sign/verify performance.

## Next step

After v24b, ML-DSA high-level lifecycle workspace work is mostly complete.

Possible next directions:

- v25: lower-level ML-DSA polynomial helper stack analysis
- ML-KEM workspace optimization
- Raspberry Pi benchmarking
