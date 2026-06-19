# Layer 3 v23b: Caller-Provided ML-DSA Keygen Workspace

## Goal

Reduce ML-DSA key generation and public-key reconstruction stack usage by moving local buffers into caller-provided workspace.

## Background

v23a showed that the remaining keygen/provisioning frames are local-buffer dominated:

- `keypair_internal`: 8640 B normal, 8576 B no-inline
- `pk_from_sk`: 10176 B normal, 10176 B no-inline

## v23b change

v23b introduces:

`mld_v23b_keygen_workspace`

It moves keypair buffers out of stack:

- `s1`
- `s2`
- `seedbuf`
- `tr`
- `inbuf`

It also moves pk_from_sk buffers out of stack:

- `s1`
- `s2`
- `t0_packed`
- `tr`
- `tr_computed`
- `rho`
- `key`

## Results

Stack reduction:

- `keypair_internal`: 8640 B → 160 B
- `pk_from_sk`: 10176 B → 96 B

Benchmark result:

- Keypair: 26.881 us
- Sign: 80.419 us
- Verify: 27.361 us
- BSS: 296 B

Workspace accounting:

- Unified sign workspace: 44064 B
- Verify workspace: 8128 B
- Keygen workspace: 10240 B
- Total explicit workspace: 62432 B

## Interpretation

v23b does not remove memory.

It converts keygen/provisioning temporary memory from hidden stack usage into explicit caller-owned workspace.

## Lifecycle coverage

Together with previous versions:

- v19b/v21: low-stack signing
- v22b: low-stack verification
- v23b: low-stack key generation / public-key reconstruction

## Conclusion

v23b completes the low-stack ML-DSA lifecycle.
