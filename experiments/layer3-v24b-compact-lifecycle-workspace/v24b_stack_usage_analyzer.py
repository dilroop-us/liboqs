#!/usr/bin/env python3
from pathlib import Path
import csv
import re
import sys

ROOT = Path.home() / "pqc/liboqs"

if len(sys.argv) != 4:
    print("usage: v24b_stack_usage_analyzer.py <build-dir> <label> <results-dir>")
    sys.exit(2)

BUILD = ROOT / sys.argv[1]
LABEL = sys.argv[2]
RESULTS = ROOT / sys.argv[3]

RESULTS.mkdir(exist_ok=True)

SU_RE = re.compile(r"^(.*?):(\d+):(\d+):([^\t]+)\t(\d+)\t(.+)$")


def variant_from_path(path: str) -> str:
    if "mldsa-native_ml-dsa-44_x86_64" in path:
        return "x86_64"
    if "mldsa-native_ml-dsa-44_ref" in path:
        return "ref"
    return "unknown"


rows = []

for su in BUILD.rglob("*.su"):
    text = su.read_text(errors="replace")
    for line in text.splitlines():
        m = SU_RE.match(line)
        if not m:
            continue

        src, line_no, col_no, function, bytes_s, kind = m.groups()

        if "mldsa-native_ml-dsa-44" not in src:
            continue

        rows.append({
            "variant": variant_from_path(src),
            "bytes": int(bytes_s),
            "kind": kind,
            "function": function,
            "location": f"{src}:{line_no}:{col_no}",
            "source_file": src,
            "line": int(line_no),
            "su_file": str(su),
        })

rows.sort(key=lambda r: r["bytes"], reverse=True)

csv_path = RESULTS / f"v24b_{LABEL}_stack_usage.csv"
top_path = RESULTS / f"v24b_{LABEL}_top_stack_usage.md"
x86_path = RESULTS / f"v24b_{LABEL}_x86_64_top_stack_usage.md"
targets_path = RESULTS / f"v24b_{LABEL}_targets.md"

with csv_path.open("w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "variant", "bytes", "kind", "function", "location",
            "source_file", "line", "su_file"
        ],
    )
    writer.writeheader()
    writer.writerows(rows)


def write_top(path, title, filtered_rows):
    with path.open("w") as f:
        f.write(f"# v24b top ML-DSA stack-usage functions: {title}\n\n")
        f.write("| Rank | Variant | Bytes | Kind | Function | Location |\n")
        f.write("|---:|---|---:|---|---|---|\n")
        for i, row in enumerate(filtered_rows[:40], 1):
            f.write(
                f"| {i} | {row['variant']} | {row['bytes']} | {row['kind']} | "
                f"`{row['function']}` | `{row['location']}` |\n"
            )


write_top(top_path, LABEL, rows)
write_top(x86_path, LABEL, [r for r in rows if r["variant"] == "x86_64"])

targets = [
    r for r in rows
    if "keypair_internal" in r["function"] or "pk_from_sk" in r["function"]
]

with targets_path.open("w") as f:
    f.write("# v24b target ML-DSA stack frames\n\n")
    f.write("| Variant | Target | Bytes | Kind | Function | Location |\n")
    f.write("|---|---|---:|---|---|---|\n")
    for row in targets:
        target = "keypair_internal" if "keypair_internal" in row["function"] else "pk_from_sk"
        f.write(
            f"| {row['variant']} | {target} | {row['bytes']} | {row['kind']} | "
            f"`{row['function']}` | `{row['location']}` |\n"
        )

print(f"wrote {csv_path}")
print(f"wrote {top_path}")
print(f"wrote {x86_path}")
print(f"wrote {targets_path}")
print(f"rows: {len(rows)}")
