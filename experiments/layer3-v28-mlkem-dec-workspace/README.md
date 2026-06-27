# Layer 3 v28: ML-KEM Decapsulation Caller Workspace

## Goal

Reduce ML-KEM-768 decapsulation stack usage by moving the large local buffers inside `indcpa_dec` into explicit caller-provided workspace.

v28 builds on v26 and v27.

- v26 reduced `indcpa_enc`
- v27 reduced `indcpa_keypair_derand`
- v28 reduces `indcpa_dec`

## Why `indcpa_dec`

v25a showed the largest ML-KEM stack frames:

- `indcpa_enc`: 13312 B
- `indcpa_keypair_derand`: 10336 B
- `indcpa_dec`: 4992 B

v26 and v27 already handled the first two, so v28 targets `indcpa_dec`.

## v28 result

v28 reduced `indcpa_dec` stack usage:

| Variant | Previous stack | v28 stack | Reduction |
|---|---:|---:|---:|
| x86_64 | 4992 B | 80 B | 98.40% |
| ref | 4992 B | 80 B | 98.40% |

The previous v26/v27 reductions stayed stable:

| Variant | Function | Stack |
|---|---|---:|
| x86_64 | `indcpa_enc` | 192 B |
| ref | `indcpa_enc` | 160 B |
| x86_64 | `indcpa_keypair_derand` | 192 B |
| ref | `indcpa_keypair_derand` | 128 B |

## Workspace

Measured workspace sizes:

- `v26_enc_workspace`: 13088 B
- `v27_keypair_workspace`: 10112 B
- `v28_dec_workspace`: 4864 B

## v28 workspace buffers

The workspace contains the major `indcpa_dec` local buffers:

- `mlk_polyvec b`
- `mlk_polyvec skpv`
- `mlk_polyvec_mulcache b_cache`
- `mlk_poly v`
- `mlk_poly sb`

## Experimental API

v28 adds experimental workspace APIs for both native variants:

- `PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v28_dec_workspace_bytes`
- `PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v28_dec_workspace_set`
- `PQCP_MLKEM_NATIVE_MLKEM768_C_v28_dec_workspace_bytes`
- `PQCP_MLKEM_NATIVE_MLKEM768_C_v28_dec_workspace_set`

## Build flags

v28 is built with all three ML-KEM workspace flags:

- `MLK_CONFIG_EXPERIMENTAL_CALLER_ENC_WORKSPACE`
- `MLK_CONFIG_EXPERIMENTAL_CALLER_KEYPAIR_WORKSPACE`
- `MLK_CONFIG_EXPERIMENTAL_CALLER_DEC_WORKSPACE`

## Safety rule

v28 only moves storage location.

Allowed:

- stack/local buffer to caller workspace buffer

Not changed:

- ciphertext unpacking
- secret-key unpacking
- polynomial arithmetic
- compression/decompression
- message conversion
- hashing/KDF behavior
- constant-time behavior
- decapsulation failure handling

## Outputs

Generated files:

- `layer3-results/v28_build.log`
- `layer3-results/v28_mlkem_targets.md`
- `layer3-results/v28_mlkem_correctness.csv`
- `layer3-results/v28_mlkem_speed.csv`
- `layer3-results/v28_mlkem_size.csv`
- `layer3-results/v28_mlkem_workspace.csv`
- `layer3-results/v28_mlkem_dec_workspace_report.md`

## Next version

v29 should implement compact ML-KEM lifecycle workspace.
