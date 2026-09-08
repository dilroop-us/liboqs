# ALOG-DSA-S2 ML-DSA-44 Baseline Stack Classification

## Measurement method

Compiler stack-usage information was collected using -fstack-usage.
Individual .su frame sizes are compiler-reported function-frame sizes.

These values MUST NOT be summed unless the corresponding functions are
confirmed to be simultaneously nested on the same runtime call path.

## Largest relevant individual frames

| Function | Frame bytes | Preliminary role |
|---|---:|---|
| poly_uniform_4x | 3648 | public matrix generation |
| poly_uniform_gamma1_4x | 3360 | signing masking-vector sampling |
| mld_compute_pack_t0_t1 | 2176 | key generation candidate |
| poly_uniform_eta_4x | 1216 | key generation secret sampling candidate |

## Signing path

Expected structure:

OQS_SIG_sign
  -> ML-DSA wrapper
  -> mld_sign_signature_internal
  -> mld_attempt_signature_generation
       -> y sampling
       -> matrix-vector multiplication
       -> challenge
       -> z computation
       -> rejection checks
       -> hints
  -> accepted signature

The signing operation also uses the 44,064-byte explicit lifecycle workspace.

## Verification path

Expected structure:

OQS_SIG_verify
  -> ML-DSA wrapper
  -> mld_sign_verify_internal
       -> signature unpacking
       -> public matrix reconstruction/use
       -> challenge reconstruction
       -> final comparison

Verification uses the 8,128-byte operation workspace rather than the
44,064-byte signing peak.

## Important accounting rule

The largest individual .su entry is not the total ML-DSA stack peak.
A call-path sum is valid only when the caller/callee nesting has been
confirmed.

## ALOG implication

ALOG-DSA-S2 does not attempt to reduce the instantaneous ML-DSA signing
workspace. It reduces how often an ML-DSA signing operation and its
associated workspace/stack activity are invoked.
