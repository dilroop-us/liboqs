# Layer 3 v41: Rust Workspace Ownership and Alignment API

## Goal

v41 moves lifecycle workspace allocation, alignment, activation, ownership,
and zeroization into a reusable Rust-side workspace context.

## Build under test

- ML-KEM-768 with v29 lifecycle workspace
- ML-DSA-44 with v24 lifecycle workspace
- static minimal liboqs build
- Rust 2021 edition

## Workspace API responsibilities

The Rust workspace context:

- obtains workspace sizes from liboqs
- allocates caller-owned workspace memory
- guarantees 64-byte alignment
- zero-initializes new memory
- activates C and x86_64 lifecycle implementations
- keeps workspace allocations alive during crypto operations
- performs volatile zeroization before deallocation

## Runtime validations

v41 validates:

- workspace size accounting
- workspace alignment
- zero initialization
- lifecycle setter activation
- explicit zeroization routine
- ML-KEM flow through the workspace context
- ML-DSA flow through the workspace context
- combined ML-KEM and ML-DSA flow

## Zeroization boundary

The runtime harness validates the wipe routine while the allocation remains
live. Drop calls the same wipe routine before deallocation.

The harness does not read freed memory because doing so would be undefined
behavior.

## Claim boundary

v41 provides Rust workspace ownership and integration evidence. It does not
prove complete Rust safety, complete FFI safety, async safety, cross-platform
support, hardware readiness, or production readiness.

## Next

v42 should add a structured Rust correctness test suite using the v41
workspace API.
