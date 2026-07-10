# Layer 3 v38: Timing / Constant-Time-Style Leakage Validation

## Goal

Perform dudect-style timing-distribution screening for selected optimized ML-KEM/ML-DSA lifecycle-workspace operations.

v38 is statistical timing screening, not a formal constant-time proof.

## Optimized build under test

- ML-KEM-768 with v29 lifecycle workspace
- ML-DSA-44 with v24 lifecycle workspace

## What v38 tests

v38 collects timing samples for two timing classes per case and computes an absolute Welch t-statistic.

Tested cases:

- ML-KEM decapsulation: valid ciphertext vs modified ciphertext
- ML-DSA verification: valid signature vs modified signature
- ML-DSA signing: fixed message vs alternate message
- Combined transcript verification: valid transcript vs modified transcript

## Status meanings

- PASS: abs(Welch t) is below the configured threshold and no execution failure occurred
- FLAG: abs(Welch t) is above the configured threshold
- FAIL: expected cryptographic correctness behavior failed during timing collection

## Default parameters

- samples per case: 2000
- warmup operations per case: 100
- Welch t-threshold: 4.5
- batch size: 1

## Claims supported

v38 supports statistical timing-distribution evidence for the tested timing classes.

If no rows are flagged, v38 supports the claim that the tested classes did not exceed the configured leakage-candidate threshold.

If rows are flagged, v38 supports the claim that those rows require timing follow-up.

## Limitations

v38 does not prove:

- formal constant-time behavior
- power-analysis resistance
- EM side-channel resistance
- cache-attack resistance
- branch-predictor resistance
- production side-channel security

Timing results can be affected by CPU frequency scaling, OS scheduling, thermal throttling, and background processes.

## Next

v39 should produce a final memory/accounting/evidence report tying v31-v38 together, or perform deeper timing follow-up if v38 produces timing flags.
