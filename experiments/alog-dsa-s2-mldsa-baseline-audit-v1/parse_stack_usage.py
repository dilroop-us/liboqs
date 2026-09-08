#!/usr/bin/env python3

import csv
import re
from pathlib import Path


ROOT = Path.home() / "pqc" / "liboqs"

BUILD = (
    ROOT /
    "build-alog-dsa-s2-mldsa-baseline-audit-v1"
)

RESULTS = (
    ROOT /
    "research-results" /
    "alog-dsa-s2-mldsa-baseline-audit-v1"
)

ALL_OUT = RESULTS / "stack_usage_all.csv"
MLDSA_OUT = RESULTS / "stack_usage_mldsa.csv"


pattern = re.compile(
    r"^(.*?):"
    r"(\d+):"
    r"(\d+):"
    r"([^\t]+)"
    r"\t(\d+)"
    r"\t(.*)$"
)


rows = []

for path in BUILD.rglob("*.su"):
    text = path.read_text(
        encoding="utf-8",
        errors="replace"
    )

    for raw in text.splitlines():
        match = pattern.match(raw.strip())

        if not match:
            continue

        source = match.group(1)
        line = match.group(2)
        column = match.group(3)
        function = match.group(4)
        bytes_used = int(match.group(5))
        kind = match.group(6)

        rows.append({
            "bytes": bytes_used,
            "kind": kind,
            "function": function,
            "source": source,
            "line": line,
            "column": column,
            "su_file": str(path.relative_to(BUILD)),
        })


rows.sort(
    key=lambda r: r["bytes"],
    reverse=True
)


def write_csv(path, data):
    with path.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "bytes",
                "kind",
                "function",
                "source",
                "line",
                "column",
                "su_file",
            ]
        )

        writer.writeheader()
        writer.writerows(data)


write_csv(ALL_OUT, rows)


def is_mldsa(row):
    text = (
        row["source"]
        + " "
        + row["function"]
        + " "
        + row["su_file"]
    ).lower()

    return (
        "ml_dsa" in text
        or "mldsa" in text
        or "ml-dsa" in text
    )


mldsa_rows = [
    row
    for row in rows
    if is_mldsa(row)
]

write_csv(MLDSA_OUT, mldsa_rows)

print(f"TOTAL_STACK_RECORDS,{len(rows)}")
print(f"MLDSA_STACK_RECORDS,{len(mldsa_rows)}")

print()
print("TOP_MLDSA_STACK_FRAMES")

for row in mldsa_rows[:30]:
    print(
        f"{row['bytes']:6d} B  "
        f"{row['kind']:<18} "
        f"{row['function']}  "
        f"{row['source']}:{row['line']}"
    )
