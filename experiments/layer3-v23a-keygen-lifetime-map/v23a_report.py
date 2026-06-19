#!/usr/bin/env python3
from pathlib import Path
import csv

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"
OUT = RESULTS / "v23a_keygen_lifetime_map_report.md"

TARGETS = [
    ("keypair_internal", "x86_64"),
    ("pk_from_sk", "x86_64"),
]


def load_lifetime(target, variant):
    path = RESULTS / f"v23a_{target}_lifetime_map_{variant}.csv"
    rows = []

    if not path.exists():
        return rows

    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                row["bytes_int"] = int(row["bytes"]) if row["bytes"] else 0
            except ValueError:
                row["bytes_int"] = 0
            rows.append(row)

    rows.sort(key=lambda r: r["bytes_int"], reverse=True)
    return rows


def load_compare():
    path = RESULTS / "v23a_noinline_compare.csv"
    out = {}

    if not path.exists():
        return out

    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            out[(row["target"], row["variant"])] = row

    return out


compare = load_compare()

report = "# Layer 3 v23a: ML-DSA Keypair / pk_from_sk Lifetime Map\n\n"

report += "## Goal\n\n"
report += (
    "Analyze the remaining large ML-DSA stack frames after v22b reduced "
    "`verify_internal` from about 8256 B to about 192 B.\n\n"
)

report += "Targets:\n\n"
report += "- `keypair_internal`\n"
report += "- `pk_from_sk`\n\n"

report += "v23a is analysis only. It does not modify the implementation.\n\n"

for target, variant in TARGETS:
    rows = load_lifetime(target, variant)
    cmp_row = compare.get((target, variant), {})

    normal = cmp_row.get("normal_bytes", "")
    noinline = cmp_row.get("noinline_bytes", "")
    delta = cmp_row.get("delta_percent", "")

    non_pointer_total = sum(
        r["bytes_int"]
        for r in rows
        if r["kind"] not in ("pointer", "workspace_pointer")
    )

    report += f"## {target} ({variant})\n\n"

    if normal:
        report += f"Normal stack frame: **{normal} B**\n\n"
    if noinline:
        report += f"No-inline stack frame: **{noinline} B**\n\n"
    if delta:
        report += f"No-inline delta: **{delta}%**\n\n"

    report += f"Known non-pointer source-level local total: **{non_pointer_total} B**\n\n"

    report += "| Name | Type | Kind | Approx bytes | First use | Last use |\n"
    report += "|---|---|---|---:|---:|---:|\n"

    for row in rows:
        if row["bytes_int"] == 0:
            continue
        report += (
            f"| `{row['name']}` | `{row['type']}` | {row['kind']} | "
            f"{row['bytes_int']} | {row['first_use']} | {row['last_use']} |\n"
        )

    report += "\n"

report += "## Interpretation\n\n"
report += (
    "`keypair_internal` and `pk_from_sk` are both local-buffer dominated. "
    "The no-inline attribution build does not significantly reduce either frame.\n\n"
)

report += "The large buffers are mostly:\n\n"
report += "- `s1`\n"
report += "- `s2`\n"
report += "- `t0_packed` in `pk_from_sk`\n"
report += "- smaller seed/hash buffers\n\n"

report += "## Recommended v23b direction\n\n"
report += (
    "v23b should move keygen/provisioning buffers into caller-provided workspace.\n\n"
)

report += "Recommended design:\n\n"
report += "- one `mld_v23b_keygen_workspace`\n"
report += "- used by both `keypair_internal` and `pk_from_sk`\n"
report += "- workspace should cover the larger `pk_from_sk` case, around 10 KB\n"
report += "- stack should drop from about 8.6 KB / 10.1 KB to small wrapper frames\n\n"

report += "## Conclusion\n\n"
report += (
    "v23a proves that the remaining ML-DSA key generation / public-key reconstruction "
    "stack hotspots are caused by local buffers, not compiler inlining. "
    "This makes them suitable for the same caller-workspace optimization pattern used in v19b/v21/v22b.\n"
)

OUT.write_text(report)
print(f"wrote {OUT}")
