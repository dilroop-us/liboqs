# Layer 3 v19b: Caller-Provided Attempt-Generation Workspace

## Goal

Reduce the remaining ML-DSA-44 signing stack hotspot after v17b/v18.

Target function:

`mld_attempt_signature_generation`

## Background

v17b moved outer signing buffers into caller-provided workspace:

- `mat`
- `s1hat`
- `s2hat`
- `t0hat`

v19a showed that the remaining signing frame is dominated by attempt-generation temporary buffers:

- `y`
- `w1tmp`
- `w0`
- `z`
- `cp`
- `t`
- `challenge_bytes`

Their lifetimes overlap heavily, so simple union-style reuse was not suitable.

## v19b idea

Move the attempt-generation buffers into explicit caller-owned workspace.

## Results

v19b removed `mld_attempt_signature_generation` from the top ML-DSA x86_64 stack-usage list.

Measured result:

- Sign mean: 80.659 us
- Verify mean: 27.683 us
- Caller sign workspace: 28672 B
- Caller attempt workspace: 15392 B
- Total caller workspace: 44064 B
- BSS: 248 B

## Interpretation

v19b does not remove memory entirely.

It moves memory from stack into explicit caller workspace.

This is useful for constrained systems where stack is limited but a fixed workspace can be reserved by the caller.

## Conclusion

v19b successfully performs the second-stage ML-DSA signing stack optimization.

v17b moved outer signing buffers.

v19b moved inner attempt-generation buffers.

Together, they provide low-stack ML-DSA signing while preserving near-baseline signing speed and keeping BSS low.
