# Layer 3 v41: Rust Workspace Ownership and Alignment API

## Scope

v41 moves lifecycle workspace allocation, alignment, activation, ownership, and zeroization into a Rust-side workspace context.

Crypto operations use the workspace context instead of directly managing raw allocation and lifecycle setter calls.

## Configuration

| Metric | Value |
|---|---:|
| crypto iterations per flow | 100 |
| workspace alignment | 64 bytes |

## Workspace accounting

| Scheme | Bytes | KiB |
|---|---:|---:|
| ML-KEM-768 | 13088 | 12.78 |
| ML-DSA-44 | 44064 | 43.03 |
| Combined | 57152 | 55.81 |

## Summary

| Metric | Value |
|---|---:|
| total rows | 8 |
| PASS rows | 8 |
| FAIL rows | 0 |
| overall v41 status | PASS |

## Results

| Case | Iterations | Passed | Failed | Status | Notes |
|---|---:|---:|---:|---|---|
| workspace_size_accounting | 1 | 1 | 0 | PASS | Workspace sizes match established lifecycle values |
| workspace_alignment | 1 | 1 | 0 | PASS | Both Rust-owned workspaces are 64-byte aligned |
| workspace_zero_initialization | 1 | 1 | 0 | PASS | Both workspace allocations begin zero initialized |
| workspace_activation | 1 | 1 | 0 | PASS | C and x86_64 lifecycle setters accept Rust-owned buffers |
| workspace_zeroization_routine | 1 | 1 | 0 | PASS | Live workspace wipe routine restores all bytes to zero |
| rust_workspace_api_mlkem_flow | 100 | 100 | 0 | PASS | ML-KEM flow through Rust workspace context |
| rust_workspace_api_mldsa_flow | 100 | 100 | 0 | PASS | ML-DSA flow through Rust workspace context |
| rust_workspace_api_combined_flow | 100 | 100 | 0 | PASS | Combined ML-KEM and ML-DSA flow through workspace context |

## What v41 validates

| Area | Validation |
|---|---|
| Ownership | Rust context owns both lifecycle workspace allocations |
| Size accounting | Workspace sizes match 13088 and 44064 bytes |
| Alignment | Both allocations satisfy 64-byte alignment |
| Initialization | New workspace memory begins zero initialized |
| Activation | C and x86_64 lifecycle setters accept the owned buffers |
| Zeroization | The live volatile wipe routine restores workspace bytes to zero |
| Crypto integration | ML-KEM ML-DSA and combined flows use the context successfully |

## Zeroization interpretation

The runtime test validates the same wipe routine while the allocation is still live. The Drop implementation calls that wipe routine before deallocation.

The harness intentionally does not read memory after deallocation, because doing so would be undefined behavior.

## Claim supported by v41

> v41 provides evidence that Rust can own, align, activate, and zeroize the optimized ML-KEM-768 and ML-DSA-44 lifecycle workspaces through a reusable workspace context while preserving the tested cryptographic flows.

## Limitations

- v41 is not a formal proof of Rust memory safety.
- v41 does not eliminate all unsafe FFI code.
- v41 does not test cross-thread workspace movement.
- v41 does not test async task behavior.
- v41 does not test all target architectures.
- v41 does not test real constrained-device hardware.
- v41 does not prove production readiness.

## Next

v42 should add a structured Rust correctness test suite around the workspace API with repeatable positive and negative test cases.
