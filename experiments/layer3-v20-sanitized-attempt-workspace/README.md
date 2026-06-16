# Layer 3 v20: Sanitized v19b Workspace

## Goal

Measure the security/performance cost of sanitizing caller-provided ML-DSA signing workspaces.

## Background

v19b moved the remaining `mld_attempt_signature_generation` buffers into caller-provided workspace:

- `y`
- `w1tmp`
- `w0`
- `z`
- `cp`
- `t`
- `challenge_bytes`

v19b removed the attempt-generation function from the signing stack hotspot list while preserving near-baseline speed.

## v20 change

v20 uses the same caller-workspace design as v19b, but enables:

`MLD_CONFIG_EXPERIMENTAL_WORKSPACE_SANITIZE`

This wipes caller-owned workspace memory after use.

## Build flags

- `MLD_CONFIG_EXPERIMENTAL_CALLER_SIGN_WORKSPACE`
- `MLD_CONFIG_EXPERIMENTAL_CALLER_ATTEMPT_WORKSPACE`
- `MLD_CONFIG_EXPERIMENTAL_WORKSPACE_SANITIZE`

## Results

Measured v20 result:

- Sign mean: 110.400 us
- Verify mean: 37.049 us
- BSS: 248 B
- Caller sign workspace: 28672 B
- Caller attempt workspace: 15392 B
- Total caller workspace: 44064 B

Stack result:

- `mld_attempt_signature_generation` does not return as a large stack hotspot.
- Signing wrapper frames remain small.

## Interpretation

v20 does not reduce memory further.

It measures the cost of cleaning explicit workspace memory.

The result is useful for security-conscious constrained systems where temporary signing state should not remain in caller-owned memory after use.

## Conclusion

v20 is the sanitized version of v19b.

It keeps low stack and low BSS, but adds measurable runtime overhead due to workspace cleanup.
