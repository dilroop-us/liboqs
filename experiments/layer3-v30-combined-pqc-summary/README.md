# Layer 3 v30: Combined PQC Workspace Summary

## Goal

Create a number-heavy combined report for the completed Layer 3 workspace work across:

- ML-KEM-768
- ML-DSA-44
- combined ML-KEM + ML-DSA constrained build profile

v30 is report-only. It does not modify cryptographic code.

## Inputs summarized

ML-DSA phase:

- v16 caller matrix workspace
- v17b full sign workspace
- v19b attempt-generation workspace
- v21 unified signing workspace
- v22b verify workspace
- v23b keygen/provisioning workspace
- v24b compact lifecycle workspace

ML-KEM phase:

- v25a stack/lifetime analysis
- v25b baseline profiler
- v26 encapsulation workspace
- v27 keypair workspace
- v28 decapsulation workspace
- v29 compact lifecycle workspace

## Main numbers

ML-KEM:

- separate workspace total: 28064 B
- compact lifecycle workspace: 13088 B
- saved: 14976 B
- saved: 53.36%

ML-DSA:

- separate workspace total: 62432 B
- compact lifecycle workspace: 44064 B
- saved: 18368 B
- saved: 29.42%

Combined explicit workspace:

- ML-KEM lifecycle workspace: 13088 B
- ML-DSA lifecycle workspace: 44064 B
- combined total: 57152 B

## Outputs

Generated files:

- `layer3-results/v30_combined_pqc_summary_report.md`
- `layer3-results/v30_combined_pqc_summary.csv`
- `layer3-results/v30_combined_pqc_summary.json`

## Important limitation

v30 is an evidence summary.

It does not claim:

- production readiness
- formal verification
- constant-time proof
- Rust FFI readiness
- Pi readiness

Those are later phases.

## Next

v31 should implement a combined correctness harness for both ML-KEM and ML-DSA.
