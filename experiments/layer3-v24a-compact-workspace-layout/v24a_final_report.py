#!/usr/bin/env python3
from pathlib import Path
import csv

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"

SIZE_CSV = RESULTS / "v24a_workspace_size_compare.csv"
CALL_MD = RESULTS / "v24a_call_order_checks.md"
OUT = RESULTS / "v24a_compact_workspace_final_report.md"


def load_rows(path):
    rows = []

    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    return rows


rows = load_rows(SIZE_CSV)

separate = next(
    (r for r in rows if r["layout"] == "v23b_separate_workspaces"),
    None,
)

compact = next(
    (r for r in rows if r["layout"] == "v24a_compact_model"),
    None,
)

if separate is None:
    raise SystemExit("missing v23b_separate_workspaces row in v24a_workspace_size_compare.csv")

if compact is None:
    raise SystemExit("missing v24a_compact_model row in v24a_workspace_size_compare.csv")

separate_total = int(separate["total_bytes"])
compact_total = int(compact["total_bytes"])

savings = separate_total - compact_total
savings_percent = (savings / separate_total * 100.0) if separate_total else 0.0

call_checks = CALL_MD.read_text() if CALL_MD.exists() else "call-order checks not found"

report = f"""# Layer 3 v24a Final Report: Compact ML-DSA Lifecycle Workspace

## Goal

Analyze whether the separate v21/v22b/v23b caller workspaces can be represented as one compact ML-DSA lifecycle workspace.

v24a does not modify implementation code. It only analyzes workspace layout and call-order safety.

## Current state after v23b

After v23b, the current design uses three separate caller-provided workspaces.

| Workspace | Bytes |
|---|---:|
| Unified sign workspace | 44064 |
| Verify workspace | 8128 |
| Keygen workspace | 10240 |
| Separate total | {separate_total} |

## Compact v24a model

The compact model uses one common matrix region and one union of operation-specific buffers.

| Region | Bytes |
|---|---:|
| Common matrix region | 16384 |
| Sign operation region | 27680 |
| Verify operation region | 8128 |
| Keygen operation region | 10240 |
| Operation union size | 27680 |
| Compact total | {compact_total} |

## Savings

| Metric | Value |
|---|---:|
| v23b separate total | {separate_total} B |
| v24a compact model | {compact_total} B |
| Saved bytes | {savings} B |
| Saved percent | {savings_percent:.2f}% |

## Safety reasoning

The compact layout is safe under these conditions:

1. One workspace is used by one thread/context at a time.
2. The same workspace is not used for concurrent sign/verify/keygen operations.
3. The matrix region remains common and separate.
4. Sign, verify, and keygen operation-specific temporary regions share a union.
5. Keygen/provisioning buffers are cleaned before pairwise consistency testing enters sign/verify paths.

## Call-order check

{call_checks}

## Recommended v24b implementation

v24b should introduce one lifecycle workspace API:

    size_t v24_lifecycle_workspace_bytes(void);
    int v24_lifecycle_workspace_set(void *workspace, size_t workspace_bytes);

Internally, v24b should map these older workspace pointers into safe offsets inside one compact caller-owned buffer:

- v21 sign workspace pointer
- v22b verify workspace pointer
- v23b keygen workspace pointer

## Expected v24b result

| Metric | Expected |
|---|---:|
| Stack | unchanged from v23b |
| Speed | unchanged from v23b |
| BSS | stays low |
| Explicit workspace | {compact_total} B |
| Saved explicit workspace | {savings} B |

## Conclusion

v24a predicts that ML-DSA lifecycle explicit workspace can be reduced from {separate_total} B to {compact_total} B, saving {savings} B ({savings_percent:.2f}%), while preserving the low-stack behavior achieved in v21, v22b, and v23b.

This means v24b should focus on API cleanup and workspace compaction, not new stack reduction.
"""

OUT.write_text(report)

print(f"wrote {OUT}")
print(f"separate_total={separate_total}")
print(f"compact_total={compact_total}")
print(f"savings={savings}")
print(f"savings_percent={savings_percent:.2f}")
