# Layer 3 v14: Stack Frame and Buffer Lifetime Analysis

## Goal

v14 analyzes ML-DSA-44 stack usage at the function and buffer-lifetime level.

v13 showed that the experimental lazy-polyvec path behaves almost the same as reduced-RAM on the x86_64 path. v14 therefore focuses on identifying the stack-heavy functions and temporary buffers before attempting a workspace or buffer-reuse optimization.

## Builds analyzed

All builds use:

- `OQS_EMBEDDED_BUILD=ON`
- `OQS_USE_OPENSSL=OFF`
- Minimal algorithms:
  - ML-KEM-768
  - ML-DSA-44
- `-fstack-usage`
- `-Wframe-larger-than=4096`

Profiles:

| Profile | Build flags |
|---|---|
| baseline | none |
| reduce_ram | `-DMLD_CONFIG_REDUCE_RAM` |
| lazy_polyvec | `-DMLD_CONFIG_EXPERIMENTAL_LAZY_MATRIX_ONLY -DMLD_CONFIG_SERIAL_FIPS202_ONLY` |

## Tools added

| File | Purpose |
|---|---|
| `run_v14_build_stack_usage.sh` | builds stack-usage instrumented variants |
| `v14_stack_usage_analyzer.py` | parses `.su` files and ranks ML-DSA stack frames |
| `run_v14_stack_usage_analysis.sh` | runs stack analysis for all profiles |
| `v14_compare_stack_profiles.py` | compares baseline, reduced-RAM, and lazy-polyvec stack frames |
| `run_v14_source_buffer_scan.sh` | scans ML-DSA source for large temporary buffer candidates |
| `v14_operation_profiler.c` | operation profiler source reused for consistency |

## Main x86_64 stack-frame results

| Function | Baseline | Reduced-RAM | Lazy-polyvec |
|---|---:|---:|---:|
| `signature_internal` | 44624 B | 13040 B | 13040 B |
| `verify_internal` | 24640 B | 9312 B | 9312 B |
| `mld_compute_pack_t0_t1` | 18560 B | 3232 B | 3232 B |
| `pk_from_sk` | 10176 B | 10176 B | 10176 B |
| `keypair_internal` | 8640 B | 8640 B | 8576 B |

## Findings

Reduced-RAM and lazy-polyvec both reduce the main x86_64 ML-DSA signing and verification stack frames significantly.

The largest reductions are:

| Function | Reduction |
|---|---:|
| `signature_internal` | 31584 B |
| `verify_internal` | 15328 B |
| `mld_compute_pack_t0_t1` | 15328 B |

This confirms that the memory savings observed in earlier runtime profiling come mainly from the ML-DSA signing and verification path in `sign.c`.

## Source-level buffer candidates

The source scan points to these key temporary objects:

```text
mld_polymat
mld_yvec
mld_polyveck
mld_polyvecl
mld_poly
