# Layer 3 v27: ML-KEM Keypair Caller Workspace

## Goal

Reduce ML-KEM-768 keypair stack usage by moving the large local buffers inside `indcpa_keypair_derand` into explicit caller-provided workspace.

v27 builds on v26.

- v26 reduced `indcpa_enc`
- v27 reduces `indcpa_keypair_derand`

## Why `indcpa_keypair_derand`

v25a showed the largest ML-KEM stack frames:

- `indcpa_enc`: 13312 B
- `indcpa_keypair_derand`: 10336 B
- `indcpa_dec`: 4992 B

v26 already handled `indcpa_enc`, so v27 targets `indcpa_keypair_derand`.

## v27 result

v27 reduced `indcpa_keypair_derand` stack usage:

| Variant | Previous stack | v27 stack | Reduction |
|---|---:|---:|---:|
| x86_64 | 10336 B | 192 B | 98.14% |
| ref | 10336 B | 128 B | 98.76% |

The v26 encapsulation frame stayed low:

| Variant | `indcpa_enc` stack |
|---|---:|
| x86_64 | 192 B |
| ref | 160 B |

`indcpa_dec` remains unchanged at 4992 B and is the target for v28.

## Workspace

v27 uses explicit caller-provided workspace for keypair.

Measured workspace sizes:

- `v26_enc_workspace`: 13088 B
- `v27_keypair_workspace`: 10112 B

## v27 workspace buffers

The workspace contains the major `indcpa_keypair_derand` local buffers:

- `mlk_polymat a`
- `mlk_polyvec e`
- `mlk_polyvec pkpv`
- `mlk_polyvec skpv`
- `mlk_polyvec_mulcache skpv_cache`
- `uint8_t buf[2 * MLKEM_SYMBYTES]`
- `uint8_t coins_with_domain_separator[MLKEM_SYMBYTES + 1]`

## Experimental API

v27 adds experimental workspace APIs for both native variants:

- `PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v27_keypair_workspace_bytes`
- `PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v27_keypair_workspace_set`
- `PQCP_MLKEM_NATIVE_MLKEM768_C_v27_keypair_workspace_bytes`
- `PQCP_MLKEM_NATIVE_MLKEM768_C_v27_keypair_workspace_set`

## Build flags

v27 is built with both v26 and v27 ML-KEM workspace flags:

- `MLK_CONFIG_EXPERIMENTAL_CALLER_ENC_WORKSPACE`
- `MLK_CONFIG_EXPERIMENTAL_CALLER_KEYPAIR_WORKSPACE`

## Safety rule

v27 only moves storage location.

Allowed:

- stack/local buffer to caller workspace buffer

Not changed:

- ML-KEM arithmetic
- matrix generation
- noise generation
- NTT logic
- packing
- hashing/KDF behavior
- randomness behavior
- constant-time behavior
- decapsulation failure handling

## Outputs

Generated files:

- `layer3-results/v27_build.log`
- `layer3-results/v27_mlkem_targets.md`
- `layer3-results/v27_mlkem_correctness.csv`
- `layer3-results/v27_mlkem_speed.csv`
- `layer3-results/v27_mlkem_size.csv`
- `layer3-results/v27_mlkem_workspace.csv`
- `layer3-results/v27_mlkem_keypair_workspace_report.md`

## Next version

v28 should target `indcpa_dec`.
