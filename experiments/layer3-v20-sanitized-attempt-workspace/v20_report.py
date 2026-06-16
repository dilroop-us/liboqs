#!/usr/bin/env python3
from pathlib import Path
import csv

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"
OUT = RESULTS / "v20_sanitized_workspace_report.md"


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
v20_speed = load_speed(RESULTS / "v20_speed.csv")

v19b_workspace = load_workspace(RESULTS / "v19b_workspace_bytes.csv")
v20_workspace = load_workspace(RESULTS / "v20_workspace_bytes.csv")

v19b_bss = load_bss(RESULTS / "v19b_size.csv")
v20_bss = load_bss(RESULTS / "v20_size.csv")

v19b_sign = v19b_speed.get("sig-sign", 0.0)
v19b_verify = v19b_speed.get("sig-verify", 0.0)

v20_sign = v20_speed.get("sig-sign", 0.0)
v20_verify = v20_speed.get("sig-verify", 0.0)

sign_overhead = ((v20_sign - v19b_sign) / v19b_sign * 100.0) if v19b_sign else 0.0
verify_overhead = ((v20_verify - v19b_verify) / v19b_verify * 100.0) if v19b_verify else 0.0

report = f"""# Layer 3 v20: Sanitized v19b Workspace

## Goal

Measure the cost of sanitizing caller-provided ML-DSA signing workspaces after v19b.

v19b moved the remaining attempt-generation buffers out of stack and into caller-owned workspace.

v20 enables:

`MLD_CONFIG_EXPERIMENTAL_WORKSPACE_SANITIZE`

## Build configuration

v20 uses:

- `MLD_CONFIG_EXPERIMENTAL_CALLER_SIGN_WORKSPACE`
- `MLD_CONFIG_EXPERIMENTAL_CALLER_ATTEMPT_WORKSPACE`
- `MLD_CONFIG_EXPERIMENTAL_WORKSPACE_SANITIZE`

## Results

| Metric | v19b unsanitized | v20 sanitized |
|---|---:|---:|
| Sign mean | {v19b_sign:.3f} us | {v20_sign:.3f} us |
| Verify mean | {v19b_verify:.3f} us | {v20_verify:.3f} us |
| Sign overhead | - | {sign_overhead:.2f}% |
| Verify overhead | - | {verify_overhead:.2f}% |
| BSS | {v19b_bss} B | {v20_bss} B |
| Caller sign workspace | {v19b_workspace.get("caller_sign_workspace", 0)} B | {v20_workspace.get("caller_sign_workspace", 0)} B |
| Caller attempt workspace | {v19b_workspace.get("caller_attempt_workspace", 0)} B | {v20_workspace.get("caller_attempt_workspace", 0)} B |
| Total caller workspace | {v19b_workspace.get("total_caller_workspace", 0)} B | {v20_workspace.get("total_caller_workspace", 0)} B |

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

v20 preserves the v19b low-stack design but adds memory sanitization.

It does not reduce total memory further. It improves memory hygiene by wiping caller-owned signing workspaces after use.

The tradeoff is increased latency.

## Conclusion

v20 is the security-conscious version of v19b.

v19b answers:

`How low can signing stack go while keeping speed?`

v20 answers:

`What is the cost of cleaning the caller workspace after use?`

Final conclusion:

`v20 keeps the low-stack design and low BSS, but sanitization adds measurable runtime overhead.`
"""

OUT.write_text(report)
print(f"wrote {OUT}")
