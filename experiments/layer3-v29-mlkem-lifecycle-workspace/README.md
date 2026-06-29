# Layer 3 v29: Compact ML-KEM Lifecycle Workspace

## Goal

Reduce explicit caller-provided ML-KEM workspace memory by combining the separate v26, v27, and v28 workspaces into one compact lifecycle workspace.

v29 builds on:

- v26: `indcpa_enc` caller workspace
- v27: `indcpa_keypair_derand` caller workspace
- v28: `indcpa_dec` caller workspace

## Why v29

After v28, the main ML-KEM IND-CPA stack frames are already reduced:

- `indcpa_enc`
- `indcpa_keypair_derand`
- `indcpa_dec`

However, the explicit workspace memory is still separate:

- `v26_enc_workspace`: 13088 B
- `v27_keypair_workspace`: 10112 B
- `v28_dec_workspace`: 4864 B

Separate total:

- 28064 B

v29 compacts these into one lifecycle workspace using a union-style layout.

Compact size:

- 13088 B

Saving:

- 14976 B
- about 53.36%

## Result

v29 keeps the v26/v27/v28 stack reductions unchanged:

| Variant | Function | v29 stack |
|---|---|---:|
| x86_64 | `indcpa_keypair_derand` | 192 B |
| ref | `indcpa_keypair_derand` | 128 B |
| x86_64 | `indcpa_enc` | 192 B |
| ref | `indcpa_enc` | 160 B |
| x86_64 | `indcpa_dec` | 80 B |
| ref | `indcpa_dec` | 80 B |

## Experimental API

v29 adds experimental lifecycle workspace APIs for both native variants:

- `PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v29_lifecycle_workspace_bytes`
- `PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v29_lifecycle_workspace_set`
- `PQCP_MLKEM_NATIVE_MLKEM768_C_v29_lifecycle_workspace_bytes`
- `PQCP_MLKEM_NATIVE_MLKEM768_C_v29_lifecycle_workspace_set`

## Build flags

v29 is built with all three ML-KEM operation workspace flags and the compact lifecycle flag:

- `MLK_CONFIG_EXPERIMENTAL_CALLER_ENC_WORKSPACE`
- `MLK_CONFIG_EXPERIMENTAL_CALLER_KEYPAIR_WORKSPACE`
- `MLK_CONFIG_EXPERIMENTAL_CALLER_DEC_WORKSPACE`
- `MLK_CONFIG_EXPERIMENTAL_COMPACT_LIFECYCLE_WORKSPACE`

## Safety rule

v29 only changes workspace ownership and layout.

Allowed:

- separate operation workspaces to one compact lifecycle workspace

Not changed:

- ML-KEM arithmetic
- matrix generation
- noise generation
- packing
- compression/decompression
- hashing/KDF behavior
- constant-time behavior
- decapsulation failure handling

## Outputs

Generated files:

- `layer3-results/v29_build.log`
- `layer3-results/v29_mlkem_targets.md`
- `layer3-results/v29_mlkem_correctness.csv`
- `layer3-results/v29_mlkem_speed.csv`
- `layer3-results/v29_mlkem_size.csv`
- `layer3-results/v29_mlkem_workspace.csv`
- `layer3-results/v29_mlkem_lifecycle_workspace_report.md`

## Interpretation

v29 completes the ML-KEM high-level workspace phase.

After v29:

- stack is reduced through v26/v27/v28
- explicit workspace is compacted through v29
