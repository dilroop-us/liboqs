# Layer 3 v18: Workspace Accounting and Sanitization

## Goal

Make the v17b workspace optimization honest and safer.

v17b reduced ML-DSA-44 signing stack by moving large signing buffers into a caller-provided workspace. v18 measures the full memory tradeoff and adds experimental workspace sanitization.

## Why

v17b does not remove memory completely. It moves memory from stack into explicit caller-owned workspace.

That is useful for IoT systems where stack size is constrained, but the result must be reported honestly using:

- signing stack
- verification stack
- caller workspace size
- BSS size
- speed
- sanitization overhead

## Sanitization

v18 adds:

`MLD_CONFIG_EXPERIMENTAL_WORKSPACE_SANITIZE`

When enabled with:

`MLD_CONFIG_EXPERIMENTAL_CALLER_SIGN_WORKSPACE`

the caller-provided signing workspace is cleared during cleanup.

The workspace contains secret-derived buffers such as:

- `s1hat`
- `s2hat`
- `t0hat`

## Results

| Profile | Sign hot stack B | Verify stack B | Caller workspace B | BSS B | Stack + workspace + BSS B | Sign us | Verify us |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 44624 | 24640 | 0 | 216 | 44840 | 81.527 | 27.806 |
| Reduced-RAM | 13040 | 9312 | 0 | 216 | 13256 | 234.500 | 41.833 |
| v15 static matrix | 28240 | 8224 | 0 | 32984 | 61224 | 81.108 | 27.711 |
| v16 caller matrix | 28240 | 8256 | 16384 | 232 | 44856 | 81.985 | 27.635 |
| v17b full sign workspace | 15584 | 8256 | 28672 | 232 | 44488 | 81.461 | 27.677 |
| v18 sanitized workspace | 15584 | 8256 | 28672 | 232 | 44488 | 90.883 | 36.858 |

## Interpretation

Baseline is fast but stack-heavy.

Reduced-RAM gives the lowest memory usage but makes signing much slower.

v15 reduces stack but hides memory in BSS.

v16 moves matrix memory into caller-owned workspace.

v17b moves the full signing workspace into caller-owned memory, reducing signing stack to about 15.6 KB while keeping near-baseline speed.

v18 keeps the same memory layout as v17b and adds cleanup for secret-derived workspace data. The cost is about 9 us overhead because the current sanitizer clears the full workspace during cleanup.

## Conclusion

v18 proves the real memory tradeoff.

The optimization converts hidden stack pressure into explicit caller-owned workspace memory, keeps BSS low, and adds sanitization for secret-derived workspace data.
