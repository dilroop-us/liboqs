# S-Profile Base v1 - D00 Upstream Migration

## Purpose

Forward-port the validated Layer 3 ML-KEM and ML-DSA workspace
research onto the updated liboqs upstream main before beginning:

- C-RX-KEM-S1
- ALOG-DSA-S2

## Upstream merge

The updated liboqs main was merged into the validated research state.

The ML-DSA sign.c conflicts were resolved additively:

- retained the Layer 3 experimental workspace/lifecycle work
- retained the new upstream mldsa-native source changes

ML-KEM custom workspace features also remained present after the merge.

## Frozen workspace controls

ML-KEM-768 v29 lifecycle:
13088 bytes

ML-DSA-44 v24 lifecycle:
44064 bytes

Combined lifecycle workspaces:
57152 bytes

## D00 validation

### v37 fresh build matrix

Build configurations:
- Release / O3
- RelWithDebInfo / O2
- Debug / O0
- Release / Os

Result:
12 / 12 rows PASS

ML-KEM correctness:
PASS

ML-DSA correctness + negative checks:
PASS

Combined ML-KEM + ML-DSA sequence:
PASS

### v40 fresh Rust FFI smoke

Result:
PASS

Iterations:
10 per case

## Decision

The updated upstream source preserves the validated Layer 3
workspace controls and Rust integration.

This commit is accepted as the common implementation base for:

- C-RX-KEM-S1
- ALOG-DSA-S2
