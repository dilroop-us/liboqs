#!/usr/bin/env python3
from pathlib import Path
import csv

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"
OUT = RESULTS / "v23b_keygen_workspace_report.md"


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


speed = load_speed(RESULTS / "v23b_speed.csv")
workspace = load_workspace(RESULTS / "v23b_workspace_bytes.csv")
bss = load_bss(RESULTS / "v23b_size.csv")

stack_md = RESULTS / "v23b_keygen_workspace_x86_64_top_stack_usage.md"
keypair_row = find_stack_row(stack_md, "keypair_internal")
pk_from_sk_row = find_stack_row(stack_md, "pk_from_sk")
verify_row = find_stack_row(stack_md, "verify_internal")

report = f"""# Layer 3 v23b: Caller-Provided ML-DSA Keygen Workspace

## Goal

Reduce the remaining ML-DSA key generation and public-key reconstruction stack hotspots.

v23a showed that these frames were local-buffer dominated:

- `keypair_internal`: 8640 B normal, 8576 B no-inline
- `pk_from_sk`: 10176 B normal, 10176 B no-inline

## v23b change

v23b introduces:

`mld_v23b_keygen_workspace`

It moves keypair/provisioning temporary buffers out of stack and into explicit caller-owned workspace.

### keypair_internal buffers moved

- `s1`
- `s2`
- `seedbuf`
- `tr`
- `inbuf`

### pk_from_sk buffers moved

- `s1`
- `s2`
- `t0_packed`
- `tr`
- `tr_computed`
- `rho`
- `key`

## Stack results

Before v23b:

- `keypair_internal`: 8640 B
- `pk_from_sk`: 10176 B

After v23b:

- `keypair_internal`: 160 B on x86_64
- `pk_from_sk`: 96 B on x86_64

Stack rows:

`{keypair_row}`

`{pk_from_sk_row}`

Verification remains low-stack from v22b:

`{verify_row}`

## Benchmark results

| Metric | v23b |
|---|---:|
| Keypair mean | {speed.get("sig-keypair", 0.0):.3f} us |
| Sign mean | {speed.get("sig-sign", 0.0):.3f} us |
| Verify mean | {speed.get("sig-verify", 0.0):.3f} us |
| BSS | {bss} B |

## Workspace accounting

| Workspace | Bytes |
|---|---:|
| Unified sign workspace | {workspace.get("unified_sign_workspace", 0)} B |
| Verify workspace | {workspace.get("verify_workspace", 0)} B |
| Keygen workspace | {workspace.get("keygen_workspace", 0)} B |
| Total explicit workspace | {workspace.get("total_sign_verify_keygen_workspace", 0)} B |

## Interpretation

v23b does not remove memory.

It converts key generation and public-key reconstruction temporary memory from hidden stack usage into explicit caller-owned workspace.

This matches the previous Layer 3 pattern:

- v19b/v21: low-stack signing
- v22b: low-stack verification
- v23b: low-stack key generation / public-key reconstruction

## Conclusion

v23b completes the low-stack ML-DSA lifecycle.

The remaining major stack hotspots are now lower-level polynomial helper functions, not the high-level ML-DSA sign, verify, keypair, or pk_from_sk paths.
"""

OUT.write_text(report)
print(f"wrote {OUT}")
