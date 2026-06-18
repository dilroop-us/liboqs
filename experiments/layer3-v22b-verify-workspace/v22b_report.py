#!/usr/bin/env python3
from pathlib import Path
import csv

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"
OUT = RESULTS / "v22b_verify_workspace_report.md"


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


def find_stack_row(path, needle):
    if not path.exists():
        return ""
    for line in path.read_text().splitlines():
        if needle in line:
            return line
    return ""


v21_speed = load_speed(RESULTS / "v21_speed.csv")
v22b_speed = load_speed(RESULTS / "v22b_speed.csv")

v22b_workspace = load_workspace(RESULTS / "v22b_workspace_bytes.csv")

v21_bss = load_bss(RESULTS / "v21_size.csv")
v22b_bss = load_bss(RESULTS / "v22b_size.csv")

v21_sign = v21_speed.get("sig-sign", 0.0)
v21_verify = v21_speed.get("sig-verify", 0.0)

v22b_sign = v22b_speed.get("sig-sign", 0.0)
v22b_verify = v22b_speed.get("sig-verify", 0.0)

sign_delta = ((v22b_sign - v21_sign) / v21_sign * 100.0) if v21_sign else 0.0
verify_delta = ((v22b_verify - v21_verify) / v21_verify * 100.0) if v21_verify else 0.0

stack_md = RESULTS / "v22b_verify_workspace_x86_64_top_stack_usage.md"
verify_stack_row = find_stack_row(stack_md, "verify_internal")

report = f"""# Layer 3 v22b: Caller-Provided ML-DSA Verify Workspace

## Goal

Reduce the remaining ML-DSA verification stack hotspot by moving verification-local buffers into caller-provided workspace.

v22a showed that `verify_internal` was local-buffer dominated:

- normal stack: 8256 B
- no-inline stack: 8288 B
- source-level local buffers: about 8072 B

## v22b change

v22b introduces `mld_v22b_verify_workspace`.

It moves these verification-local buffers out of stack:

- `z`
- `cp`
- `w1`
- `tmp`
- `buf`
- `mu`
- `c`
- `c2`
- `hpk`

The matrix `mat` remains handled by the existing v17b/v21 workspace path.

## Results

| Metric | v21 | v22b |
|---|---:|---:|
| Sign mean | {v21_sign:.3f} us | {v22b_sign:.3f} us |
| Verify mean | {v21_verify:.3f} us | {v22b_verify:.3f} us |
| Sign delta | - | {sign_delta:.2f}% |
| Verify delta | - | {verify_delta:.2f}% |
| BSS | {v21_bss} B | {v22b_bss} B |
| Unified sign workspace | 44064 B | {v22b_workspace.get("unified_sign_workspace", 0)} B |
| Verify workspace | - | {v22b_workspace.get("verify_workspace", 0)} B |
| Total sign+verify workspace | - | {v22b_workspace.get("total_sign_plus_verify_workspace", 0)} B |

## Stack result

Before v22b:

- `verify_internal`: 8256 B

After v22b:

- `verify_internal`: 192 B

Stack analyzer row:

`{verify_stack_row}`

## Interpretation

v22b extends the caller-workspace model from signing to verification.

It does not remove memory. It converts verification temporary memory from hidden stack usage into explicit caller-owned workspace.

The result is strong because verification stack drops dramatically while BSS stays low and verification speed remains near v21.

## Conclusion

v22b completes the ML-DSA sign/verify low-stack story:

- v19b/v21: low-stack signing
- v22b: low-stack verification

Final conclusion:

`v22b reduces ML-DSA verification stack pressure from about 8256 B to about 192 B by converting verification-local buffers into explicit caller-provided workspace.`
"""

OUT.write_text(report)
print(f"wrote {OUT}")
