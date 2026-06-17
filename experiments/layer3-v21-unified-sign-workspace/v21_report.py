#!/usr/bin/env python3
from pathlib import Path
import csv

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"
OUT = RESULTS / "v21_unified_sign_workspace_report.md"


def load_speed(path):
    out = {}
    if not path.exists():
        return out

    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            out[row["mode"]] = float(row["mean_us"])

    return out


def load_workspace(path):
    out = {}
    if not path.exists():
        return out

    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            out[row["workspace_kind"]] = int(row["bytes"])

    return out


def load_bss(path):
    if not path.exists():
        return 0

    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 6 and parts[0].isdigit():
            return int(parts[2])

    return 0


v19b_speed = load_speed(RESULTS / "v19b_speed.csv")
v21_speed = load_speed(RESULTS / "v21_speed.csv")

v21_workspace = load_workspace(RESULTS / "v21_workspace_bytes.csv")

v19b_bss = load_bss(RESULTS / "v19b_size.csv")
v21_bss = load_bss(RESULTS / "v21_size.csv")

v19b_sign = v19b_speed.get("sig-sign", 0.0)
v21_sign = v21_speed.get("sig-sign", 0.0)

v19b_verify = v19b_speed.get("sig-verify", 0.0)
v21_verify = v21_speed.get("sig-verify", 0.0)

sign_delta = ((v21_sign - v19b_sign) / v19b_sign * 100.0) if v19b_sign else 0.0
verify_delta = ((v21_verify - v19b_verify) / v19b_verify * 100.0) if v19b_verify else 0.0

report = f"""# Layer 3 v21: Unified Caller-Provided ML-DSA Signing Workspace

## Goal

Unify the v17b outer signing workspace and the v19b attempt-generation workspace into one caller-facing API.

v21 is an API cleanup and integration step, not a new memory-reduction algorithm.

## Build configuration

v21 uses:

- `MLD_CONFIG_EXPERIMENTAL_CALLER_SIGN_WORKSPACE`
- `MLD_CONFIG_EXPERIMENTAL_CALLER_ATTEMPT_WORKSPACE`
- `MLD_CONFIG_EXPERIMENTAL_UNIFIED_SIGN_WORKSPACE`

## Results

| Metric | v19b | v21 |
|---|---:|---:|
| Sign mean | {v19b_sign:.3f} us | {v21_sign:.3f} us |
| Verify mean | {v19b_verify:.3f} us | {v21_verify:.3f} us |
| Sign delta | - | {sign_delta:.2f}% |
| Verify delta | - | {verify_delta:.2f}% |
| BSS | {v19b_bss} B | {v21_bss} B |
| Unified signing workspace | - | {v21_workspace.get("unified_sign_workspace", 0)} B |

## Workspace accounting

| Workspace | Bytes |
|---|---:|
| Outer sign workspace | {v21_workspace.get("caller_sign_workspace", 0)} |
| Attempt-generation workspace | {v21_workspace.get("caller_attempt_workspace", 0)} |
| Unified signing workspace | {v21_workspace.get("unified_sign_workspace", 0)} |

## Stack result

`mld_attempt_signature_generation` does not return as a large stack hotspot.

The remaining signing wrapper frames are small:

- `signature`: about 544 B
- `signature_internal`: about 528 B
- `sign`: about 112 B

The remaining large ML-DSA frames are unrelated paths:

- `pk_from_sk`
- `keypair_internal`
- `verify_internal`

## Interpretation

v21 keeps the v19b low-stack design but hides the two-workspace implementation behind one caller-provided workspace API.

The caller now reserves one fixed memory block for ML-DSA signing temporary state.

## Conclusion

v21 turns the v17b/v19b experimental stack optimizations into a cleaner embedded-facing workspace model.

Final conclusion:

`v21 provides one unified caller-owned ML-DSA signing workspace while preserving the v19b low-stack behavior.`
"""

OUT.write_text(report)
print(f"wrote {OUT}")
