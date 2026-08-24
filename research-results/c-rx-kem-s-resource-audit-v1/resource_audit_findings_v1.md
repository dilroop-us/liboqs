# C-RX-KEM-S Resource Audit Findings v1

## Confirmed operation workspaces

- v26 encapsulation / receiver re-encryption: 13,088 B
- v27 keypair: 10,112 B
- v28 IND-CPA decryption: 4,864 B
- v29 lifecycle: 13,088 B

The full ML-KEM receiver reaches the v26 workspace because
CCA decapsulation recomputes the ciphertext using IND-CPA encryption.

## v28 breakdown

- b: 1,536 B
- skpv: 1,536 B
- b_cache: 768 B
- v: 512 B
- sb: 512 B
- total: 4,864 B

All major v28 objects overlap around the multiply phase.
Simple lifetime aliasing therefore appears limited.

## v26 breakdown

- at: 4,608 B
- sp: 1,536 B
- pkpv: 1,536 B
- ep: 1,536 B
- b: 1,536 B
- sp_cache: 768 B
- v: 512 B
- k: 512 B
- epp: 512 B
- seed: 32 B
- total: 13,088 B

## Current-schedule semantic peak

Preliminary source-lifetime analysis indicates approximately
12,544 B of semantically live v26 state during matrix-vector
multiplication.

The difference between the allocated 13,088-B workspace and
the current semantic peak is therefore only approximately 544 B.

This suggests that simple union/aliasing changes alone are
unlikely to produce a large improvement.

## S1 scheduling hypothesis

ep, epp, and k are currently produced before the matrix and
multiply stages even though they are consumed later.

A standards-preserving scheduling hypothesis is to delay their
generation until after sp/pkpv/sp_cache-heavy processing has
finished.

The analytical live-set model predicts a possible workspace
peak of approximately:

9,984 B

compared with:

13,088 B

for a potential reduction of:

3,104 B (~23.7%)

This is an analytical hypothesis only. No implementation or
correctness claim has yet been made.

## Persistent key

Serialized ML-KEM-768 decapsulation key:

2,400 B

Preliminary component model:

- IND-CPA secret: 1,152 B
- embedded public key: 1,184 B
- H(pk): 32 B
- z: 32 B

Storage-reconstruction opportunities remain under analysis.

## Stack

Known top-level mlk_kem_dec static frame:

1,376 B

Most of this is explained by:

- buf: 64 B
- kr: 64 B
- tmp: 1,120 B

Nested receiver call-path peak remains to be finalized.

## Candidate status

### S1
Promising. Main target is receiver-side deterministic
re-encryption scheduling.

### S2
Still under analysis. Persistent storage is materially smaller
than the workspace but may still matter on very constrained
targets.

### S3
Still valuable for bounded service memory and resource-exhaustion
control under concurrent requests.

## Final selection

Not yet frozen.
