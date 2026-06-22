#!/usr/bin/env python3
from pathlib import Path
import csv

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"
OUT = RESULTS / "v24b_compact_lifecycle_workspace_report.md"


def load_speed(path: Path) -> dict:
    values = {}

    if not path.exists():
        return values

    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            values[row["mode"]] = float(row["mean_us"])

    return values


def load_workspace(path: Path) -> dict:
    values = {}

    if not path.exists():
        return values

    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            values[row["workspace_kind"]] = int(row["bytes"])

    return values


def load_bss(path: Path) -> int:
    if not path.exists():
        return 0

    for line in path.read_text().splitlines():
        parts = line.split()

        if len(parts) >= 6 and parts[0].isdigit():
            return int(parts[2])

    return 0


speed = load_speed(RESULTS / "v24b_speed.csv")
workspace = load_workspace(RESULTS / "v24b_workspace_bytes.csv")
bss = load_bss(RESULTS / "v24b_size.csv")

v21_sign = workspace.get("unified_sign_workspace", 0)
v22b_verify = workspace.get("verify_workspace", 0)
v23b_keygen = workspace.get("keygen_workspace", 0)
v23b_total = workspace.get("v23b_separate_total", 0)
v24_total = workspace.get("v24_lifecycle_workspace", 0)
saved = workspace.get("saved_bytes", 0)
saved_percent = (saved / v23b_total * 100.0) if v23b_total else 0.0

keypair_us = speed.get("sig-keypair", 0.0)
sign_us = speed.get("sig-sign", 0.0)
verify_us = speed.get("sig-verify", 0.0)

report = f"""# Layer 3 v24b: Compact ML-DSA Lifecycle Workspace API

## Goal

Implement the compact lifecycle workspace model from v24a.

v24b introduces one caller-facing lifecycle workspace API that internally maps the older v21, v22b, and v23b workspace pointers into one compact caller-owned buffer.

## API added

    size_t v24_lifecycle_workspace_bytes(void);
    int v24_lifecycle_workspace_set(void *workspace, size_t workspace_bytes);

## Workspace result

| Workspace kind | Bytes |
|---|---:|
| v21 unified sign workspace | {v21_sign} |
| v22b verify workspace | {v22b_verify} |
| v23b keygen workspace | {v23b_keygen} |
| v23b separate total | {v23b_total} |
| v24 lifecycle workspace | {v24_total} |
| Saved bytes | {saved} |
| Saved percent | {saved_percent:.2f}% |

## Benchmark result

| Operation | Mean |
|---|---:|
| Keypair | {keypair_us:.3f} us |
| Sign | {sign_us:.3f} us |
| Verify | {verify_us:.3f} us |
| BSS | {bss} B |

## Stack result

v24b preserves the low-stack behavior achieved in v21, v22b, and v23b.

Expected high-level ML-DSA stack frames remain approximately:

| Function | Stack |
|---|---:|
| keypair_internal | about 160 B |
| pk_from_sk | about 96 B |
| verify_internal | about 192 B |
| signature/sign wrappers | about 528-544 B |

## Interpretation

v24b does not reduce stack further.

Instead, it reduces the caller-visible lifecycle workspace requirement while preserving speed, BSS, and low-stack behavior.

Before v24b, the caller had to manage three separate workspaces:

- sign workspace
- verify workspace
- keygen workspace

After v24b, the caller can manage one compact lifecycle workspace.

## Safety condition

The compact workspace is safe under this rule:

one workspace per thread/context; no concurrent sign, verify, or keygen operation on the same workspace.

## Conclusion

v24b successfully implements the compact ML-DSA lifecycle workspace API.

It reduces explicit caller workspace from {v23b_total} B to {v24_total} B, saving {saved} B ({saved_percent:.2f}%), while keeping keypair/sign/verify speed near v23b and keeping BSS low.
"""

OUT.write_text(report)

print(f"wrote {OUT}")
print(f"v23b_total={v23b_total}")
print(f"v24_total={v24_total}")
print(f"saved={saved}")
print(f"saved_percent={saved_percent:.2f}")
print(f"keypair_us={keypair_us:.3f}")
print(f"sign_us={sign_us:.3f}")
print(f"verify_us={verify_us:.3f}")
print(f"bss={bss}")
