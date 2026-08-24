#!/usr/bin/env python3

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path.home() / "pqc" / "liboqs"

BUILD = (
    ROOT
    / "build-c-rx-kem-s-resource-audit-v1"
)

RESULTS = (
    ROOT
    / "research-results"
    / "c-rx-kem-s-resource-audit-v1"
)

ALL_OUT = RESULTS / "stack_usage_all.csv"
MLKEM_OUT = RESULTS / "stack_usage_mlkem.csv"

KEYWORDS = re.compile(
    r"ml[_-]?kem|mlkem|kem_dec|decaps|decapsulate|pqcp_mlkem",
    re.IGNORECASE,
)


def parse_su(path: Path):
    rows = []

    try:
        lines = path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
    except Exception:
        return rows

    for line in lines:
        parts = line.split("\t")

        if len(parts) < 2:
            continue

        descriptor = parts[0]

        try:
            stack_bytes = int(parts[1])
        except ValueError:
            continue

        mode = parts[2] if len(parts) > 2 else ""

        rows.append(
            {
                "su_file": str(path.relative_to(ROOT)),
                "descriptor": descriptor,
                "stack_bytes": stack_bytes,
                "mode": mode,
            }
        )

    return rows


rows = []

for path in BUILD.rglob("*.su"):
    rows.extend(parse_su(path))

rows.sort(
    key=lambda row: row["stack_bytes"],
    reverse=True,
)

mlkem_rows = [
    row
    for row in rows
    if KEYWORDS.search(
        row["descriptor"] + " " + row["su_file"]
    )
]


def write_csv(path: Path, data):
    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "stack_bytes",
                "mode",
                "descriptor",
                "su_file",
            ],
        )

        writer.writeheader()

        for row in data:
            writer.writerow(
                {
                    "stack_bytes": row["stack_bytes"],
                    "mode": row["mode"],
                    "descriptor": row["descriptor"],
                    "su_file": row["su_file"],
                }
            )


write_csv(ALL_OUT, rows)
write_csv(MLKEM_OUT, mlkem_rows)

print(f"all stack rows: {len(rows)}")
print(f"ML-KEM rows:    {len(mlkem_rows)}")

print()
print("Top ML-KEM-related stack frames:")

for row in mlkem_rows[:30]:
    print(
        f"{row['stack_bytes']:8d}  "
        f"{row['descriptor']}"
    )

print()
print(f"wrote {ALL_OUT}")
print(f"wrote {MLKEM_OUT}")
