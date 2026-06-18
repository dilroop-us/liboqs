#!/usr/bin/env python3
from pathlib import Path
import csv

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"
OUT = RESULTS / "v22a_verify_lifetime_map_report.md"

X86_CSV = RESULTS / "v22a_verify_lifetime_map_x86_64.csv"
STACK_MD = RESULTS / "v22a_verify_lifetime_map_x86_64_top_stack_usage.md"


def load_buffers(path):
    rows = []
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


def extract_verify_stack(path):
    if not path.exists():
        return ""
    for line in path.read_text().splitlines():
        if "verify_internal" in line:
            return line
    return ""


buffers = load_buffers(X86_CSV)
verify_stack_line = extract_verify_stack(STACK_MD)

non_pointer_total = sum(
    r["bytes_int"] for r in buffers
    if r["kind"] not in ("pointer", "workspace_pointer")
)

report = f"""# Layer 3 v22a: ML-DSA verify_internal Lifetime Map

## Goal

Analyze the remaining ML-DSA verification stack hotspot after v19b/v20/v21 optimized the signing path.

v22a is analysis only. It does not modify verification buffers.

## Stack result

Normal build:

- `verify_internal`: 8256 B

No-inline attribution build:

- `verify_internal`: 8288 B

Because the no-inline frame stays almost the same, the stack pressure is caused by local verification buffers, not by inlined child functions.

## Source-level buffer map

| Name | Type | Approx bytes | First use | Last use |
|---|---|---:|---:|---:|
"""

for r in buffers:
    if r["kind"] == "workspace_pointer":
        continue
    report += (
        f"| `{r['name']}` | `{r['type']}` | {r['bytes_int']} | "
        f"{r['first_use']} | {r['last_use']} |\n"
    )

report += f"""

Known non-pointer local total: **{non_pointer_total} B**

Compiler frame: **8256 B**

Difference: **{8256 - non_pointer_total} B**, likely scalar locals, compiler alignment, and frame overhead.

## Interpretation

The verification frame is dominated by these buffers:

- `z`
- `cp`
- `w1`
- `tmp`
- `buf`
- `mu`
- `c`
- `c2`

Their lifetimes overlap across most of `mld_sign_verify_internal`, so simple union reuse is not the safest first optimization.

## v22b direction

v22b should introduce a caller-provided verification workspace containing:

- `z`
- `cp`
- `w1`
- `tmp`
- `buf`
- `mu`
- `c`
- `c2`

The existing `mat` buffer should remain handled through the v17b/v21 caller matrix/signing workspace path.

Expected v22b result:

- `verify_internal` stack drops significantly
- BSS remains low
- verification speed remains close to baseline
- caller verify workspace becomes explicit, around 8 KB

## Conclusion

v22a proves that the remaining ML-DSA verification stack hotspot is local-buffer dominated.

Final conclusion:

`verify_internal` is approximately 8 KB because of local verification buffers, not because of compiler inlining.
"""

OUT.write_text(report)
print(f"wrote {OUT}")
