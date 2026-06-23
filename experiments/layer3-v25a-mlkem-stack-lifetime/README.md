# Layer 3 v25a: ML-KEM-768 Stack and Lifetime Analysis

## Goal

Analyze ML-KEM-768 stack usage before modifying ML-KEM implementation code.

v25a is analysis only.

## Build profiles

v25a uses three builds:

1. ML-KEM-only normal build
2. ML-KEM + ML-DSA combined build
3. ML-KEM-only no-inline build

## Why both ML-KEM-only and combined builds are used

The ML-KEM-only build gives clean ML-KEM stack data.

The combined build validates that the same ML-KEM stack hotspots appear in the full project context with ML-DSA included.

The no-inline build checks whether the large ML-KEM frames are caused by inlining or by real local buffers.

## Target operations

- ML-KEM keypair
- ML-KEM encapsulation
- ML-KEM decapsulation

## Target internal functions

The current known large stack frames are in:

- `indcpa_keypair_derand`
- `indcpa_enc`
- `indcpa_dec`

## What v25a does

v25a performs:

1. ML-KEM-only stack-usage build
2. Combined ML-KEM + ML-DSA stack-usage build
3. ML-KEM-only no-inline stack-usage build
4. ML-KEM-only vs combined comparison
5. Normal vs no-inline comparison
6. Source-level lifetime map of large local buffers in `indcpa.c`
7. Final report

## Key result

The ML-KEM-only and combined builds show the same main ML-KEM stack hotspots:

- `indcpa_enc`: about 13312 B
- `indcpa_keypair_derand`: about 10336 B
- `indcpa_dec`: about 4992 B

The no-inline comparison shows these frames are local-buffer dominated.

## Outputs

Generated result files:

- `layer3-results/v25a_mlkem_only_mlkem_stack_usage.csv`
- `layer3-results/v25a_mlkem_only_mlkem_top_stack_usage.md`
- `layer3-results/v25a_mlkem_only_mlkem_targets.md`
- `layer3-results/v25a_combined_mlkem_stack_usage.csv`
- `layer3-results/v25a_combined_mlkem_top_stack_usage.md`
- `layer3-results/v25a_combined_mlkem_targets.md`
- `layer3-results/v25a_noinline_mlkem_stack_usage.csv`
- `layer3-results/v25a_noinline_mlkem_top_stack_usage.md`
- `layer3-results/v25a_noinline_mlkem_targets.md`
- `layer3-results/v25a_mlkem_only_vs_combined.md`
- `layer3-results/v25a_mlkem_normal_vs_noinline.md`
- `layer3-results/v25a_mlkem_lifetime_map.md`
- `layer3-results/v25a_mlkem_report.md`

## Next step

After v25a, run v25b.

v25b should benchmark ML-KEM keypair, encapsulation, and decapsulation before making ML-KEM workspace changes.

## Safety rule for future ML-KEM patches

Future patches should only move storage location:

- stack local buffer
- to caller-provided workspace buffer

Do not change:

- constant-time comparison
- failure handling
- decapsulation selection logic
- hashing/KDF order
- randomness
- compression/decompression arithmetic
- polynomial arithmetic
