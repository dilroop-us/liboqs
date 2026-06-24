# Layer 3 v26: ML-KEM Encapsulation Caller Workspace

## Goal

Reduce ML-KEM-768 encapsulation stack usage by moving the large local buffers inside `indcpa_enc` into explicit caller-provided workspace.

v26 is the first real ML-KEM implementation optimization after v25a and v25b.

## Why `indcpa_enc`

v25a showed the largest ML-KEM stack frames:

- `indcpa_enc`: 13312 B
- `indcpa_keypair_derand`: 10336 B
- `indcpa_dec`: 4992 B

So v26 targets `indcpa_enc` first.

## v26 result

v26 reduced `indcpa_enc` stack usage:

| Variant | v25a stack | v26 stack | Reduction |
|---|---:|---:|---:|
| x86_64 | 13312 B | 192 B | 98.56% |
| ref | 13312 B | 160 B | 98.80% |

Correctness passed for:

- ML-KEM keypair
- ML-KEM encapsulation
- ML-KEM decapsulation

## Workspace

v26 uses an explicit caller-provided workspace for encapsulation.

Measured workspace size:

- `v26_enc_workspace`: 13088 B

## v26 workspace buffers

The workspace contains the major `indcpa_enc` local buffers:

- `mlk_polymat at`
- `mlk_polyvec sp`
- `mlk_polyvec pkpv`
- `mlk_polyvec ep`
- `mlk_polyvec b`
- `mlk_polyvec_mulcache sp_cache`
- `mlk_poly v`
- `mlk_poly k`
- `mlk_poly epp`
- `uint8_t seed[MLKEM_SYMBYTES]`

## Experimental API

v26 adds experimental workspace APIs for both native variants:

- `PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v26_enc_workspace_bytes`
- `PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v26_enc_workspace_set`
- `PQCP_MLKEM_NATIVE_MLKEM768_C_v26_enc_workspace_bytes`
- `PQCP_MLKEM_NATIVE_MLKEM768_C_v26_enc_workspace_set`

## Safety rule

v26 only moves storage location.

Allowed:

- stack local buffer to caller workspace buffer

Not changed:

- ML-KEM arithmetic
- matrix generation
- noise generation
- NTT logic
- compression/decompression
- hashing/KDF behavior
- randomness behavior
- ciphertext computation
- constant-time behavior
- decapsulation failure handling

## Outputs

Generated files:

- `layer3-results/v26_build.log`
- `layer3-results/v26_mlkem_targets.md`
- `layer3-results/v26_mlkem_correctness.csv`
- `layer3-results/v26_mlkem_speed.csv`
- `layer3-results/v26_mlkem_size.csv`
- `layer3-results/v26_mlkem_workspace.csv`
- `layer3-results/v26_mlkem_enc_workspace_report.md`

## Next version

v27 should target `indcpa_keypair_derand`.
