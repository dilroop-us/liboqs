# Layer 3 v21: Unified Caller-Provided ML-DSA Signing Workspace

## Goal

Unify the v17b outer signing workspace and the v19b attempt-generation workspace into one caller-facing API.

## Background

v17b introduced caller-provided outer signing workspace.

v19b introduced caller-provided attempt-generation workspace.

Together they reduce ML-DSA signing stack pressure while preserving near-baseline signing speed.

Before v21, the caller had to manage two workspaces.

v21 exposes one unified signing workspace.

## Build flags

- `MLD_CONFIG_EXPERIMENTAL_CALLER_SIGN_WORKSPACE`
- `MLD_CONFIG_EXPERIMENTAL_CALLER_ATTEMPT_WORKSPACE`
- `MLD_CONFIG_EXPERIMENTAL_UNIFIED_SIGN_WORKSPACE`

## API idea

The caller uses:

- `v21_sign_workspace_bytes()`
- `v21_sign_workspace_set(...)`

Internally, this one workspace is split into:

- v17b outer signing workspace
- v19b attempt-generation workspace

## Results

Measured v21 result:

- Sign mean: 80.172 us
- Verify mean: 27.540 us
- BSS: 232 B

Stack result:

- `mld_attempt_signature_generation` does not return as a large stack hotspot.
- Signing wrapper frames remain small.

## Meaning

v21 is not a new cryptographic optimization.

It is an API cleanup step that makes the previous low-stack design easier to use in embedded systems.
