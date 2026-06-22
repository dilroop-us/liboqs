#!/usr/bin/env python3
from pathlib import Path
import csv

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"

CURRENT_SYMBOLS = RESULTS / "v24a_current_workspace_symbols.csv"
OUT_CSV = RESULTS / "v24a_workspace_size_compare.csv"
OUT_MD = RESULTS / "v24a_workspace_layout_report.md"

MATRIX_BYTES = 16384
DEFAULT_SIGN = 44064
DEFAULT_VERIFY = 8128
DEFAULT_KEYGEN = 10240


def load_symbols():
    values = {}

    if not CURRENT_SYMBOLS.exists():
        raise SystemExit(f"missing required file: {CURRENT_SYMBOLS}")

    with CURRENT_SYMBOLS.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            values[row["workspace_kind"]] = int(row["bytes"])

    return values


symbols = load_symbols()

sign_workspace = symbols.get("unified_sign_workspace", DEFAULT_SIGN)
verify_workspace = symbols.get("verify_workspace", DEFAULT_VERIFY)
keygen_workspace = symbols.get("keygen_workspace", DEFAULT_KEYGEN)

if sign_workspace == 0 or verify_workspace == 0 or keygen_workspace == 0:
    raise SystemExit(
        "one or more workspace symbols returned 0; check that v23b was built with v21/v22b/v23b workspace symbols"
    )

separate_total = sign_workspace + verify_workspace + keygen_workspace

sign_op_only = sign_workspace - MATRIX_BYTES
verify_op = verify_workspace
keygen_op = keygen_workspace

compact_common = MATRIX_BYTES
compact_union_op = max(sign_op_only, verify_op, keygen_op)
compact_total = compact_common + compact_union_op

savings = separate_total - compact_total
savings_percent = (savings / separate_total * 100.0) if separate_total else 0.0

rows = [
    {
        "layout": "v23b_separate_workspaces",
        "common_matrix_bytes": 0,
        "sign_op_bytes": sign_workspace,
        "verify_op_bytes": verify_workspace,
        "keygen_op_bytes": keygen_workspace,
        "total_bytes": separate_total,
        "notes": "Current separate v21/v22b/v23b caller workspaces",
    },
    {
        "layout": "v24a_compact_model",
        "common_matrix_bytes": compact_common,
        "sign_op_bytes": sign_op_only,
        "verify_op_bytes": verify_op,
        "keygen_op_bytes": keygen_op,
        "total_bytes": compact_total,
        "notes": "Common matrix plus union of sign/verify/keygen operation buffers",
    },
]

with OUT_CSV.open("w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "layout",
            "common_matrix_bytes",
            "sign_op_bytes",
            "verify_op_bytes",
            "keygen_op_bytes",
            "total_bytes",
            "notes",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)

report = f"""# Layer 3 v24a: Compact ML-DSA Workspace Layout Model

## Current v23b layout

| Workspace | Bytes |
|---|---:|
| Unified sign workspace | {sign_workspace} |
| Verify workspace | {verify_workspace} |
| Keygen workspace | {keygen_workspace} |
| Separate total | {separate_total} |

## Compact v24a model

| Region | Bytes |
|---|---:|
| Common matrix region | {compact_common} |
| Sign-only operation region | {sign_op_only} |
| Verify operation region | {verify_op} |
| Keygen operation region | {keygen_op} |
| Operation union size | {compact_union_op} |
| Compact total | {compact_total} |

## Savings

| Metric | Value |
|---|---:|
| Saved bytes | {savings} |
| Saved percent | {savings_percent:.2f}% |

## Conclusion

v24a predicts that the separate v21/v22b/v23b workspaces can be compacted from {separate_total} B to {compact_total} B.
"""

OUT_MD.write_text(report)

print(f"wrote {OUT_CSV}")
print(f"wrote {OUT_MD}")
print(f"separate_total={separate_total}")
print(f"compact_total={compact_total}")
print(f"savings={savings}")
print(f"savings_percent={savings_percent:.2f}")
